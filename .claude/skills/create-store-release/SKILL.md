---
name: create-store-release
description: >
  Creates the store release for a build that's already uploaded and submits
  it for app review — a new App Store Connect version (iOS) and a Google
  Play production release (Android) — via the store APIs, replacing
  the manual steps in both consoles. Can also stop short of submitting
  (Prepare mode), and upload screenshots, app preview videos, the App Store
  header/search banners, and the feature graphic exported by the
  screenshots tool. Use when the user says
  things like "submit anglers-log for review", "submit the release",
  "publish the release", "create the store releases", "promote to
  production", "send 2.8.1 to app review", "create the release but don't
  submit it", "prepare the release", "set up 2.8.1 in the stores",
  "upload the new screenshots", or asks what state a release is in on the
  stores ("is tapd in review yet?"). Works for anglers-log, activity-log, and
  tapd only — not pro-iq, whose releases are created manually. This skill
  never builds or uploads anything — that is `build-and-upload-release`,
  which is run (and release-tested) beforehand; don't chain into this skill
  from it unless the user asks.
---

# create-store-release Skill

Takes a build that `build-and-upload-release` already put on App Store
Connect / Google Play's internal track and turns it into a release that's
submitted for review. Everything goes through `create_store_release.py`
(next to this file); no dependencies beyond `python3` and `openssl`.

## Modes

| Mode | Command | Ends with |
|---|---|---|
| **Status** — "is tapd in review yet?" | `status` | A report; nothing changes. |
| **Prepare** — "create the release but don't submit it" | `prepare` | App Store version in "Prepare for Submission"; Google Play **draft** production release. Nobody sees it. |
| **Submit** — "submit the release" (default) | `submit` | Both sent for review. |

`prepare` followed later by `submit` is a normal flow: `submit` picks up
the prepared release and, without `--notes-file`, reuses its What's New.

Submitting is public-facing and can't be cleanly undone, so **`submit` only
ever runs after the user has seen the plan from Step 5 and said yes in this
conversation**. A request like "submit the release" starts this skill; it
doesn't skip the confirmation. `prepare` changes nothing customers can see,
so an explicit request to prepare is the go-ahead — show the plan and run
it.

```bash
python3 /Users/cohen/Documents/flutter-projects/.claude/skills/create-store-release/create_store_release.py <status|prepare|submit> <project> [flags]
```

| Flag | Meaning |
|---|---|
| `--platform ios\|android` | Repeatable. Default: both. |
| `--version X.Y.Z` / `--build N` | Default: `pubspec.yaml`'s `X.Y.Z+N`. |
| `--notes-file <path>` | What's New JSON (Step 3). Omit to keep the release's current text; `submit` then fails if any locale's text is empty. |
| `--media <zip-or-folder>` | Repeatable. Screenshots/previews to upload (Step 4). |
| `--play-video-url <url>` | Google Play promo video (YouTube) for every listing locale (Step 4). |
| `--release-type manual\|after-approval` | App Store. Default: same as the live version. |
| `--phased` / `--no-phased` | App Store 7-day phased release. Default: same as the live version. |
| `--rollout-fraction F` | Google Play staged rollout, `0 < F <= 1`. Default `1` (everyone). Ignored by `prepare`. |

## Step 1 — Identify the project (ask if not given)

`anglers-log`, `activity-log`, or `tapd` (iOS + Android each). Narrow with
`--platform` only when the user names one.

**pro-iq is out of scope**: there's no App Store Connect API access for
its teams, so the user creates those releases (both stores, every tenant)
manually. If asked to submit pro-iq, say so and stop — don't work around
it with another project's key or by calling the store APIs directly.

## Step 2 — Run `status` and check the build

```bash
python3 .../create_store_release.py status <project>
```

Read-only (on Google Play it opens an edit and discards it). Per target:

- **App Store** — `build` (`null` = not uploaded; `processingState` must be
  `VALID`), `versions` (newest first, with state and attached build),
  `live_version`, `live_release_type`, `live_was_phased`,
  `open_review_submissions`, `locales`, and `media` (screenshot/preview
  counts per locale and display type, plus each placed banner's file
  name, for `media.of_version`).
- **Google Play** — `build_found_in` (track → release status for this
  version code), `tracks`, `locales`, and `media` (image counts per locale
  and image type, plus the promo `video` URL).

