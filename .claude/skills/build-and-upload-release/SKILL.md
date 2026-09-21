---
name: build-and-upload-release
description: >
  Runs a Flutter sub-project's build_and_upload_release.sh script to build
  and upload a new release to the App Store / Google Play, then
  automatically diagnoses and retries any platform that fails. Use when the
  user says things like "build and upload a release", "cut a release build",
  "upload pro-iq/anglers-log/activity-log/tapd", "release build_and_upload", or
  invokes /build-and-upload-release directly. Also use to retry a previous
  failed run (e.g. "retry the failed iOS uploads") — pass the project and,
  if known, which platform(s)/tenant(s) failed.
---

# build-and-upload-release Skill

Runs the root
`/Users/cohen/Documents/flutter-projects/build_and_upload_release.sh` for one
project, then reads its results and retries automatically where it can. The
single-tenant projects are invoked directly against the root script (it
sources the project's `release_credentials.sh`, defaults the platforms to
`ios android`, and reads the Android package name from
`android/app/build.gradle` itself — no per-project wrapper exists). pro-iq is
the exception: its multi-tenant driver sets up each tenant's credentials and
flavor, then calls the root script itself.

## Step 1 — Identify the project (ask if not given)

One of:

| Project | Entry point | Notes |
|---|---|---|
| `pro-iq` | `pro-iq/build_and_upload_release.sh` | Multi-tenant driver — loops `tenants.yaml`, one tenant at a time, each tenant's platforms in parallel. It calls the root script per tenant. |
| `anglers-log` | root script, project dir `anglers-log/mobile` | Single tenant, defaults to `ios android`. |
| `activity-log` | root script, project dir `activity-log/mobile` | Single tenant, defaults to `ios android`. |
| `tapd` | root script, project dir `tapd/mobile` | Single tenant, defaults to `ios android`. |

If the user's request doesn't name one and it's not obvious from context
(e.g. continuing a prior run discussed in this conversation), ask which
project before doing anything else.

## Step 2 — Prompt for the version number immediately

This is the **only required input** — ask for it before anything else,
right after the project is known (don't wait to gather platform/tenant
preferences first).

1. Read the project's current version: `grep '^version:' <project-dir>/pubspec.yaml`
   (strip the `+<build>` suffix — only the `X.Y.Z` part is relevant to show).
2. Ask: *"Current version is `X.Y.Z`. What version should this release be?
   (blank keeps `X.Y.Z` and only bumps the build number)"*
3. If the user gives a new `X.Y.Z`, that becomes `--version=<X.Y.Z>`. If they
   say to keep it, or the request already stated the target version, don't
   ask again — just confirm what you'll pass.

Do not rely on the underlying scripts' own interactive `read -p` prompt for
this (`bump_pubspec_version.sh`) — it only fires on a real TTY, which a tool
invocation isn't, so it would silently no-op. Always pass the version
explicitly via `--version=`.

## Step 3 — Resolve platforms / tenants

Default to **running the script as-is** — don't ask about this unless the
request implies a narrower scope:

- **pro-iq**: all tenants with `build: true` in `tenants.yaml`, each tenant's
  full configured platform list.
