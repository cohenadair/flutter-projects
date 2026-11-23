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
- **This is a retry of a previous failed run** — see Step 9. Scope to
  exactly the tenant/platform combinations that failed; don't rebuild ones
  that already succeeded.

## Step 4 — Pull the latest default branch

**Skip this on retries** (Step 9). A retry must build the same code as the
original run's other platforms, which share its build number.

The build compiles whatever is checked out locally. Merged PRs that haven't
been pulled are silently left out of the release. This happened with
activity-log `2.0.5+2026111701`, which shipped without two merged fixes.

Pull **both** of these repos:

- **The app repo:** the project's own submodule (`pro-iq`, `anglers-log`,
  `activity-log` or `tapd`), not the `<project>/mobile` dir or the parent
  monorepo.
- **`adair-flutter-lib`:** every app depends on it by path, so its working
  tree is compiled into the release too. Its default branch is `main`.

Run steps 1–3 for each repo.

1. **Check the branch:** `git -C <repo> branch --show-current` must be the
   repo's default branch (`main` or `master`). If it isn't, stop and ask.
   Don't switch branches yourself.
2. **Pull without touching local changes:**
   ```bash
   git -C <repo> pull --ff-only
   ```
   `--ff-only` works with uncommitted changes as long as the incoming
   commits don't touch those files. **Never stash, unstage or reset** to
   make a pull work.
3. **If the pull fails, stop and ask.** It fails when local commits haven't
   been pushed (the branches diverged), or when incoming commits touch a
   file with uncommitted changes. Report which case it is.
4. Note in the final report (Step 10) which commits each pull brought in,
   from `git log --oneline <old HEAD>..HEAD`.

## Step 5 — Pre-build check: hardcoded Pro override

**Run this before every build, including retries.** Every project depends
on `adair-flutter-lib` by path, so a local dev override in its
`SubscriptionManager` (e.g. `bool get isPro => true;`) is compiled straight
into the release and gives **every user Pro for free**. This has shipped
once already (anglers-log `2.8.0+2026092502`).

The file is
`/Users/cohen/Documents/flutter-projects/adair-flutter-lib/lib/managers/subscription_manager.dart`.
The correct getter is:

```dart
bool get isPro => _state == SubscriptionState.pro;
```

1. **Check the committed version first:**
   ```bash
   cd /Users/cohen/Documents/flutter-projects/adair-flutter-lib && \
     git show HEAD:lib/managers/subscription_manager.dart | grep -n 'bool get is\(Pro\|Free\)'
   ```
   If `HEAD` itself has an override, **stop and flag it to the user — do
   not build.** Don't commit a fix yourself; it's their call how to land it.
2. **Check uncommitted (staged + unstaged) changes:**
   ```bash
   cd /Users/cohen/Documents/flutter-projects/adair-flutter-lib && \
     git diff -U0 HEAD -- lib/managers/subscription_manager.dart
   ```
   Treat any changed line that forces subscription state as an override.
   Examples include `isPro`/`isFree` returning a literal `true`/`false`,
   `_state` initialized or assigned to `SubscriptionState.pro` outside the
   RevenueCat callback, and an early return that skips entitlement checks.
3. **If an override is found, flag it to the user** by quoting the offending
   line(s), **then revert it automatically** before building:
   - Save the full diff first, so the user can reapply it for local
     testing after the release:
     `git diff HEAD -- lib/managers/subscription_manager.dart > <scratchpad>/subscription_manager_override.patch`
   - Restore **only the override lines** to their `HEAD` version with the
     Edit tool. Leave any other uncommitted changes in the file alone.
   - If the override was also staged, run `git add` on this one file after
     the edit so the index doesn't still hold the override. Don't touch
     staging for any other file.
4. **Verify** before continuing:
   `grep -n 'bool get isPro' lib/managers/subscription_manager.dart` must
   print `bool get isPro => _state == SubscriptionState.pro;`. If it
   doesn't, stop and ask.
5. In the final report (Step 10), say that the override was reverted and give
   the patch path.

## Step 6 — Pre-build check: in-app change log

**Skip this on retries** (Step 9). They reuse the build number from the
original run, and the check already passed then.

The change log page is compiled into the app. A release without an entry
for its version would need a new build and upload to fix it.

1. **Does the project have a change log page?** Use the **Project reference
   table** in
   `/Users/cohen/Documents/flutter-projects/.claude/skills/public-release-notes/SKILL.md`
   as the source of truth. If it says "No", skip this step. If the project
   isn't listed, ask the user rather than guessing.
