#!/usr/bin/env python3
"""Create a store release from an already-uploaded build and submit it for
review, on App Store Connect (iOS) and Google Play (Android).

Commands:
  status <project>   Read-only. Shows, per platform, the uploaded build, the
                     current store versions/tracks, the store's locales, and
                     the screenshots/previews currently on the listing.
  prepare <project>  Creates/updates the release, attaches the build, sets the
                     "What's New" text and media, but doesn't send it for
                     review (Google Play: a draft production release).
  submit <project>   Everything `prepare` does, then submits it for review.
  media <project>    Uploads --media / --play-video-url only: App Store, onto
                     the existing editable --version (no build, notes, or
                     review submission); Google Play, onto the store listing,
                     committed without sending it for review.

Media (--media): a folder or .zip exported by the screenshots tool, laid out
as <ios|android>/<device>/<WxH>/<locale>/<files>. iOS folders may also hold
app preview videos (.mp4/.mov/.m4v), and the App Store product page header
and search results banners (uploaded as PNG). Google Play can't host videos;
its promo video is a YouTube URL (--play-video-url).

No third-party packages: JWTs are signed with the `openssl` CLI.

Credentials:
  * Google Play — GOOGLE_PLAY_JSON_KEY from the project's
    release_credentials.sh (the same file build_and_upload_release.sh uses).
  * App Store Connect — an API key per Apple team in config.json next to
    this script (git-ignored), keyed by APPLE_TEAM_ID:
      {
        "app_store_connect_keys": {
          "ABCDE12345": {
            "issuer_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "key_id": "ABCDE12345",
            "private_key_path": "AuthKey_ABCDE12345.p8"
          }
        }
      }
    A relative private_key_path is resolved against this script's folder.

Output: JSON on stdout (see SKILL.md). A failure on one target is reported
inline so it doesn't hide the others. Exit code 1 if any target failed.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")
ASC_API = "https://api.appstoreconnect.apple.com"
PLAY_API = (
    "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
)
PLAY_UPLOAD_API = (
    "https://androidpublisher.googleapis.com/upload/androidpublisher/v3/"
    "applications"
)

# Apple caps token lifetime at 20 minutes.
ASC_TOKEN_TTL_SECONDS = 19 * 60

WHATS_NEW_LIMITS = {"app_store": 4000, "google_play": 500}

PROJECTS = {
    "anglers-log": {
        "dir": "anglers-log/mobile",
        "apple_bundle_id": "CMA.TheAnglersLog",
        "android_package": "com.cohenadair.anglerslog",
        "platforms": ["ios", "android"],
    },
    "activity-log": {
        "dir": "activity-log/mobile",
        "apple_bundle_id": "com.cohenadair.activitylog",
        "android_package": "com.cohenadair.activitylog",
        "platforms": ["ios", "android"],
    },
    "tapd": {
        "dir": "tapd/mobile",
        "apple_bundle_id": "com.cohenadair.colortap",
        "android_package": "com.cohenadair.colortap",
        "platforms": ["ios", "android"],
    },
}

ASC_PLATFORMS = {"ios": "IOS"}

# A version in one of these states can still be edited and (re)submitted.
ASC_EDITABLE_STATES = {
    "PREPARE_FOR_SUBMISSION", "READY_FOR_REVIEW", "REJECTED",
    "METADATA_REJECTED", "DEVELOPER_REJECTED", "INVALID_BINARY",
}
ASC_LIVE_STATES = {"READY_FOR_DISTRIBUTION", "READY_FOR_SALE"}
ASC_OPEN_SUBMISSION_STATES = (
    "READY_FOR_REVIEW,WAITING_FOR_REVIEW,IN_REVIEW,UNRESOLVED_ISSUES"
)
ASC_RELEASE_TYPES = {"manual": "MANUAL", "after-approval": "AFTER_APPROVAL"}

# ── Media ────────────────────────────────────────────────────────────────────

# Screenshots tool export folder (<platform>/<device>/<WxH>) → store slot.
# iOS: (device, screenshot display type, app preview type). Only Apple's
# required sizes are uploaded — one per device, the first listed that the
# export has — and App Store Connect scales them for every other size.
ASC_MEDIA_SLOTS = {
    "ios/iphone/1320x2868": ("iphone", "APP_IPHONE_67", "IPHONE_67"),
    # 6.5" is only required when there's no 6.9".
    "ios/iphone/1284x2778": ("iphone", "APP_IPHONE_65", "IPHONE_65"),
    "ios/ipad/2064x2752": ("ipad", "APP_IPAD_PRO_3GEN_129",
                           "IPAD_PRO_3GEN_129"),
    "ios/ipad/2048x2732": ("ipad", "APP_IPAD_PRO_3GEN_129",
                           "IPAD_PRO_3GEN_129"),
}
# Google Play: any size in the device folder → image type.
PLAY_MEDIA_SLOTS = {
    "android/android": "phoneScreenshots",
    "android/android-7": "sevenInchScreenshots",
    "android/android-10": "tenInchScreenshots",
    "android/feature-graphic": "featureGraphic",
}
# App Store banners: any size in the device folder → asset library placement
# type, one image per locale. Apple's asset library rejects JPEGs that its
# screenshot sets accept (INVALID_ASSET_FILE_FORMAT), so they're converted
# to PNG before upload.
ASC_BANNER_SLOTS = {
    "ios/app-store-header": "PRODUCT_PAGE_HEADER_ASSET",
    "ios/app-store-search": "APP_STORE_SEARCH_RESULTS_ASSET",
}
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
VIDEO_TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4",
               ".mov": "video/quicktime"}
ASC_MAX_SCREENSHOTS = 10
ASC_MAX_PREVIEWS = 3
PLAY_MAX_IMAGES = {"featureGraphic": 1}
PLAY_MAX_SCREENSHOTS = 8
ASC_ASSET_TIMEOUT_SECONDS = 600


class ApiError(RuntimeError):
    def __init__(self, code, detail):
        super().__init__("HTTP {}: {}".format(code, detail))
        self.code = code


class Stop(RuntimeError):
    """A precondition failed; nothing further is attempted for the target."""


# ── HTTP / auth ──────────────────────────────────────────────────────────────

def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def api(method, url, token, body=None, form=None, raw=None, headers=None):
    """`raw` sends bytes as-is; `headers` adds to or overrides the defaults."""
    headers = dict(headers or {})
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
    elif raw is not None:
        data = raw
    elif method in ("POST", "PUT", "PATCH"):
        data = b""
    request = urllib.request.Request(
        url, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read()
            if not raw.strip():
                return {}
            try:
                return json.loads(raw)
            except ValueError:
                # Upload hosts may answer with a non-JSON body.
                return {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        detail = raw[:500]
        try:
            parsed = json.loads(raw)
            if isinstance(parsed.get("errors"), list):
                detail = "; ".join(
                    "{} {}".format(err.get("title", ""), err.get("detail", ""))
                    for err in parsed["errors"]
                )
            elif isinstance(parsed.get("error"), dict):
                detail = parsed["error"].get("message", detail)
        except ValueError:
            pass
        raise ApiError(e.code, detail.strip())


def openssl_sign(key_path, signing_input):
    with tempfile.NamedTemporaryFile() as f:
        f.write(signing_input.encode())
        f.flush()
        return subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_path, f.name],
            check=True, capture_output=True,
        ).stdout


def der_to_raw_signature(der):
    """Convert an ASN.1 DER ECDSA signature to the raw r||s form JWS wants."""
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


def jwt_signing_input(header, payload):
    return (
        b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url(json.dumps(payload, separators=(",", ":")).encode())
    )


def asc_token(key):
    now = int(time.time())
    signing_input = jwt_signing_input(
        {"alg": "ES256", "kid": key["key_id"], "typ": "JWT"},
        {
            "iss": key["issuer_id"],
            "iat": now,
            "exp": now + ASC_TOKEN_TTL_SECONDS,
            "aud": "appstoreconnect-v1",
        },
    )
    key_path = os.path.join(
        SKILL_DIR, os.path.expanduser(key["private_key_path"])
    )
    der = openssl_sign(key_path, signing_input)
    return signing_input + "." + b64url(der_to_raw_signature(der))


def play_token(json_key_path):
    with open(json_key_path) as f:
        account = json.load(f)
    now = int(time.time())
    signing_input = jwt_signing_input(
        {"alg": "RS256", "typ": "JWT"},
        {
            "iss": account["client_email"],
            "scope": "https://www.googleapis.com/auth/androidpublisher",
            "aud": account["token_uri"],
            "iat": now,
            "exp": now + 3600,
        },
    )
    # NamedTemporaryFile is created 0600, so the key isn't world-readable.
    with tempfile.NamedTemporaryFile() as f:
        f.write(account["private_key"].encode())
        f.flush()
        signature = openssl_sign(f.name, signing_input)
    response = api("POST", account["token_uri"], None, form={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": signing_input + "." + b64url(signature),
    })
    return response["access_token"]


# ── Target resolution ────────────────────────────────────────────────────────

def read_credentials(project_dir):
    """APPLE_TEAM_ID and GOOGLE_PLAY_JSON_KEY from release_credentials.sh.

    Only these two values are read; the Apple ID password never leaves the
    shell.
    """
    script = (
        "source ./release_credentials.sh >/dev/null 2>&1 || exit 3; "
        'printf "%s\\n%s\\n" "${APPLE_TEAM_ID:-}" "${GOOGLE_PLAY_JSON_KEY:-}"'
    )
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=project_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise Stop("release_credentials.sh not found in " + project_dir)
    lines = result.stdout.split("\n")
    json_key = lines[1].strip()
    if json_key and json_key != "TODO" and not os.path.isabs(json_key):
        json_key = os.path.normpath(os.path.join(project_dir, json_key))
    return {"apple_team_id": lines[0].strip(), "google_play_json_key": json_key}


def read_pubspec_version(project_dir):
    with open(os.path.join(project_dir, "pubspec.yaml")) as f:
        match = re.search(r"^version:\s*([^\s+]+)\+(\d+)", f.read(), re.M)
    if match is None:
        raise Stop("No `version: X.Y.Z+BUILD` in pubspec.yaml")
    return match.group(1), match.group(2)


def resolve_targets(args):
    """One dict per platform to act on."""
    project = PROJECTS[args.project]
    project_dir = os.path.join(REPO_ROOT, project["dir"])
    pubspec_version, pubspec_build = read_pubspec_version(project_dir)
    credentials = read_credentials(project_dir)

    targets = []
    for platform in project["platforms"]:
        if args.platform and platform not in args.platform:
            continue
        targets.append({
            "label": platform,
            "platform": platform,
            "version": args.version or pubspec_version,
            "build": args.build or pubspec_build,
            "credentials": credentials,
            "apple_bundle_id": project["apple_bundle_id"],
            "android_package": project["android_package"],
        })
    return targets, {"version": pubspec_version, "build": pubspec_build}


# ── What's New ───────────────────────────────────────────────────────────────

def load_notes(path):
    if path is None:
        return None
    with open(path) as f:
        notes = json.load(f)
    if not isinstance(notes, dict) or not notes:
        raise Stop("Notes file must be a non-empty JSON object")
    return {k.lower(): v.strip() for k, v in notes.items()}


def locale_lookup(mapping, locale):
    """The value for a store locale in a lowercase-keyed mapping: the exact
    locale, then its language. None if neither is there."""
    value = mapping.get(locale.lower())
    if value is None:
        value = mapping.get(locale.split("-")[0].lower())
    return value


def notes_for_locales(notes, locales, store):
    """Map each store locale to its text: exact, then language, then default."""
    resolved = {}
    missing = []
    for locale in locales:
        text = locale_lookup(notes, locale)
        if text is None:
            text = notes.get("default")
        if text is None:
            missing.append(locale)
            continue
        if len(text) > WHATS_NEW_LIMITS[store]:
            raise Stop("What's New for {} is {} characters; limit is {}".format(
                locale, len(text), WHATS_NEW_LIMITS[store]))
        resolved[locale] = text
    if missing:
        raise Stop(
            "No What's New text for store locale(s): {}. Add them (or a "
            "\"default\") to the notes file.".format(", ".join(missing))
        )
    return resolved


# ── Media files ──────────────────────────────────────────────────────────────

def file_digest(path, algorithm):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def media_root(path, scratch):
    """A folder to read media from; a .zip is extracted into `scratch`."""
    path = os.path.abspath(os.path.expanduser(path))
    if os.path.isdir(path):
        return path
    if zipfile.is_zipfile(path):
        root = tempfile.mkdtemp(dir=scratch)
        with zipfile.ZipFile(path) as archive:
            archive.extractall(root)
        return root
    raise Stop("--media must be a folder or a .zip: " + path)


def banner_png(path, scratch):
    """`path` as a PNG, converted into `scratch` with `sips` if needed."""
    if os.path.splitext(path)[1].lower() == ".png":
        return path
    out = os.path.join(
        tempfile.mkdtemp(dir=scratch),
        os.path.splitext(os.path.basename(path))[0] + ".png")
    subprocess.run(["sips", "-s", "format", "png", path, "--out", out],
                   check=True, capture_output=True)
    return out


def load_media(paths, scratch):
    """Index every exported file by store slot and locale.

    Returns {"app_store": {(display_type, preview_type): {locale:
    {"screenshots": [...], "previews": [...]}}}, "app_store_banners":
    {placement_type: {locale: png_path}}, "google_play": {image_type:
    {locale: [...]}}, "ignored": [...]}, locales lowercased, files sorted
    by name.
    """
    files = []
    for path in paths:
        root = media_root(path, scratch)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__MACOSX"]
            for name in filenames:
                if name.startswith("."):
                    continue
                file_path = os.path.join(dirpath, name)
                rel = os.path.relpath(file_path, root).replace(os.sep, "/")
                files.append((rel, file_path))

    # Visit slot folders in ASC_MEDIA_SLOTS order so the first listed size
    # claims its device, then by path.
    folder_rank = {folder: i for i, folder in enumerate(ASC_MEDIA_SLOTS)}
    files.sort(key=lambda f: (
        folder_rank.get("/".join(f[0].split("/")[:3]), 0), f[0]))

    media = {"app_store": {}, "app_store_banners": {}, "google_play": {},
             "ignored": []}
    # (device or Play image type, locale) → the export folder that filled it
    claimed = {}
    for rel, file_path in files:
        parts = rel.split("/")
        ext = os.path.splitext(rel)[1].lower()
        if len(parts) != 5:
            media["ignored"].append(rel + " (unexpected layout)")
            continue
        folder = "/".join(parts[:3])
        locale = parts[3].lower()
        is_video = ext in VIDEO_TYPES
        if ext not in IMAGE_TYPES and not is_video:
            media["ignored"].append(rel + " (not an image or video)")
            continue

        banner_slot = ASC_BANNER_SLOTS.get("/".join(parts[:2]))
        if banner_slot is not None:
            by_locale = media["app_store_banners"].setdefault(banner_slot, {})
            if is_video:
                media["ignored"].append(
                    rel + " (banner videos aren't supported)")
            elif locale in by_locale:
                media["ignored"].append(
                    rel + " (one banner per locale; an earlier file is used)")
            else:
                by_locale[locale] = banner_png(file_path, scratch)
            continue

        asc_slot = ASC_MEDIA_SLOTS.get(folder)
        play_slot = PLAY_MEDIA_SLOTS.get("/".join(parts[:2]))
        if asc_slot is None and play_slot is None:
            media["ignored"].append(rel + (
                " (not a required size; App Store Connect scales it)"
                if parts[:2] in (["ios", "iphone"], ["ios", "ipad"])
                else " (no store slot)"))
            continue
        owner = claimed.setdefault(
            (play_slot if asc_slot is None else asc_slot[0], locale), folder)
        if owner != folder:
            media["ignored"].append(
                "{} (not needed; {} covers this device)".format(rel, owner))
            continue

        if asc_slot is not None:
            entry = media["app_store"].setdefault(
                asc_slot[1:], {}).setdefault(
                locale, {"screenshots": [], "previews": []})
            entry["previews" if is_video else "screenshots"].append(file_path)
        elif is_video:
            media["ignored"].append(
                rel + " (Google Play can't host videos; use --play-video-url)")
        else:
            media["google_play"].setdefault(play_slot, {}).setdefault(
                locale, []).append(file_path)

    for (display_type, _), by_locale in media["app_store"].items():
        for locale, files in by_locale.items():
            if len(files["screenshots"]) > ASC_MAX_SCREENSHOTS:
                raise Stop(
                    "{} {}: {} screenshots; App Store limit is {}".format(
                        display_type, locale, len(files["screenshots"]),
                        ASC_MAX_SCREENSHOTS))
            if len(files["previews"]) > ASC_MAX_PREVIEWS:
                raise Stop("{} {}: {} previews; App Store limit is {}".format(
                    display_type, locale, len(files["previews"]),
                    ASC_MAX_PREVIEWS))
    for image_type, by_locale in media["google_play"].items():
        limit = PLAY_MAX_IMAGES.get(image_type, PLAY_MAX_SCREENSHOTS)
        for locale, files in by_locale.items():
            if len(files) > limit:
                raise Stop("{} {}: {} images; Google Play limit is {}".format(
                    image_type, locale, len(files), limit))
    return media


def media_summary(media):
    """The loaded media as counts, for the JSON output."""
    if media is None:
        return None
    return {
        "app_store": {
            display_type: {
                locale: {k: len(v) for k, v in files.items()}
                for locale, files in sorted(by_locale.items())
            }
            for (display_type, _), by_locale in media["app_store"].items()
        },
        "app_store_banners": {
            placement_type: sorted(by_locale)
            for placement_type, by_locale in
            media["app_store_banners"].items()
        },
        "google_play": {
            image_type: {
                locale: len(files)
                for locale, files in sorted(by_locale.items())
            }
            for image_type, by_locale in media["google_play"].items()
        },
        "ignored": media["ignored"],
    }


# ── App Store Connect ────────────────────────────────────────────────────────

def asc_get(path, token, params=None):
    url = ASC_API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return api("GET", url, token)


def asc_state(attributes):
    return attributes.get("appVersionState") or attributes.get("appStoreState")


def asc_load(target, token):
    """Everything `status` reports, also the starting point for `submit`."""
    platform = ASC_PLATFORMS[target["platform"]]
    bundle_id = target["apple_bundle_id"]
    apps = asc_get("/v1/apps", token, {
        "filter[bundleId]": bundle_id, "fields[apps]": "name,bundleId",
    })["data"]
    apps = [a for a in apps if a["attributes"]["bundleId"] == bundle_id]
    if not apps:
        raise Stop("No App Store Connect app with bundle ID " + bundle_id)
    app = apps[0]

    page = asc_get("/v1/apps/{}/appStoreVersions".format(app["id"]), token, {
        "filter[platform]": platform,
        "limit": 20,
        "include": "build",
        "fields[appStoreVersions]":
            "versionString,appVersionState,appStoreState,releaseType,"
            "createdDate,build",
        "fields[builds]": "version,processingState",
    })
    attached = {
        inc["id"]: inc["attributes"].get("version")
        for inc in page.get("included", []) if inc["type"] == "builds"
    }
    versions = []
    for item in page["data"]:
        build_ref = item.get("relationships", {}).get("build", {}).get("data")
        versions.append({
            "id": item["id"],
            "version": item["attributes"]["versionString"],
            "state": asc_state(item["attributes"]),
            "release_type": item["attributes"].get("releaseType"),
            "created": item["attributes"].get("createdDate"),
            "build": None if build_ref is None
            else attached.get(build_ref["id"]),
        })
    versions.sort(key=lambda v: v["created"] or "", reverse=True)

    builds = asc_get("/v1/builds", token, {
        "filter[app]": app["id"],
        "filter[version]": target["build"],
        "filter[preReleaseVersion.version]": target["version"],
        "filter[preReleaseVersion.platform]": platform,
        "fields[builds]":
            "version,processingState,expired,usesNonExemptEncryption,"
            "uploadedDate",
        "limit": 5,
    })["data"]
    build = None
    if builds:
        build = dict(builds[0]["attributes"], id=builds[0]["id"])

    submissions = asc_get("/v1/reviewSubmissions", token, {
        "filter[app]": app["id"],
        "filter[platform]": platform,
        "filter[state]": ASC_OPEN_SUBMISSION_STATES,
        "fields[reviewSubmissions]": "state,submittedDate",
    })["data"]

    live = next((v for v in versions if v["state"] in ASC_LIVE_STATES), None)
    return {
        "app": app,
        "asc_platform": platform,
        "versions": versions,
        "build": build,
        "live": live,
        "open_submissions": [
            {"id": s["id"], "state": s["attributes"]["state"]}
            for s in submissions
        ],
    }


def asc_localizations(version_id, token):
    return asc_get(
        "/v1/appStoreVersions/{}/appStoreVersionLocalizations".format(
            version_id),
        token,
        {"fields[appStoreVersionLocalizations]": "locale,whatsNew",
         "limit": 200},
    )["data"]


def asc_phased_release(version_id, token):
    try:
        return asc_get(
            "/v1/appStoreVersions/{}/appStoreVersionPhasedRelease".format(
                version_id),
            token,
        ).get("data")
    except ApiError as e:
        if e.code == 404:
            return None
        raise


# Screenshot and app preview sets work the same way under different names.
ASC_SCREENSHOTS = {
    "key": "screenshots", "set_type": "appScreenshotSets",
    "set_attr": "screenshotDisplayType", "asset_type": "appScreenshots",
    "set_rel": "appScreenshotSet", "max": ASC_MAX_SCREENSHOTS,
}
ASC_PREVIEWS = {
    "key": "previews", "set_type": "appPreviewSets",
    "set_attr": "previewType", "asset_type": "appPreviews",
    "set_rel": "appPreviewSet", "max": ASC_MAX_PREVIEWS,
}


def asc_media_sets(localization_id, kind, token):
    """{display/preview type: {"id", "checksums", "complete"}} for a
    localization's screenshot or preview sets."""
    asset_type = kind["asset_type"]
    page = asc_get(
        "/v1/appStoreVersionLocalizations/{}/{}".format(
            localization_id, kind["set_type"]),
        token,
        {
            "include": asset_type,
            "limit": 50,
            "limit[{}]".format(asset_type): kind["max"],
            "fields[{}]".format(asset_type):
                "sourceFileChecksum,assetDeliveryState",
        },
    )
    assets = {
        inc["id"]: inc["attributes"]
        for inc in page.get("included", []) if inc["type"] == asset_type
    }
    sets = {}
    for item in page["data"]:
        refs = item.get("relationships", {}).get(asset_type, {}).get(
            "data") or []
        attributes = [assets.get(ref["id"], {}) for ref in refs]
        sets[item["attributes"][kind["set_attr"]]] = {
            "id": item["id"],
            "checksums": [a.get("sourceFileChecksum") for a in attributes],
            "complete": all(
                (a.get("assetDeliveryState") or {}).get("state") == "COMPLETE"
                for a in attributes
            ),
        }
    return sets