- **anglers-log** / **activity-log** / **tapd**: `ios android` (the root
  script's own default when no platform is passed).

Narrow the scope only when:
- The user names specific platforms ("just iOS", "android only") →
  pass those platform tokens (`ios`/`macos`/`android`) through.
- The user names specific pro-iq tenants ("just pro-iq, not
  hill-method-coaching") → pass `--tenant=<id>` (repeatable).
- **This is a retry of a previous failed run** — see Step 6. Scope to
  exactly the tenant/platform combinations that failed; don't rebuild ones
  that already succeeded.

## Step 4 — Run it

```bash
# anglers-log / activity-log / tapd — root script, project dir as an argument
cd /Users/cohen/Documents/flutter-projects && \
  ./build_and_upload_release.sh <project>/mobile --version=<X.Y.Z> [ios] [macos] [android]

# pro-iq — multi-tenant driver (calls the root script per tenant)
cd /Users/cohen/Documents/flutter-projects/pro-iq && \
  ./build_and_upload_release.sh --version=<X.Y.Z> [--tenant=<id> ...] [ios] [macos] [android]
```

Omit the platform tokens to use the default (`ios android` for single-tenant
projects; each tenant's configured list for pro-iq). Add `--skip-upload` only
if the user asks for a build-only verification run — it's a root-script flag
for the single-tenant projects, and pro-iq's driver doesn't accept it.

Run this with the Bash tool in the foreground — it can take a long time
(multiple platform builds), and its console output is now just a project
line plus progress dots followed by the final report table (all the
step-by-step output lives in log files under `build/release_logs/`, printed
in the table). Use a generous timeout; if using a background invocation,
check back rather than assuming it's done from silence.

## Step 5 — Read the report

Every run ends with a table listing each platform (pro-iq: each
tenant/platform pair) as `uploaded`/`built`/`FAILED - <reason>`, plus the
path to that platform's full log file. Read the **log file**, not just the
one-line reason, before deciding anything about a failure — the reason
string is a short label (e.g. `flutter build ipa failed`), the log has the
actual compiler/signing/upload error.

Report the table to the user first, in full, before doing any auto-fix work.

## Step 6 — Auto-fix and retry failures

For each failed platform, in order:

1. **Read its log file in full** (or at least the last ~150 lines — the
   actual error is usually near the end, but a signing/pod error can appear
   earlier with a generic "failed" line at the very end).
2. **Classify the failure** against the categories below. If it doesn't
   match a known, confidently-fixable pattern, **stop for that platform** —
   report the log excerpt and ask the user rather than guessing at a fix.
   Guessing wrong on a release build wastes a full rebuild cycle.
3. **Apply the fix**, then retry — **only that platform** (and, for pro-iq,
   only that tenant), always with `--skip-version-bump` (see the callout
   below), never re-running platforms that already succeeded.
4. **Cap retries at 2 attempts per platform.** If it still fails after a
   fix attempt, stop and hand it back to the user with both attempts' log
   excerpts — don't loop indefinitely on the same platform.

**Always retry with `--skip-version-bump`.** The version/build number was
already bumped once during Step 4's run; other platforms in that same run
may have already uploaded successfully under that exact build number.
Re-bumping on retry would give the retried platform a *different* build
number than its siblings from the same release. Pass `--skip-version-bump`
on every retry invocation (both the root script directly and pro-iq's
driver support this flag) and omit `--version=` entirely (it's ignored
alongside `--skip-version-bump` anyway). For example, retrying only iOS for
activity-log:

```bash
cd /Users/cohen/Documents/flutter-projects && \
  ./build_and_upload_release.sh activity-log/mobile --skip-version-bump ios
```

### Known fixable categories

- **Stale/incomplete build output** (`no .ipa found`, `no .aab found`, `no
  .pkg found in export output`): usually means an earlier step silently
  produced nothing where the log's tail expected. Re-read the full log for
  the actual first error (often a code-signing or export-options failure
  higher up) rather than treating "no artifact found" as the root cause
  itself. Retry once that underlying error is addressed.
- **Transient network failure** (upload step: connection reset, timeout, 5xx
  from Apple/Google's API): retry as-is, no code change needed — but only
  once; a second consecutive network failure likely isn't transient.
- **App Store Connect "duplicate build number"**: means a build with that
  exact version+build already exists — check `pubspec.yaml`'s current value
  against what was actually uploaded (e.g. this platform partially uploaded
  before failing). Do not just bump the build number yourself outside the
  scripts' own mechanism — ask the user, since it likely means a previous
  run partially succeeded in a way the log doesn't fully capture.
- **Google Play "versionCode has already been used"**: same reasoning as
  above — ask rather than silently re-bumping.

### Not auto-fixable — always ask

- Code-signing / provisioning profile errors ("no signing certificate
  matches", "no profiles for X were found") — these are Apple Developer
  account/keychain state, not something to guess-fix from a script.
  Auto-fixing this class wrong risks masking a real account problem.
  Report what the log shows and ask.
- Any missing/expired credential (`APPLE_APP_SPECIFIC_PASSWORD`,
  `GOOGLE_PLAY_JSON_KEY` invalid or expired) — never regenerate or guess at
  credentials; tell the user which one and point at where it's configured:
  each project's own `mobile/release_credentials.sh` (pro-iq:
  `release_credentials.sh` at the pro-iq root) — a local, gitignored file,
  not the committed `build_and_upload_release.sh` itself.
- A genuine compile error in app code (not a stale-cache symptom) — this is
  a real bug, not a release-pipeline issue. Report it; fixing app code is
  outside this skill's scope unless the user explicitly asks you to.

## Step 7 — Final report

After all retries (successful or exhausted), give one final table covering
every platform from the original run — including ones fixed on retry (note
they were retried) and any left failing with a one-line reason. Don't lose
track of platforms that succeeded on the very first pass; the point is one
complete picture of the release, not just what changed during retries.