Check before going further:

- **The version/build is the one the user tested.** It defaults to
  `pubspec.yaml`, which is only right if nothing was bumped since the
  upload. If `build` is `null` / `build_found_in` is empty, don't guess a
  different number — show what the stores do have and ask.
- **Not already submitted.** A version already `WAITING_FOR_REVIEW`,
  `IN_REVIEW`, or live, or a version code already on `production`, means
  there's nothing to do for that target — say so and drop it.
- **Nothing in the way.** An `open_review_submissions` entry that is
  `UNRESOLVED_ISSUES` (a rejection), or a Google Play production release
  that is `inProgress` (a staged rollout this release would replace) —
  flag it and ask before continuing.

If the user only asked about a release's state, report this and stop.

## Step 3 — Get the "What's New" text

Both stores need it for every locale the listing has (`locales` in the
status output). In Prepare mode it's optional — if the user doesn't have
it yet, prepare without `--notes-file` and say What's New is still empty.
For a `submit` of an already prepared release whose text the user is happy
with, omit `--notes-file` too. Otherwise, in order of preference:

1. Text already produced in this conversation (e.g. by
   `public-release-notes`).
2. Text the user pastes.
3. Otherwise ask — offer to run `public-release-notes`. Never invent notes
   and never reuse a previous version's.

Write it as JSON to a temp file outside the repo (the session scratchpad):

```json
{
  "en": "- Fixed a crash when picking photos\n- Improved sync",
  "en-CA": "…only if the Canadian spelling differs…",
  "es": "- Se corrigió un fallo al elegir fotos\n- …"
}
```

Each store locale resolves to its exact key (`en-CA`), then its language
(`en`, `es` — covers `es-ES`, `es-MX`, `es-419`, …), then `"default"`. A
store locale with no match is an error rather than silently getting
English, so every language in `locales` needs real text — translate
properly, as `public-release-notes` does. Limits: 4000 characters on the
App Store, **500 on Google Play**; if the text is over 500, ask the user
how to shorten it instead of trimming it yourself.

## Step 4 — Media (only when asked)

Only when the user asks for screenshots, previews, or a video to be
uploaded. Never upload media the user didn't point at, and never reuse an
old export without asking.

**Source.** `--media` takes the screenshots tool's (`screenshots/`
submodule) **Export bundle** / **Export all** zip as downloaded, or that
zip extracted. Its layout is
`<ios|android>/<device>/<WxH>/<locale>/NN-<layout>.png`. Pass `--media`
more than once to combine exports (e.g. an iOS zip and an Android zip).
Ask the user which file to use; it's usually the newest
`<app>-…zip` in `~/Downloads`.

**App preview videos** (App Store only) aren't made by the tool. The user
drops them (`.mp4`/`.mov`/`.m4v`, sorted by name) into the matching
device/size/locale folder of an extracted export, e.g.
`ios/iphone/1320x2868/en/preview-1.mp4` → the 6.9" iPhone preview slot.
Up to 3 per slot; Apple checks the video's resolution/length when it
processes it.

**Google Play videos** can't be uploaded — Play only takes a YouTube URL.
If the user wants one, ask for the URL and pass `--play-video-url`.

**Mapping.** `ASC_MEDIA_SLOTS` / `PLAY_MEDIA_SLOTS` at the top of the
script. For Apple, only the **required** sizes are uploaded, one per
device, and App Store Connect scales them for every other size (the user's
choice). The export's other iPhone/iPad sizes are skipped on purpose, so
the user can point at a full export.