def asc_media_overview(version_id, token):
    """Per locale, how many screenshots/previews each device slot holds."""
    overview = {}
    for loc in asc_localizations(version_id, token):
        overview[loc["attributes"]["locale"]] = {
            kind["key"]: {
                set_value: len(media_set["checksums"])
                for set_value, media_set in sorted(
                    asc_media_sets(loc["id"], kind, token).items())
            }
            for kind in (ASC_SCREENSHOTS, ASC_PREVIEWS)
        }
        overview[loc["attributes"]["locale"]]["banners"] = {
            placement_type: placement["image"].get("fileName")
            for placement_type, placement in sorted(
                asc_banner_placements(loc["id"], token).items())
        }
    return overview


def asc_run_upload_operations(operations, path):
    """Send a reserved asset's bytes to Apple's upload URLs (no token)."""
    with open(path, "rb") as f:
        for operation in operations:
            f.seek(operation["offset"])
            api(operation["method"], operation["url"], None,
                raw=f.read(operation["length"]),
                headers={
                    header["name"]: header["value"]
                    for header in operation.get("requestHeaders") or []
                })


def asc_upload_asset(kind, set_id, path, token):
    """Reserve, upload, and commit one file into a set; returns its id."""
    asset_type = kind["asset_type"]
    attributes = {
        "fileName": os.path.basename(path),
        "fileSize": os.path.getsize(path),
    }
    if kind is ASC_PREVIEWS:
        attributes["mimeType"] = VIDEO_TYPES[os.path.splitext(path)[1].lower()]
    created = api("POST", ASC_API + "/v1/" + asset_type, token, {
        "data": {
            "type": asset_type,
            "attributes": attributes,
            "relationships": {
                kind["set_rel"]: {
                    "data": {"type": kind["set_type"], "id": set_id},
                },
            },
        },
    })["data"]
    asc_run_upload_operations(created["attributes"]["uploadOperations"], path)
    api("PATCH", "{}/v1/{}/{}".format(ASC_API, asset_type, created["id"]),
        token, {
            "data": {
                "type": asset_type,
                "id": created["id"],
                "attributes": {
                    "uploaded": True,
                    "sourceFileChecksum": file_digest(path, "md5"),
                },
            },
        })
    return created["id"]


