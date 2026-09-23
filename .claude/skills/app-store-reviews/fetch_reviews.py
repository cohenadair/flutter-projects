#!/usr/bin/env python3
"""Fetch App Store customer reviews for every app on the personal team.

Uses the App Store Connect API (GET /v1/apps, GET /v1/apps/{id}/
customerReviews). No third-party packages: the ES256 JWT is signed with the
`openssl` CLI.

Config: config.json next to this script (git-ignored)
  {
    "issuer_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "key_id": "ABCDE12345",
    "private_key_path": "AuthKey_ABCDE12345.p8"
  }
A relative private_key_path is resolved against this script's folder.

Output: JSON on stdout (see SKILL.md for the shape). Errors for a single app
are reported inline so one failure doesn't hide the rest.
"""

import argparse
import base64
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")
STATE_PATH = os.path.join(SKILL_DIR, "state.json")
API = "https://api.appstoreconnect.apple.com"

# Apple caps token lifetime at 20 minutes.
TOKEN_TTL_SECONDS = 19 * 60

# How far back to look past the newest review already seen, so reviews
# edited/re-dated near the checkpoint boundary aren't missed.
NEW_MODE_OVERLAP_DAYS = 7

# Default look-back for the needs-reply list, independent of the review
# window, so an unanswered review keeps showing up on later runs.
DEFAULT_REPLY_LOOKBACK_DAYS = 365


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def der_to_raw_signature(der):
    """Convert an ASN.1 DER ECDSA signature to the raw r||s form JWS wants."""
    # SEQUENCE { INTEGER r, INTEGER s }
    if der[0] != 0x30:
        raise ValueError("Unexpected signature format")
    idx = 2 if der[1] < 0x80 else 2 + (der[1] & 0x7F)
    parts = []
    for _ in range(2):
        if der[idx] != 0x02:
            raise ValueError("Unexpected signature format")
        length = der[idx + 1]
        value = der[idx + 2:idx + 2 + length].lstrip(b"\x00")
        parts.append(value.rjust(32, b"\x00"))
        idx += 2 + length
    return parts[0] + parts[1]


def make_token(config):
    now = int(time.time())
    header = {"alg": "ES256", "kid": config["key_id"], "typ": "JWT"}
    payload = {
        "iss": config["issuer_id"],
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "aud": "appstoreconnect-v1",
    }
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url(json.dumps(payload, separators=(",", ":")).encode())
    )
    key_path = os.path.join(
        SKILL_DIR, os.path.expanduser(config["private_key_path"])
    )
    with tempfile.NamedTemporaryFile() as f:
        f.write(signing_input.encode())
        f.flush()
        der = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_path, f.name],
            check=True,
            capture_output=True,
        ).stdout
    return signing_input + "." + b64url(der_to_raw_signature(der))


def get(url, token):
    request = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + token}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            errors = json.loads(body).get("errors", [])
            detail = "; ".join(
                "{} {}".format(err.get("title", ""), err.get("detail", ""))
                for err in errors
            )
        except ValueError:
            detail = body[:300]
        raise RuntimeError("HTTP {}: {}".format(e.code, detail.strip()))


def paginate(url, token):
    while url:
        page = get(url, token)
        yield page
        url = page.get("links", {}).get("next")


