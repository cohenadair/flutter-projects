---
name: app-store-reviews
description: >
  Weekly App Store review check for every published app on the personal
  Apple Developer team (anglers-log, activity-log, tapd, and anything else
  on that team — not pro-iq), via the App Store Connect API. Always calls
  out reviews that still need a reply (never answered, or edited after the
  reply) first, then summarizes reviews. Two modes: Update Me mode (only
  reviews not seen on the last run — the weekly check) and Summary mode
  (reviews from a time window, or all reviews). Use Update Me mode when the
  user says "check my reviews", "weekly review check", "any new reviews",
  "update me on reviews", "new reviews since last time", or similar. Use
  Summary mode when the user says "fetch App Store reviews", "show my app
  reviews", "what are people saying about <app>", "summarize reviews from
  the last 90 days", "any 1-star reviews", or "which reviews haven't I
  replied to". Read-only: never posts replies to reviews.
---

# App Store Reviews

The main job of this skill is to **replace the user's manual weekly review
check**: surface every review that still needs a reply, then show what's
new. Fetches with `fetch_reviews.py` (next to this file); no dependencies
beyond `python3` and `openssl`.

Read-only. **Never** post a review response (`POST
/v1/customerReviewResponses`) — that's publicly visible. If the user wants to
reply, draft the text in chat and let them post it themselves in App Store
Connect.

## Choosing a mode

- The weekly check ("check my reviews", "weekly review check") or *new
  since last time* ("any new reviews", "update me") → **Update Me**
  (`--new`). Using the checkpoint instead of a fixed 7-day window means a
  skipped week doesn't lose anything.
- Anything else (a window, a specific app, low ratings, "all reviews") →
  **Summary**.
- "Which reviews haven't I replied to" / "unanswered reviews" → **Summary**
  with default flags, presenting only the **Needs reply** section. Add
  `--reply-lookback-days 0` if they ask for all time / the full backlog.

## Step 1 — Run the script

```bash
python3 .claude/skills/app-store-reviews/fetch_reviews.py [flags]
```

| Flag | Meaning |
|---|---|
| `--days N` | Reviews from the last N days (default 30). |
| `--all` | Every review, no cutoff. Can be slow for anglers-log. |
| `--new` | Update Me mode: only reviews not seen on a previous `--new` run. Writes the checkpoint. |
| `--app X` | Only apps whose name or bundle ID contains `X` (case-insensitive). Repeatable. |
| `--reply-lookback-days N` | How far back the needs-reply list looks, independent of the review window (default 365). `0` = all time. |
| `--dismiss REVIEW_ID` | Mark a review as needing no reply (repeatable). Only writes `state.json`; fetches nothing. See **Dismissing**. |

Map the request: "last 3 months" → `--days 90`, "Anglers' Log reviews" →
`--app angler`, "check my reviews" → `--new`. Don't pass `--new` in Summary
mode — it would silently advance the checkpoint.

The needs-reply list deliberately ignores the review window and the `--new`
checkpoint: an unanswered review stays on it every run until the user
replies. The default 365-day look-back keeps out the pre-2022 backlog (~40
never-answered reviews from 2015–2021 as of Sep 2026); only include that
backlog when asked.

## Step 2 — Handle errors

- `{"error": "missing_config"}` (exit 2) → walk the user through **Setup**
  below. Don't create the config with placeholder values.
- Top-level `error` (exit 1) → the key failed entirely. `HTTP 401` usually
  means a wrong key/issuer ID or a revoked key; `HTTP 403` means the key's
  role can't read reviews. An `openssl` error means a bad `.p8` path.
- `apps[].error` → that one app failed; report it and summarize the rest.
  Say explicitly that its needs-reply list couldn't be checked. In `--new`
  mode the failed app's checkpoint isn't advanced, so its reviews will show
  up on the next successful run.

## Step 3 — Summarize

Output shape:

```json
{
  "mode": "window" | "new",
  "window_days": 30,
  "first_run": false,
  "reply_lookback_days": 365,
  "needs_reply_total": 1,
  "apps": [{
    "app_id": "959989008", "name": "...",
    "bundle_id": "...", "error": null,
    "needs_reply": [{ ...review, "reason": "no_reply" | "edited_after_reply" }],
    "reviews": [{
      "id": "...", "rating": 1-5, "title": "...", "body": "...",
      "reviewer": "...", "created": "ISO-8601", "territory": "USA",
      "response": null | {"responseBody": "...", "lastModifiedDate": "ISO-8601", "state": "PUBLISHED" | "PENDING_PUBLISH"}
    }]
  }],
  "error": null
}
```