def asc_wait_for_assets(kind, ids, token):
    """Block until App Store Connect has processed every uploaded file."""
    asset_type = kind["asset_type"]
    deadline = time.time() + ASC_ASSET_TIMEOUT_SECONDS
    pending = list(ids)
    while pending:
        for asset_id in list(pending):
            attributes = asc_get(
                "/v1/{}/{}".format(asset_type, asset_id), token,
                {"fields[{}]".format(asset_type):
                    "fileName,assetDeliveryState"},
            )["data"]["attributes"]
            delivery = attributes.get("assetDeliveryState") or {}
            if delivery.get("state") == "COMPLETE":
                pending.remove(asset_id)
            elif delivery.get("state") == "FAILED":
                raise Stop("App Store Connect rejected {}: {}".format(
                    attributes.get("fileName"),
                    "; ".join(
                        error.get("description") or error.get("code", "")
                        for error in delivery.get("errors") or []
                    ) or "no reason given"))
        if not pending:
            break
        if time.time() > deadline:
            raise Stop("Timed out waiting for App Store Connect to process "
                       "{} {}".format(len(pending), asset_type))
        time.sleep(3)


def asc_replace_set(localization_id, kind, set_value, paths, existing, token):
    """Make a set hold exactly `paths`, in order. Returns the new asset ids,
    or None when the set already holds those files."""
    current = existing.get(set_value)
    if current is not None and current["complete"] and \
            current["checksums"] == [file_digest(p, "md5") for p in paths]:
        return None
    if current is not None:
        api("DELETE", "{}/v1/{}/{}".format(
            ASC_API, kind["set_type"], current["id"]), token)
    set_id = api("POST", ASC_API + "/v1/" + kind["set_type"], token, {
        "data": {
            "type": kind["set_type"],
            "attributes": {kind["set_attr"]: set_value},
            "relationships": {
                "appStoreVersionLocalization": {
                    "data": {
                        "type": "appStoreVersionLocalizations",
                        "id": localization_id,
                    },
                },
            },
        },
    })["data"]["id"]
    ids = [asc_upload_asset(kind, set_id, path, token) for path in paths]
    api("PATCH", "{}/v1/{}/{}/relationships/{}".format(
        ASC_API, kind["set_type"], set_id, kind["asset_type"]),
        token, {"data": [{"type": kind["asset_type"], "id": i} for i in ids]})
    return ids