def parse_date(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def list_apps(token):
    query = urllib.parse.urlencode(
        {"fields[apps]": "name,bundleId", "limit": 200}
    )
    apps = []
    for page in paginate("{}/v1/apps?{}".format(API, query), token):
        for item in page.get("data", []):
            apps.append({
                "app_id": item["id"],
                "name": item["attributes"].get("name", ""),
                "bundle_id": item["attributes"].get("bundleId", ""),
            })
    return apps


def list_reviews(token, app_id, cutoff):
    """Newest-first reviews created at/after `cutoff` (None = all)."""
    query = urllib.parse.urlencode({
        "sort": "-createdDate",
        "limit": 200,
        "include": "response",
        "fields[customerReviews]": ",".join([
            "rating", "title", "body", "reviewerNickname", "createdDate",
            "territory", "response",
        ]),
        "fields[customerReviewResponses]": "responseBody,lastModifiedDate,state",
    })
    url = "{}/v1/apps/{}/customerReviews?{}".format(API, app_id, query)
    reviews = []
    for page in paginate(url, token):
        responses = {
            inc["id"]: inc["attributes"]
            for inc in page.get("included", [])
            if inc.get("type") == "customerReviewResponses"
        }
        reached_cutoff = False
        for item in page.get("data", []):
            attrs = item["attributes"]
            if cutoff is not None and parse_date(attrs["createdDate"]) < cutoff:
                reached_cutoff = True
                break
            response_data = (
                item.get("relationships", {}).get("response", {}).get("data")
            )
            response = None
            if response_data is not None:
                response = responses.get(response_data["id"])
            reviews.append({
                "id": item["id"],
                "rating": attrs.get("rating"),
                "title": attrs.get("title", ""),
                "body": attrs.get("body", ""),
                "reviewer": attrs.get("reviewerNickname", ""),
                "created": attrs.get("createdDate"),
                "territory": attrs.get("territory", ""),
                "response": response,
            })
        if reached_cutoff:
            break
    return reviews


def needs_reply_reason(review):
    """Why a review needs (another) reply, or None if it doesn't."""
    response = review["response"]
    if response is None:
        return "no_reply"
    if response.get("state") != "PUBLISHED":
        return None
    replied = response.get("lastModifiedDate")
    if replied and parse_date(replied) < parse_date(review["created"]):
        return "edited_after_reply"
    return None


def is_dismissed(review, dismissed):
    """Whether the user marked this review as needing no reply.

    A dismissal only covers the review as it was when dismissed: Apple
    re-dates a review when it's edited, so an edit brings it back.
    """
    dismissed_at = dismissed.get(review["id"])
    return (
        dismissed_at is not None
        and parse_date(review["created"]) <= parse_date(dismissed_at)
    )


def earliest(*cutoffs):
    """The earliest cutoff, where None means "no cutoff"."""
    if any(c is None for c in cutoffs):
        return None
    return min(cutoffs)


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    window = parser.add_mutually_exclusive_group()
    window.add_argument(
        "--days", type=int, default=30,
        help="Only reviews from the last N days (default 30).",
    )
    window.add_argument(
        "--all", action="store_true", help="Every review, no date cutoff.",
    )
    parser.add_argument(
        "--new", action="store_true",
        help="Only reviews not seen on a previous --new run; updates the "
             "checkpoint. On the first run, --days sets the baseline window.",
    )
    parser.add_argument(
        "--app", action="append", default=[],
        help="Case-insensitive substring of app name or bundle ID to "
             "include. Repeatable. Default: all apps.",
    )
    parser.add_argument(
        "--reply-lookback-days", type=int,
        default=DEFAULT_REPLY_LOOKBACK_DAYS,
        help="How far back to look for reviews needing a reply, regardless "
             "of the review window (default {}). 0 = all time.".format(
                 DEFAULT_REPLY_LOOKBACK_DAYS),
    )
    parser.add_argument(
        "--dismiss", action="append", default=[], metavar="REVIEW_ID",
        help="Mark a review as needing no reply, hiding it from the "
             "needs-reply list until it's edited again. Repeatable. Only "
             "updates the checkpoint file; fetches nothing.",
    )
    args = parser.parse_args()

    state = load_json(STATE_PATH, {"apps": {}})
    state.setdefault("dismissed", {})

    if args.dismiss:
        dismissed_at = dt.datetime.now(dt.timezone.utc).isoformat()
        for review_id in args.dismiss:
            state["dismissed"][review_id] = dismissed_at
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
        print(json.dumps({"dismissed": args.dismiss, "at": dismissed_at}))
        return 0

    config = load_json(CONFIG_PATH, None)
    required = ("issuer_id", "key_id", "private_key_path")
    if config is None or not all(config.get(k) for k in required):
        print(json.dumps({
            "error": "missing_config",
            "config_path": CONFIG_PATH,
        }))
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    default_cutoff = None if args.all else now - dt.timedelta(days=args.days)
    reply_cutoff = None
    if args.reply_lookback_days > 0:
        reply_cutoff = now - dt.timedelta(days=args.reply_lookback_days)

    first_run = args.new and not state["apps"]

    result = {
        "fetched_at": now.isoformat(),
        "mode": "new" if args.new else "window",
        "window_days": None if args.all else args.days,
        "first_run": first_run,
        "reply_lookback_days": args.reply_lookback_days or None,
        "needs_reply_total": 0,
        "apps": [],
        "error": None,
    }

    try:
        token = make_token(config)
        apps = list_apps(token)
    except (RuntimeError, OSError, subprocess.CalledProcessError,
            ValueError) as e:
        result["error"] = str(e)
        print(json.dumps(result, indent=2))
        return 1

    for app in apps:
        haystack = (app["name"] + " " + app["bundle_id"]).lower()
        if args.app and not any(a.lower() in haystack for a in args.app):
            continue

        app_state = state["apps"].get(app["app_id"]) if args.new else None
        cutoff = default_cutoff
        if app_state is not None and app_state.get("newest_created"):
            cutoff = parse_date(app_state["newest_created"]) - dt.timedelta(
                days=NEW_MODE_OVERLAP_DAYS
            )

        entry = dict(app, needs_reply=[], reviews=[], error=None)
        try:
            fetched = list_reviews(
                token, app["app_id"], earliest(cutoff, reply_cutoff)
            )
        except (RuntimeError, OSError) as e:
            entry["error"] = str(e)
            result["apps"].append(entry)
            continue

        for review in fetched:
            created = parse_date(review["created"])
            if reply_cutoff is not None and created < reply_cutoff:
                continue
            reason = needs_reply_reason(review)
            if reason is not None and not is_dismissed(
                review, state["dismissed"]
            ):
                entry["needs_reply"].append(dict(review, reason=reason))
        result["needs_reply_total"] += len(entry["needs_reply"])

        reviews = [
            r for r in fetched
            if cutoff is None or parse_date(r["created"]) >= cutoff
        ]

        if args.new:
            seen = set(app_state.get("seen_ids", [])) if app_state else set()
            entry["reviews"] = [r for r in reviews if r["id"] not in seen]
            newest = max(
                [r["created"] for r in reviews]
                + ([app_state["newest_created"]]
                   if app_state and app_state.get("newest_created")
                   else []),
                default=None,
                key=lambda d: parse_date(d),
            )
            state["apps"][app["app_id"]] = {
                "name": app["name"],
                "newest_created": newest,
                "seen_ids": sorted(seen | {r["id"] for r in reviews}),
                "checked_at": now.isoformat(),
            }
        else:
            entry["reviews"] = reviews
        result["apps"].append(entry)

    if args.new:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