`reason`:
- `no_reply` — no response at all.
- `edited_after_reply` — the reply is published but older than the review's
  `created` date. Apple re-dates a review when the reviewer edits it, so the
  review text changed after the user answered; the reply may no longer fit.

A response in `PENDING_PUBLISH` counts as answered (not in `needs_reply`);
mark it "reply pending" wherever the review is shown.

Present, in this order:

1. **Needs reply** — always first, always present. If `needs_reply_total`
   is 0, one line: "✅ All reviews from the last <N> days have replies."
   Otherwise a heading with the count, then every entry across all apps,
   oldest first (longest-waiting at the top), each as:
   `App — ★★☆☆☆ Title — reviewer, territory, date (N days ago)`, the full
   body (trim over ~400 chars with "…"), and for `edited_after_reply` the
   label **Edited after your reply** plus the current reply text and its
   date so the user can judge whether it still fits. Include entries even if
   they're older than the review window or were seen on a previous `--new`
   run. Offer to draft replies (in chat only), and for `edited_after_reply`
   entries also offer to mark the existing reply as fine (see
   **Dismissing**).
2. **Overview table**, one row per app for the window/new reviews: review
   count, average rating, 1–2★ count, and needs-reply count. Omit apps with
   zero reviews and zero needs-reply from the table, but list their names in
   one line below it so the user knows they were checked.
3. **New/window reviews per app**, newest first:
   `★★☆☆☆ Title — reviewer, territory, date`, then the body. Mark each as
   replied / reply pending / **needs reply** — don't repeat the full body of
   anything already shown in section 1, just reference it.
4. **Themes**: 2–5 bullets per app on recurring complaints/requests (bugs,
   crashes, missing features, pricing, sync). Where a complaint points at a
   likely code area in this repo, name it — but don't go investigating
   unless asked. Skip this section when there are fewer than ~3 reviews.
5. For large result sets (more than ~40 reviews), show sections 1–2, themes,
   and only the 1–3★ reviews in full; offer the rest on request.

Update Me mode: after section 1, lead section 2 with "N new reviews since
<previous check>" (or "No new reviews"). If `first_run` is true, say this
run set the baseline and treated the last `--days` window as new.

## Dismissing

When the user says a needs-reply review is fine as-is ("the current reply is
fine", "I'm not replying to that one"), run `--dismiss <review id>` with the
`id` from the output, then confirm it's off the list. Dismissals are keyed
by review ID and time: if the reviewer edits the review again, it reappears.
Only dismiss reviews the user explicitly names — never in bulk on your own
initiative.

## Setup (first run only)

Reviews come from the personal team (`RQ74DU9PML`, the Xcode
`DEVELOPMENT_TEAM` for anglers-log, activity-log, and tapd). pro-iq is on a
separate team (`5H63B7B676`) and is out of scope — its apps won't appear.

The user must:

1. App Store Connect → Users and Access → Integrations → App Store Connect
   API → **Team Keys** → generate a key with the **Customer Support** role
   (the least-privileged role that can read reviews).
2. Download the `.p8` (possible only once) into this skill's folder, and
   note the **Key ID** and the **Issuer ID** shown at the top of that page.

The user generates and downloads the key themselves. Once they give you the
IDs and file name, write `config.json` in this skill's folder
(`private_key_path` is relative to the folder):

```json
{
  "issuer_id": "…",
  "key_id": "…",
  "private_key_path": "AuthKey_XXXXXXXXXX.p8"
}
```

The repo root `.gitignore` excludes this folder's `config.json`,
`state.json`, and `*.p8`.
Never commit them (no `git add -f`), never remove those ignore rules, and
never print the `.p8` contents. `chmod 600` the key and config.

Ignored files aren't copied into new git worktrees, so running from a
worktree reports `missing_config`. Tell the user to run from the main
checkout (or copy `config.json` and the `.p8` into the worktree's skill
folder) — don't recreate the config there.

## State

`state.json` in this skill's folder holds `--new`'s per-app checkpoints
(newest review date plus IDs seen) and the `dismissed` map (review ID →
dismissal time). Each run re-fetches from 7 days before
the newest review seen and dedups by ID, so reviews near the boundary aren't
missed. Delete the file to reset the baseline.