2. **Find the page.** Its path is project-specific. For example,
   anglers-log's is `mobile/lib/pages/onboarding/change_log_page.dart`. If
   it has moved, find it with the grep in `public-release-notes` → **Find the
   change log page**.
3. **Check for an entry for the release version** from Step 2 (the new
   `X.Y.Z`, or the current one if it's being kept). Look at the working
   tree, not `HEAD`, because the build compiles the working tree. In the
   anglers-log pattern, version `2.8.3` needs both of these:
   - a `_build2_8_3(context)` call at the top of the children list in
     `build()`
   - `changeLog_283_<n>` keys in every locale ARB file
   Other projects may use a different pattern. Match what the page
   actually does.
4. **If the entry is missing or incomplete** (for example, one locale has
   no keys), **stop before building.** Tell the user what's missing, and
   offer to run the `public-release-notes` skill to add it. That skill
   shows the proposed entries (every locale) for approval before it edits
   anything. **Don't start the build until the user has approved the
   wording.** A yes to "add the entry" doesn't count as approving it.
   Build only once the approved entry exists, or if the user explicitly
   says to release without it.
5. If the entry exists but is uncommitted, say so in the final report
   (Step 10). The build includes it, but the user needs to commit it.

## Step 7 — Run it

### Before every run: no other builds

**Do this on retries too.** A release build shares `build/` with any other
build of the same project. That includes another Claude session's
`flutter run` or `flutter build`, or Xcode. A concurrent build corrupts the
shared SPM cache: activity-log `2.0.5+2026111702` failed on iOS with
`Could not resolve package dependencies` because a Debug build was
resolving packages into the same `build/ios/SourcePackages` at the same
time. A concurrent session can also edit files mid-build. That release's
Android upload picked up another session's uncommitted edit.

1. **Look for other builds of this project:**
   ```bash
   ps -axo pid,lstart,command | grep -E 'xcodebuild|flutter|gradle' \
     | grep '<flutter dir>' | grep -v grep
   ```
   `<flutter dir>` is `<project>/mobile`, or `pro-iq` for pro-iq. If
   anything shows up, **stop and ask** the user to finish or stop it. Never
   kill it yourself, since it may be the user's own `flutter run`.
2. **Re-check `git status`** in the project repo. If files have
   uncommitted changes that weren't there at Step 4, someone else is
   editing. Stop and ask before building them into the release.

### Run the script

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

## Step 8 — Read the report

Every run ends with a table listing each platform (pro-iq: each
tenant/platform pair) as `uploaded`/`built`/`FAILED - <reason>`, plus the
path to that platform's full log file. Read the **log file**, not just the
one-line reason, before deciding anything about a failure — the reason
string is a short label (e.g. `flutter build ipa failed`), the log has the
actual compiler/signing/upload error.

Report the table to the user first, in full, before doing any auto-fix work.

## Step 9 — Auto-fix and retry failures

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
already bumped once during Step 7's run; other platforms in that same run
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
- **SPM resolve failure** (`Could not resolve package dependencies`, a
  missing `.zip` under `SourcePackages/artifacts`, or an archive that
  "does not contain a binary artifact"): usually a corrupted SPM cache,
  often from a concurrent build. Only now clear the cache, since a healthy
  one saves a full re-download on every build. Re-run the Step 7 pre-run
  checks first so nothing else is building, then clear the cache for that
  platform and retry:
  ```bash
  rm -rf <flutter dir>/build/ios/SourcePackages    # or build/macos/...
  ```
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
  each project's own `mobile/release_credentials.sh` — a local, gitignored
  file (backed up in iCloud `projects/keys`), not the committed
  `build_and_upload_release.sh` itself. pro-iq's is `release_credentials.sh`
  at the pro-iq root, committed to its private repo along with its other
  keys.
- A genuine compile error in app code (not a stale-cache symptom) — this is
  a real bug, not a release-pipeline issue. Report it; fixing app code is
  outside this skill's scope unless the user explicitly asks you to.

## Step 10 — Final report

After all retries (successful or exhausted), give one final table covering
every platform from the original run — including ones fixed on retry (note
they were retried) and any left failing with a one-line reason. Don't lose
track of platforms that succeeded on the very first pass; the point is one
complete picture of the release, not just what changed during retries.