def asc_apply_media(localizations, media, token):
    """Replace each device slot that `media` has files for, per locale.

    Slots the media doesn't cover are left as they are and reported.
    """
    report = {"replaced": [], "unchanged": [], "other_sets_left_as_is": [],
              "locales_without_media": []}
    uploaded = []
    for loc in localizations:
        locale = loc["attributes"]["locale"]
        had_media = False
        for kind in (ASC_SCREENSHOTS, ASC_PREVIEWS):
            wanted = {}
            for slot, by_locale in media["app_store"].items():
                files = locale_lookup(by_locale, locale)
                if files is not None and files[kind["key"]]:
                    set_value = slot[0] if kind is ASC_SCREENSHOTS else slot[1]
                    wanted[set_value] = files[kind["key"]]
            if not wanted:
                continue
            had_media = True
            existing = asc_media_sets(loc["id"], kind, token)
            for set_value, paths in sorted(wanted.items()):
                label = "{} {}".format(locale, set_value)
                ids = asc_replace_set(
                    loc["id"], kind, set_value, paths, existing, token)
                if ids is None:
                    report["unchanged"].append(label)
                else:
                    report["replaced"].append(
                        "{} ({} {})".format(label, len(ids), kind["key"]))
                    uploaded.append((kind, ids))
            report["other_sets_left_as_is"].extend(
                "{} {}".format(locale, set_value)
                for set_value in sorted(existing) if set_value not in wanted
            )
        if not had_media:
            report["locales_without_media"].append(locale)
    for kind, ids in uploaded:
        asc_wait_for_assets(kind, ids, token)
    return report