| Export folder | Store slot |
|---|---|
| `ios/iphone/1320x2868` | `APP_IPHONE_67` (6.9", required) |
| `ios/iphone/1284x2778` | `APP_IPHONE_65` (6.5"), **only** for a locale with no 6.9" folder |
| `ios/ipad/2064x2752`, else `2048x2732` | `APP_IPAD_PRO_3GEN_129` (13", required) |
| `android/android/*` | `phoneScreenshots` |
| `android/android-7/*` | `sevenInchScreenshots` |
| `android/android-10/*` | `tenInchScreenshots` |
| `ios/app-store-header/*` | `PRODUCT_PAGE_HEADER_ASSET` banner (3840x1646) |
| `ios/app-store-search/*` | `APP_STORE_SEARCH_RESULTS_ASSET` banner (3:2, 1920x1280 to 3840x2560) |
| `android/feature-graphic/*` | `featureGraphic` |

Everything else is listed under `media_found.ignored` and not uploaded:
smaller iPhone sizes ("not a required size"), macOS, banner videos, and
unknown sizes. There's no need to mention the skipped iPhone sizes; do
mention anything else that was ignored.

**App Store banners** (`ASC_BANNER_SLOTS`) don't live in screenshot sets.
Each is an image in the app's asset library (`appAssetLibraryImages`),
placed on a version localization (`appAssetLibraryPlacements`), one per
placement type per locale. Apple's asset library rejects the screenshots
tool's JPEG exports with `INVALID_ASSET_FILE_FORMAT` even though screenshot
sets accept JPEGs, so the script converts JPEGs to PNG with `sips` before
uploading (the PNG must have no alpha channel). It uploads first and only
then swaps the placement, so a rejected banner leaves the old one placed.
Images carry no checksum, so the script tags each upload's reference name
with the file's MD5 and skips a banner that's already placed. A rejected
upload stays in the asset library, and Apple only lets approved assets be
archived, so it can't be cleaned up. It isn't placed anywhere, though.
Whether `submit` sends newly placed banners for review along with the
version hasn't been confirmed yet. After the first `submit` with banners,
check in App Store Connect that they're in review, and update this note.

**What gets replaced.** For each store locale, the export folder with the
same locale (`en-CA`), else its language (`en`), is used. Each slot that
folder has files for is **replaced as a whole**, in file-name order; slots
and locales the export doesn't cover are left as they are (reported as
`other_sets_left_as_is` / `locales_without_media`). A slot that already
holds exactly those files is skipped, so re-running is cheap. Limits: 10
screenshots and 3 previews per App Store slot; 8 screenshots per Google
Play type, 1 feature graphic.

Scaling only happens for sizes with no screenshots of their own: a
smaller-size set already on the version (new versions copy the previous
version's) is shown instead of the scaled new ones. So any set in
`other_sets_left_as_is` (e.g. old 6.5" or 5.5" screenshots) keeps showing
the old images on those devices. Point them out; the user removes them in
App Store Connect.

**When it's applied.**

- **App Store** — `prepare` and `submit` both. Media belongs to the
  version, so customers only see it once that version is released.
  The script waits for Apple to finish processing every file (up to 10
  minutes) before submitting.
- **Google Play** — **`submit` only.** Store listing changes aren't tied
  to a release: once approved they go live, even while the old version is
  still the current one. `prepare` reports Play media as not uploaded;
  pass the same `--media` / `--play-video-url` to `submit` later.

## Step 5 — Show the plan (and, for `submit`, get a yes)

One table, one row per target: store, app, version (build), what will
happen, and the release settings that will apply:

- **App Store** — release type and phased release. Unless the user says
  otherwise these mirror the live version (`live_release_type`,
  `live_was_phased`). `after-approval` means it goes public the moment
  Apple approves it; say that in plain words.
- **Google Play** — rollout percentage (100% unless asked). Approved
  releases go live automatically unless managed publishing is on in the
  Play Console; the API can't see that setting, so mention it.

Then the What's New text per locale (or "kept as is"), then, if media is
being uploaded, which slots per store will be replaced (from
`media_found` in a first run's output, or by listing the export's
folders), what's ignored, and that Google Play media waits for `submit`.

For `submit`, ask for confirmation. Don't run it on an earlier or general
go-ahead. For `prepare`, go straight on.

## Step 6 — Prepare or submit

```bash
python3 .../create_store_release.py <prepare|submit> <project> [--notes-file <path>] [--media <zip>] [flags]
```

What it does, per target:

- **App Store** — creates version `X.Y.Z` (or renames the one unreleased
  version if a different number is sitting in "Prepare for Submission"),
  attaches the build, sets What's New on every locale, uploads media,
  applies release type / phased release, then (`submit` only) creates a
  review submission and submits it.
- **Google Play** — puts the version code on the `production` track with
  the release notes and commits the edit: a **draft** release for
  `prepare`; for `submit`, uploads listing media too and sends it all for
  review.

It's idempotent: a target that's already in review or live comes back as
`already_<state>` and is left alone, and media slots already up to date
are skipped, so re-running after a partial failure is safe. Each target
reports `result` (`submitted`, `prepared`, `already_*`), the `actions`
taken, `media` (what was replaced / unchanged / left alone), and `error`.

## Step 7 — Handle errors

Never retry by changing what's being submitted (a different build, dropped
locales, shortened notes) without asking.

- `missing_asc_key` → `config.json` or its key is missing; walk the user
  through **Setup**. The Android target still ran — report it.
- `Build is PROCESSING` → Apple hasn't finished; try again in a few minutes.
- `Build has no export compliance answer` → the user answers it in App
  Store Connect (all current apps set `ITSAppUsesNonExemptEncryption` in
  `Info.plist`, so this shouldn't appear).
- `Version is prepared but not submitted: …` → the version, build, and
  notes are in place; an existing review submission needs the user's
  attention in App Store Connect first.
- `HTTP 401` → wrong key/issuer ID or a revoked key. `HTTP 403` → the key's
  role is too low (needs App Manager), or for Google Play the service
  account lacks release permissions for that app.
- `HTTP 409` from App Store Connect → the message names what's missing
  (screenshots for a new device size, an unanswered questionnaire, …).
  Usually something only the console can fix; relay it verbatim.
- `App Store Connect rejected <file>: …` → Apple's processing refused a
  screenshot/preview (usually wrong dimensions, an alpha channel, or a
  video of the wrong size/length). Its set is left partly filled; fix the
  file and re-run — the set is replaced again. For a banner, the old
  placement is left in place.
- `<slot> <locale>: N screenshots; … limit is M` → the export has too many
  files for that slot; nothing was uploaded. Ask the user which to drop.
- `No --notes-file, and What's New is empty for: …` / `no prepared release
  notes to reuse` → `submit` needs text; go back to Step 3.
- Google Play `changesNotSentForReview` → the app has changes that must be
  sent from the Play Console (typically after a rejection); the user sends
  them there.
- Google Play `Only releases with status draft may be created on draft app`
  → the app has never been published; first release goes through the
  console.

## Step 8 — Report

A final table with every target's result, plus what happens next for each
(e.g. "releases automatically once approved", "waits for you to release
manually", "20% rollout"; for `prepare`, "ready — run submit when you
are"). Mention any target that was skipped and why, the media slots
replaced, and any ignored files or stale slots left alone. Then delete
the notes temp file.

## Setup

Google Play needs nothing of its own — it reuses `GOOGLE_PLAY_JSON_KEY`
from each project's `release_credentials.sh`.

App Store Connect needs an API key for the personal team (`RQ74DU9PML`:
anglers-log, activity-log, tapd). The upload script's app-specific
password can't call this API, and the `app-store-reviews` key is Customer
Support-only by design — don't reuse or upgrade it.

If the key is missing or revoked, the user must:

1. App Store Connect → Users and Access → Integrations → App Store Connect
   API → **Team Keys** → generate a key with the **App Manager** role.
2. Download the `.p8` (possible only once) into this skill's folder, and
   note the **Key ID** and the **Issuer ID** at the top of that page.

The user generates and downloads the key themselves. Once they give you the
IDs and file name, write `config.json` in this skill's folder, keyed by
the project's `APPLE_TEAM_ID` (`private_key_path` is relative to the
folder):

```json
{
  "app_store_connect_keys": {
    "RQ74DU9PML": {
      "issuer_id": "…",
      "key_id": "…",
      "private_key_path": "AuthKey_XXXXXXXXXX.p8"
    }
  }
}
```

The repo root `.gitignore` excludes this folder's `config.json` and `*.p8`.
Never commit them (no `git add -f`), never remove those ignore rules, and
never print the `.p8` contents. `chmod 600` the key and config. Don't
create the config with placeholder values.

Ignored files aren't copied into new git worktrees, so run from the main
checkout.

## Adding a project

Projects are listed in `PROJECTS` at the top of `create_store_release.py`
(project dir, Apple bundle ID, Android package, platforms). A project on a
different Apple team also needs that team's key in `config.json`. The
script assumes one app per project; a multi-tenant project like pro-iq
would need per-tenant bundle IDs and credentials added back.