def asc_banner_placements(localization_id, token):
    """{placement type: {"id", "image"}} for a localization's banners, where
    "image" is the placed asset library image's attributes."""
    page = asc_get(
        "/v1/appStoreVersionLocalizations/{}/placements".format(
            localization_id),
        token,
        {
            "filter[placementType]": ",".join(ASC_BANNER_SLOTS.values()),
            "include": "image",
            "limit": 50,
        },
    )
    images = {
        inc["id"]: inc["attributes"]
        for inc in page.get("included", [])
        if inc["type"] == "appAssetLibraryImages"
    }
    placements = {}
    for item in page["data"]:
        ref = item.get("relationships", {}).get("image", {}).get("data")
        placements[item["attributes"]["placementType"]] = {
            "id": item["id"],
            "image": {} if ref is None else images.get(ref["id"], {}),
        }
    return placements


def asc_banner_reference_name(path):
    """Asset library images have no checksum, so the reference name carries
    one to tell whether a placed banner is already this file."""
    return "{} ({})".format(
        os.path.basename(path), file_digest(path, "md5")[:12])


def asc_upload_banner(app_id, path, token):
    """Upload one image to the app's asset library and wait for Apple to
    process it. Returns its id."""
    created = api("POST", ASC_API + "/v1/appAssetLibraryImages", token, {
        "data": {
            "type": "appAssetLibraryImages",
            "attributes": {
                "category": "CREATIVE_ASSETS",
                "fileName": os.path.basename(path),
                "fileSize": os.path.getsize(path),
                "referenceName": asc_banner_reference_name(path),
            },
            "relationships": {
                "assetLibrary": {
                    "data": {"type": "appAssetLibraries", "id": app_id},
                },
            },
        },
    })["data"]
    asc_run_upload_operations(created["attributes"]["uploadOperations"], path)
    url = ASC_API + "/v1/appAssetLibraryImages/" + created["id"]
    api("PATCH", url, token, {
        "data": {
            "type": "appAssetLibraryImages",
            "id": created["id"],
            "attributes": {"uploaded": True},
        },
    })
    deadline = time.time() + ASC_ASSET_TIMEOUT_SECONDS
    while True:
        attributes = asc_get(
            "/v1/appAssetLibraryImages/" + created["id"], token,
        )["data"]["attributes"]
        if attributes.get("state") == "FAILED":
            raise Stop("App Store Connect rejected {}: {}".format(
                os.path.basename(path),
                "; ".join(
                    detail.get("description") or detail.get("code", "")
                    for detail in attributes.get("stateDetails") or []
                ) or "no reason given"))
        if attributes.get("imageAsset") is not None:
            return created["id"]
        if time.time() > deadline:
            raise Stop("Timed out waiting for App Store Connect to process "
                       + os.path.basename(path))
        time.sleep(3)


def asc_library_image(app_id, reference_name, token):
    """The id of a processed asset library image with this reference name,
    or None. Apple rejects a second upload under the same name, so a banner
    already uploaded for another locale or version is reused."""
    page = asc_get("/v1/appAssetLibraries/{}/images".format(app_id), token,
                   {"limit": 200})
    while True:
        for item in page["data"]:
            attributes = item["attributes"]
            if attributes.get("referenceName") == reference_name and \
                    attributes.get("imageAsset") is not None and \
                    attributes.get("state") not in ("FAILED", "ARCHIVED"):
                return item["id"]
        next_url = page.get("links", {}).get("next")
        if next_url is None:
            return None
        page = api("GET", next_url, token)


def asc_apply_banners(app_id, localizations, media, token):
    """Place each banner `media` has, per locale, replacing what's there.

    Banners the media doesn't cover are left as they are.
    """
    report = {"replaced": [], "unchanged": [], "locales_without_banners": []}
    for loc in localizations:
        locale = loc["attributes"]["locale"]
        wanted = {
            placement_type: locale_lookup(by_locale, locale)
            for placement_type, by_locale in
            media["app_store_banners"].items()
        }
        wanted = {k: v for k, v in wanted.items() if v is not None}
        if not wanted:
            report["locales_without_banners"].append(locale)
            continue
        existing = asc_banner_placements(loc["id"], token)
        for placement_type, path in sorted(wanted.items()):
            label = "{} {}".format(locale, placement_type)
            current = existing.get(placement_type)
            if current is not None and current["image"].get(
                    "referenceName") == asc_banner_reference_name(path):
                report["unchanged"].append(label)
                continue
            # Upload first, so a rejected file leaves the old banner placed.
            image_id = asc_library_image(
                app_id, asc_banner_reference_name(path), token)
            if image_id is None:
                image_id = asc_upload_banner(app_id, path, token)
            if current is not None:
                api("DELETE", ASC_API + "/v1/appAssetLibraryPlacements/"
                    + current["id"], token)
            api("POST", ASC_API + "/v1/appAssetLibraryPlacements", token, {
                "data": {
                    "type": "appAssetLibraryPlacements",
                    "attributes": {"placementType": placement_type},
                    "relationships": {
                        "image": {
                            "data": {
                                "type": "appAssetLibraryImages",
                                "id": image_id,
                            },
                        },
                        "appStoreVersionLocalization": {
                            "data": {
                                "type": "appStoreVersionLocalizations",
                                "id": loc["id"],
                            },
                        },
                    },
                },
            })
            report["replaced"].append(label)
    return report


def asc_status(target, token):
    loaded = asc_load(target, token)
    live = loaded["live"]
    locales_from = next(
        (v for v in loaded["versions"] if v["version"] == target["version"]),
        live or (loaded["versions"][0] if loaded["versions"] else None),
    )
    locales = []
    media = None
    if locales_from is not None:
        locales = sorted(
            loc["attributes"]["locale"]
            for loc in asc_localizations(locales_from["id"], token)
        )
        media = {
            "of_version": locales_from["version"],
            "by_locale": asc_media_overview(locales_from["id"], token),
        }
    return {
        "app_name": loaded["app"]["attributes"]["name"],
        "build": loaded["build"],
        "versions": loaded["versions"][:5],
        "live_version": None if live is None else live["version"],
        "live_release_type": None if live is None else live["release_type"],
        "live_was_phased": None if live is None
        else asc_phased_release(live["id"], token) is not None,
        "open_review_submissions": loaded["open_submissions"],
        "locales": locales,
        "media": media,
    }


def asc_media(target, token, media):
    """Upload media onto an existing editable version, changing nothing
    else."""
    loaded = asc_load(target, token)
    version = next(
        (v for v in loaded["versions"] if v["version"] == target["version"]),
        None,
    )
    if version is None:
        raise Stop("Version {} isn't on App Store Connect; create it first "
                   "(prepare)".format(target["version"]))
    if version["state"] not in ASC_EDITABLE_STATES:
        raise Stop("Version {} is {}; its media can't be changed".format(
            target["version"], version["state"]))

    actions = []
    media_report = None
    localizations = asc_localizations(version["id"], token)
    if media["app_store"]:
        media_report = asc_apply_media(localizations, media, token)
        actions.append("replaced {} media set(s), {} already up to date"
                       .format(len(media_report["replaced"]),
                               len(media_report["unchanged"])))
    if media["app_store_banners"]:
        banner_report = asc_apply_banners(
            loaded["app"]["id"], localizations, media, token)
        media_report = dict(media_report or {}, banners=banner_report)
        actions.append("replaced {} banner(s), {} already up to date".format(
            len(banner_report["replaced"]), len(banner_report["unchanged"])))
    return {"result": "media_uploaded", "actions": actions,
            "media": media_report}


def asc_submit(target, token, notes, media, args):
    loaded = asc_load(target, token)
    app_id = loaded["app"]["id"]
    platform = loaded["asc_platform"]
    actions = []

    build = loaded["build"]
    if build is None:
        raise Stop("Build {} ({}) not found on App Store Connect".format(
            target["version"], target["build"]))
    if build.get("processingState") != "VALID":
        raise Stop("Build is {}, not VALID — wait for processing".format(
            build.get("processingState")))
    if build.get("expired"):
        raise Stop("Build has expired")
    if build.get("usesNonExemptEncryption") is None:
        raise Stop(
            "Build has no export compliance answer; set it in App Store "
            "Connect (or ITSAppUsesNonExemptEncryption in Info.plist)"
        )

    live = loaded["live"]
    version = next(
        (v for v in loaded["versions"] if v["version"] == target["version"]),
        None,
    )
    if version is not None and version["state"] not in ASC_EDITABLE_STATES:
        return {"result": "already_" + version["state"].lower(), "actions": []}

    release_type = ASC_RELEASE_TYPES.get(args.release_type or "")
    created = False
    if version is None:
        if release_type is None:
            # Mirror the live version; a past SCHEDULED date can't be
            # reused, so fall back to the option that releases nothing.
            release_type = "AFTER_APPROVAL" if live is None \
                else live["release_type"]
            if release_type not in ASC_RELEASE_TYPES.values():
                release_type = "MANUAL"
        editable = next(
            (v for v in loaded["versions"]
             if v["state"] in ASC_EDITABLE_STATES),
            None,
        )
        if editable is None:
            response = api("POST", ASC_API + "/v1/appStoreVersions", token, {
                "data": {
                    "type": "appStoreVersions",
                    "attributes": {
                        "platform": platform,
                        "versionString": target["version"],
                        "releaseType": release_type,
                    },
                    "relationships": {
                        "app": {"data": {"type": "apps", "id": app_id}},
                    },
                },
            })
            version = {"id": response["data"]["id"]}
            created = True
            actions.append("created version " + target["version"])
        else:
            # Only one editable version can exist per platform.
            api("PATCH", ASC_API + "/v1/appStoreVersions/" + editable["id"],
                token, {
                    "data": {
                        "type": "appStoreVersions",
                        "id": editable["id"],
                        "attributes": {
                            "versionString": target["version"],
                            "releaseType": release_type,
                        },
                    },
                })
            version = editable
            actions.append("renamed unreleased version {} to {}".format(
                editable["version"], target["version"]))
    elif release_type is None:
        release_type = version["release_type"]
    elif release_type != version["release_type"]:
        api("PATCH", ASC_API + "/v1/appStoreVersions/" + version["id"],
            token, {
                "data": {
                    "type": "appStoreVersions",
                    "id": version["id"],
                    "attributes": {"releaseType": release_type},
                },
            })
        actions.append("set release type " + release_type)
    version_id = version["id"]

    api("PATCH",
        "{}/v1/appStoreVersions/{}/relationships/build".format(
            ASC_API, version_id),
        token, {"data": {"type": "builds", "id": build["id"]}})
    actions.append("attached build " + target["build"])

    localizations = asc_localizations(version_id, token)
    if notes is not None:
        texts = notes_for_locales(
            notes, [loc["attributes"]["locale"] for loc in localizations],
            "app_store",
        )
        for loc in localizations:
            api("PATCH",
                ASC_API + "/v1/appStoreVersionLocalizations/" + loc["id"],
                token, {
                    "data": {
                        "type": "appStoreVersionLocalizations",
                        "id": loc["id"],
                        "attributes": {
                            "whatsNew": texts[loc["attributes"]["locale"]],
                        },
                    },
                })
        actions.append("set What's New for " + ", ".join(sorted(texts)))
    else:
        missing = sorted(
            loc["attributes"]["locale"] for loc in localizations
            if not (loc["attributes"].get("whatsNew") or "").strip()
        )
        if missing and args.command == "submit":
            raise Stop("No --notes-file, and What's New is empty for: " +
                       ", ".join(missing))
        actions.append(
            "What's New left as is" + (
                " (empty for {})".format(", ".join(missing))
                if missing else ""))

    media_report = None
    if media is not None and media["app_store"]:
        media_report = asc_apply_media(localizations, media, token)
        actions.append("replaced {} media set(s), {} already up to date"
                       .format(len(media_report["replaced"]),
                               len(media_report["unchanged"])))
    if media is not None and media["app_store_banners"]:
        banner_report = asc_apply_banners(app_id, localizations, media, token)
        media_report = dict(media_report or {}, banners=banner_report)
        actions.append("replaced {} banner(s), {} already up to date".format(
            len(banner_report["replaced"]), len(banner_report["unchanged"])))

    phased = asc_phased_release(version_id, token)
    want_phased = args.phased
    if want_phased is None:
        # Mirror the live version on a new version; otherwise leave as is.
        want_phased = phased is not None
        if created and live is not None:
            want_phased = asc_phased_release(live["id"], token) is not None
    if want_phased and phased is None:
        api("POST", ASC_API + "/v1/appStoreVersionPhasedReleases", token, {
            "data": {
                "type": "appStoreVersionPhasedReleases",
                "attributes": {"phasedReleaseState": "INACTIVE"},
                "relationships": {
                    "appStoreVersion": {
                        "data": {"type": "appStoreVersions", "id": version_id},
                    },
                },
            },
        })
        actions.append("enabled phased release")
    elif not want_phased and phased is not None:
        api("DELETE",
            ASC_API + "/v1/appStoreVersionPhasedReleases/" + phased["id"],
            token)
        actions.append("disabled phased release")

    summary = {
        "actions": actions,
        "release_type": release_type,
        "phased_release": want_phased,
        "media": media_report,
    }
    if args.command == "prepare":
        return dict(summary, result="prepared")

    blocking = [
        s for s in loaded["open_submissions"]
        if s["state"] != "READY_FOR_REVIEW"
    ]
    if blocking:
        raise Stop(
            "Version is prepared but not submitted: a review submission is "
            "already {}. Resolve it in App Store Connect first.".format(
                blocking[0]["state"])
        )
    drafts = [
        s for s in loaded["open_submissions"]
        if s["state"] == "READY_FOR_REVIEW"
    ]
    has_item = False
    if drafts:
        submission_id = drafts[0]["id"]
        items = asc_get(
            "/v1/reviewSubmissions/{}/items".format(submission_id), token,
            {"include": "appStoreVersion", "limit": 50},
        )["data"]
        for item in items:
            ref = item.get("relationships", {}).get(
                "appStoreVersion", {}).get("data")
            if ref is not None and ref["id"] == version_id:
                has_item = True
            else:
                raise Stop(
                    "Version is prepared but not submitted: the draft review "
                    "submission holds other items. Review it in App Store "
                    "Connect."
                )
    else:
        submission_id = api(
            "POST", ASC_API + "/v1/reviewSubmissions", token, {
                "data": {
                    "type": "reviewSubmissions",
                    "attributes": {"platform": platform},
                    "relationships": {
                        "app": {"data": {"type": "apps", "id": app_id}},
                    },
                },
            })["data"]["id"]
    if not has_item:
        api("POST", ASC_API + "/v1/reviewSubmissionItems", token, {
            "data": {
                "type": "reviewSubmissionItems",
                "relationships": {
                    "reviewSubmission": {
                        "data": {
                            "type": "reviewSubmissions", "id": submission_id,
                        },
                    },
                    "appStoreVersion": {
                        "data": {"type": "appStoreVersions", "id": version_id},
                    },
                },
            },
        })
    api("PATCH", ASC_API + "/v1/reviewSubmissions/" + submission_id, token, {
        "data": {
            "type": "reviewSubmissions",
            "id": submission_id,
            "attributes": {"submitted": True},
        },
    })
    actions.append("submitted for review")
    return dict(summary, result="submitted")


# ── Google Play ──────────────────────────────────────────────────────────────

class PlayEdit:
    """An open edit, discarded on exit unless it was committed."""

    def __init__(self, package, token):
        self.base = "{}/{}/edits".format(PLAY_API, package)
        self.upload_base = "{}/{}/edits".format(PLAY_UPLOAD_API, package)
        self.token = token
        self.committed = False

    def __enter__(self):
        self.id = api("POST", self.base, self.token)["id"]
        return self

    def __exit__(self, *_):
        if not self.committed:
            try:
                api("DELETE", "{}/{}".format(self.base, self.id), self.token)
            except (ApiError, OSError):
                pass

    def call(self, method, path, body=None):
        return api(method, "{}/{}{}".format(self.base, self.id, path),
                   self.token, body)

    def tracks(self):
        return self.call("GET", "/tracks").get("tracks", [])

    def listings(self):
        return self.call("GET", "/listings").get("listings", [])

    def locales(self):
        return sorted(listing["language"] for listing in self.listings())

    def images(self, locale, image_type):
        return self.call("GET", "/listings/{}/{}".format(
            locale, image_type)).get("images", [])

    def upload_image(self, locale, image_type, path):
        with open(path, "rb") as f:
            data = f.read()
        api("POST", "{}/{}/listings/{}/{}?uploadType=media".format(
            self.upload_base, self.id, locale, image_type),
            self.token, raw=data,
            headers={"Content-Type":
                     IMAGE_TYPES[os.path.splitext(path)[1].lower()]})


def play_tracks_summary(tracks):
    return [
        {
            "track": track["track"],
            "releases": [
                {
                    "name": release.get("name"),
                    "status": release.get("status"),
                    "version_codes": release.get("versionCodes", []),
                    "user_fraction": release.get("userFraction"),
                }
                for release in track.get("releases", [])
            ],
        }
        for track in tracks
    ]


def play_find(tracks, version_code):
    """Track name → release status, for every release holding the code."""
    return {
        track["track"]: release.get("status")
        for track in tracks
        for release in track.get("releases", [])
        if version_code in release.get("versionCodes", [])
    }


def play_status(target, token):
    with PlayEdit(target["android_package"], token) as edit:
        tracks = edit.tracks()
        listings = edit.listings()
        return {
            "build_found_in": play_find(tracks, target["build"]),
            "tracks": play_tracks_summary(tracks),
            "locales": sorted(listing["language"] for listing in listings),
            "media": {
                listing["language"]: dict(
                    {
                        image_type: len(edit.images(
                            listing["language"], image_type))
                        for image_type in PLAY_MEDIA_SLOTS.values()
                    },
                    video=listing.get("video") or None,
                )
                for listing in listings
            },
        }


def play_apply_media(edit, listings, media, video_url):
    """Replace each image type `media` has files for, per listing locale,
    and set the promo video URL. Returns a report like asc_apply_media's."""
    report = {"replaced": [], "unchanged": [], "locales_without_media": []}
    for listing in listings:
        locale = listing["language"]
        had_media = False
        for image_type, by_locale in sorted(media["google_play"].items()):
            paths = locale_lookup(by_locale, locale)
            if not paths:
                continue
            had_media = True
            label = "{} {}".format(locale, image_type)
            current = [i.get("sha256") for i in edit.images(locale, image_type)]
            if current == [file_digest(p, "sha256") for p in paths]:
                report["unchanged"].append(label)
                continue
            edit.call("DELETE", "/listings/{}/{}".format(locale, image_type))
            for path in paths:
                edit.upload_image(locale, image_type, path)
            report["replaced"].append("{} ({} images)".format(
                label, len(paths)))
        if video_url is not None:
            had_media = True
            label = "{} video".format(locale)
            if listing.get("video") == video_url:
                report["unchanged"].append(label)
            else:
                edit.call("PATCH", "/listings/" + locale, {"video": video_url})
                report["replaced"].append(label)
        if not had_media:
            report["locales_without_media"].append(locale)
    return report


def play_media(target, token, media, args):
    """Update the store listing's media, committed without sending it for
    review. Google Play only allows that while the app already has changes
    waiting to be sent from the Play Console (e.g. after a rejection);
    managed publishing doesn't affect it. With --play-send-for-review, the
    edit is committed normally, which sends it for review."""
    with PlayEdit(target["android_package"], token) as edit:
        media_report = play_apply_media(
            edit, edit.listings(), media or {"google_play": {}},
            args.play_video_url)
        if args.play_send_for_review:
            edit.call("POST", ":commit")
            edit.committed = True
            return {
                "result": "media_sent_for_review",
                "actions": ["replaced {} listing asset(s), {} already up to "
                            "date; sent for review".format(
                                len(media_report["replaced"]),
                                len(media_report["unchanged"]))],
                "media": media_report,
            }
        try:
            edit.call("POST", ":commit?changesNotSentForReview=true")
        except ApiError as e:
            if e.code == 400 and "sent for review automatically" in str(e):
                raise Stop(
                    "Google Play sends this app's changes for review "
                    "automatically, so media can't be committed through the "
                    "API without submitting it. Nothing was changed. Upload "
                    "the images in the Play Console, or re-run with "
                    "--play-send-for-review.")
            raise
        edit.committed = True
        return {
            "result": "media_uploaded",
            "actions": ["replaced {} listing asset(s), {} already up to date; "
                        "not sent for review".format(
                            len(media_report["replaced"]),
                            len(media_report["unchanged"]))],
            "media": media_report,
        }


def play_production_release(tracks, version_code):
    """The production release holding this version code, if any."""
    for track in tracks:
        if track["track"] != "production":
            continue
        for release in track.get("releases", []):
            if version_code in release.get("versionCodes", []):
                return release
    return None


def play_submit(target, token, notes, media, args):
    with PlayEdit(target["android_package"], token) as edit:
        tracks = edit.tracks()
        found = play_find(tracks, target["build"])
        if not found:
            raise Stop("Version code {} isn't on any Google Play track".format(
                target["build"]))
        if found.get("production") in ("completed", "inProgress", "halted"):
            return {
                "result": "already_" + found["production"].lower(),
                "actions": [],
            }

        actions = []
        listings = edit.listings()
        release = {"versionCodes": [target["build"]]}
        if notes is not None:
            texts = notes_for_locales(
                notes, sorted(listing["language"] for listing in listings),
                "google_play")
            release["releaseNotes"] = [
                {"language": locale, "text": text}
                for locale, text in sorted(texts.items())
            ]
            actions.append("set What's New for " + ", ".join(sorted(texts)))
        else:
            # Reuse the notes of an earlier `prepare` (a draft release).
            existing = play_production_release(tracks, target["build"])
            existing_notes = [] if existing is None \
                else existing.get("releaseNotes", [])
            if not existing_notes and args.command == "submit":
                raise Stop("No --notes-file, and no prepared release notes "
                           "to reuse")
            if existing_notes:
                release["releaseNotes"] = existing_notes
            actions.append("What's New left as is")

        # Store listing changes go live as soon as they're approved, not with
        # the release, so they're only sent with `submit`.
        wants_media = args.play_video_url is not None or (
            media is not None and media["google_play"])
        media_report = None
        if wants_media and args.command == "submit":
            media_report = play_apply_media(
                edit, listings, media or {"google_play": {}},
                args.play_video_url)
            actions.append("replaced {} listing asset(s), {} already up to "
                           "date".format(len(media_report["replaced"]),
                                         len(media_report["unchanged"])))
        elif wants_media:
            actions.append("media not uploaded: Google Play publishes "
                           "listing changes on approval, separately from the "
                           "release — pass it to `submit` instead")

        if args.command == "prepare":
            release["status"] = "draft"
        elif args.rollout_fraction < 1:
            release["status"] = "inProgress"
            release["userFraction"] = args.rollout_fraction
        else:
            release["status"] = "completed"
        edit.call("PUT", "/tracks/production", {
            "track": "production", "releases": [release],
        })
        edit.call("POST", ":commit")
        edit.committed = True
        actions.append("production release {} ({})".format(
            release["status"], target["build"]))
        prepared = args.command == "prepare"
        return {
            "result": "prepared" if prepared else "submitted",
            "actions": actions,
            "rollout_fraction": None if prepared else args.rollout_fraction,
            "media": media_report,
        }


# ── Entry point ──────────────────────────────────────────────────────────────

def run_target(target, args, notes, media, config):
    if target["platform"] == "android":
        key_path = target["credentials"]["google_play_json_key"]
        if not key_path or key_path == "TODO":
            raise Stop("GOOGLE_PLAY_JSON_KEY isn't set in "
                       "release_credentials.sh")
        token = play_token(key_path)
        if args.command == "status":
            return play_status(target, token)
        if args.command == "media":
            return play_media(target, token, media, args)
        return play_submit(target, token, notes, media, args)

    team_id = target["credentials"]["apple_team_id"]
    key = config.get("app_store_connect_keys", {}).get(team_id)
    required = ("issuer_id", "key_id", "private_key_path")
    if key is None or not all(key.get(k) for k in required):
        raise Stop("missing_asc_key: no App Store Connect API key for team "
                   "{} in {}".format(team_id, CONFIG_PATH))
    token = asc_token(key)
    if args.command == "status":
        return asc_status(target, token)
    if args.command == "media":
        if media is None:
            return {"result": "skipped", "actions": ["no --media"]}
        return asc_media(target, token, media)
    return asc_submit(target, token, notes, media, args)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "command", choices=["status", "prepare", "submit", "media"])
    parser.add_argument("project", choices=sorted(PROJECTS))
    parser.add_argument(
        "--platform", action="append", default=[],
        choices=["ios", "android"],
        help="Repeatable. Default: every platform the project ships.",
    )
    parser.add_argument("--version", help="X.Y.Z. Default: pubspec.yaml.")
    parser.add_argument(
        "--build", help="Build number / version code. Default: pubspec.yaml.",
    )
    parser.add_argument(
        "--notes-file",
        help="JSON object of locale → What's New text. If omitted, the "
             "release's current text is kept (submit fails if it's empty).",
    )
    parser.add_argument(
        "--media", action="append", default=[],
        help="Repeatable. Screenshots tool export (folder or .zip). Each "
             "device slot/locale it has files for is replaced; others are "
             "left alone. Google Play media is only sent with submit.",
    )
    parser.add_argument(
        "--play-video-url",
        help="Google Play: YouTube promo video URL for every listing locale. "
             "Only sent with submit.",
    )
    parser.add_argument(
        "--play-send-for-review", action="store_true",
        help="media only: commit the Google Play listing changes normally, "
             "which sends them for review.",
    )
    parser.add_argument(
        "--release-type", choices=sorted(ASC_RELEASE_TYPES),
        help="App Store: release manually or automatically after approval. "
             "Default: same as the live version.",
    )
    phased = parser.add_mutually_exclusive_group()
    phased.add_argument(
        "--phased", dest="phased", action="store_true", default=None,
        help="App Store: 7-day phased release. Default: same as the live "
             "version.",
    )
    phased.add_argument("--no-phased", dest="phased", action="store_false")
    parser.add_argument(
        "--rollout-fraction", type=float, default=1.0,
        help="Google Play: staged rollout fraction, 0 < f <= 1 (default 1).",
    )
    args = parser.parse_args()

    if not 0 < args.rollout_fraction <= 1:
        parser.error("--rollout-fraction must be in (0, 1]")
    if args.command == "status" and (
            args.notes_file or args.media or args.play_video_url):
        parser.error("status doesn't take --notes-file, --media, or "
                     "--play-video-url")
    if args.command == "media":
        if args.notes_file:
            parser.error("media doesn't take --notes-file")
        if not args.media and not args.play_video_url:
            parser.error("media needs --media and/or --play-video-url")
    elif args.play_send_for_review:
        parser.error("--play-send-for-review only applies to media")

    with tempfile.TemporaryDirectory() as scratch:
        return run(args, scratch)


def run(args, scratch):
    result = {"command": args.command, "project": args.project,
              "targets": [], "error": None}
    try:
        notes = load_notes(args.notes_file)
        media = load_media(args.media, scratch) if args.media else None
        result["media_found"] = media_summary(media)
        targets, pubspec = resolve_targets(args)
        if not targets:
            raise Stop("No matching platforms for this project")
        config = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                config = json.load(f)
    except (Stop, OSError, ValueError, zipfile.BadZipFile,
            subprocess.CalledProcessError) as e:
        result["error"] = str(e)
        print(json.dumps(result, indent=2))
        return 1
    result["pubspec"] = pubspec

    failed = False
    for target in targets:
        entry = {
            "target": target["label"],
            "store": "google_play" if target["platform"] == "android"
            else "app_store",
            "app": target["android_package"]
            if target["platform"] == "android" else target["apple_bundle_id"],
            "version": target["version"],
            "build": target["build"],
            "error": None,
        }
        try:
            entry.update(run_target(target, args, notes, media, config))
        except (Stop, ApiError, OSError, ValueError, KeyError,
                subprocess.CalledProcessError) as e:
            entry["error"] = str(e) or type(e).__name__
            failed = True
        result["targets"].append(entry)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
