---
name: reproduce-bug
description: >
  Reproduces a bug in one of this monorepo's Flutter apps on an iOS simulator
  or Android emulator, and writes definitive, verified reproduction steps
  with the exact seed data needed — or flags clearly when the bug can't be
  verified on a simulator/emulator, and why. Given an existing bug-fix PR, it
  reproduces the bug without the PR's changes and confirms the PR fixes it.
  Runs on its own or as a step of `ship-ticket` (which also reuses it to
  confirm a fix). Use when the user says things like "reproduce this bug",
  "reproduce issue #42", "can you repro this", "verify this bug report",
  "write repro steps for <issue URL>", "is this bug real", "does PR #12 fix
  the bug", "verify this fix PR", or invokes /reproduce-bug directly.
---

# Reproduce bug

Turns a bug report (a GitHub issue, or a description) into reproduction
steps that were actually performed on a simulator or emulator, starting
from a fresh install with a known, minimal set of seed data. The output is
only "verified" if every step was performed exactly as written and the bug
was seen. Anything less is labeled as such — never present plausible-looking
steps as verified.

**Running the app is the point of this skill.** Never kill the user's own
`flutter run` sessions (ask them to stop one if it's on the device you
need), and run only **one simulator or emulator at a time** (Step 4).

Don't change app code in this skill. Temporary debug logging is fine only in
a throwaway worktree, and must be removed before reporting.

## Inputs

- **The bug**: a GitHub issue URL or number (with repo), a free-text
  description, or a **PR** that fixes it (see **PR mode** below). If none
  was given, ask for it.
- **Code to run** (optional): a worktree path. `ship-ticket` passes its
  worktree; when run on its own, Step 3 creates one at the default branch's
  remote tip.
- **Platform** (optional): `ios`, `android`, or both. Otherwise Step 2
  decides.

When `ship-ticket` invokes this skill to confirm a fix, it passes the report
from the earlier run. Re-run that report's exact steps and seed against the
fixed worktree. Don't re-derive them, so before and after are comparable.

## PR mode

Given a PR, answer two questions: does the bug reproduce without the PR's
changes, and is it gone with them?

```bash
gh pr view <n> --repo <owner>/<repo> --comments --json \
  title,body,state,baseRefName,baseRefOid,headRefOid,closingIssuesReferences,files
gh pr diff <n> --repo <owner>/<repo>
```

1. **The bug**: read the issues the PR closes (`closingIssuesReferences`,
   or `#n` references in the body) as in Step 1, plus the PR's own
   description and diff. The diff often shows exactly what triggers the
   bug. If the PR is plainly a feature rather than a fix, say so and offer
   `verify-feature` instead.
2. **Existing repro steps**: if the PR body or linked issue already has
   reproduction steps (e.g. from `ship-ticket` or `crashlytics-triage`),
   replay those as written instead of deriving new ones. Report whether
   they hold, and correct them if they don't.
3. **Two worktrees**, prepared as in Step 3:
   ```bash
   git -C <repo-dir> fetch origin <baseRefName> "pull/<n>/head"
   BASE=$(git -C <repo-dir> merge-base <baseRefOid> <headRefOid>)
   git -C <repo-dir> worktree add --detach ../<repo-name>-pr-<n>-before "$BASE"
   git -C <repo-dir> worktree add --detach ../<repo-name>-pr-<n>-after <headRefOid>
   ```
   The merge base is the base branch as the PR author saw it, so the only
   difference between the two is the PR. `pull/<n>/head` works for PRs
   from forks too.
4. **Before**: Steps 2–5 in the `before` worktree. If it's not reproduced
   there, stop and report that. Testing the fix proves nothing if the bug
   never appears.
5. **After**: replay the exact same seed and steps, on the same device(s),
   in the `after` worktree.

The report (Step 6) then has two statuses: **Before** (✅ Reproduced / ❌
Not reproduced / ⚠️ Can't verify) and **After** (✅ Fixed / ❌ Still
reproduces / ⚠️ Can't verify). It also says whether the PR's own repro
steps held up. Post it on the PR (Step 6) without asking: the user wants
PR-mode results on the PR. If the PR's own manual-test steps wouldn't show
the bug, also replace them in its description with the verified steps.
Touch nothing else in the description.

## Step 1 — Read the bug

```bash
gh issue view <n> --repo <owner>/<repo> --comments
```

Get the expected vs. actual behavior, any steps the reporter gave, the
platform/OS/app version, screenshots, and labels (`ios`, `android`, `crash`,
`bug-ui`, `regression`, `pro`). Map the repo to its sub-project:

| Repo | App root | Data layer |
|---|---|---|
| `cohenadair/anglers-log` | `anglers-log/mobile/` | SQLite (protobuf rows) |
| `cohenadair/activity-log` | `activity-log/mobile/` | SQLite + shared_preferences |
| `cohenadair/tapd` | `tapd/mobile/` | shared_preferences (+ RevenueCat) |
| `Pro-IQ-Inc/pro-iq` | `pro-iq/` | Firestore, Auth, Storage, Functions |
| `cohenadair/adair-flutter-lib` | the app it was seen in | — |

Then read the code the bug points at, and work out a hypothesis: the
specific data and action sequence that should trigger it. That is what Step
5 tries to make happen. A reporter's steps are a starting point, not the
answer. Shrink them to the minimum that still triggers the bug.

## Step 2 — Decide whether it can be verified, and on what

Pick the platform: the one the issue names. If the issue doesn't name one,
use iOS. The simulator runs at native speed on Apple Silicon, while the
Android emulator is several times slower on this Mac (16 GB of RAM, usually
swapping) and much less reliable. Use both when the code path differs per
platform (`Platform.is*`, `IoWrapper.get.is*`, plugins with native code,
`ios/` or `android/` config). Use Android alone only when the bug is
Android-specific.

Some bugs can't be verified on a simulator or emulator. Find out before
spending time on it. Common reasons:

- Needs a physical device: camera, real GPS movement, Bluetooth, background
  execution and app suspension timing, push notification delivery,
  performance on old hardware, a specific device model.
- Needs real accounts or production data: a real user's Firestore data,
  production-only Firebase config, App Store/Play receipts, real RevenueCat
  purchases or subscription states (test values for the user's own app are
  fine; real credentials never are).
- Needs an OS version or locale/region setup that no available runtime
  provides.
- Depends on an external service's state you can't control.

If it can't be verified, don't stop. Go to Step 6 and report **Can't
verify**, with the reason and best-effort steps marked unverified. If only
part can be done (e.g. the data setup works, but the trigger needs a real
purchase), verify that part and say exactly where verification ends.

## Step 3 — Code to run

If a worktree path was passed in, use it. Otherwise create a throwaway one
at the remote tip of the default branch, so the repro reflects what's
shipped and not the user's uncommitted work:

```bash
DEFAULT=$(gh repo view <owner>/<repo> --json defaultBranchRef -q .defaultBranchRef.name)
git -C <repo-dir> fetch origin "$DEFAULT"
git -C <repo-dir> worktree add --detach ../<repo-name>-repro-<n> "origin/$DEFAULT"
```

Then prepare it. This is the same setup `ship-ticket` uses:

1. **Copy gitignored config** the build needs (Firebase options and plists,
   `firebase.json`, `sensitive.properties`, pro-iq's `dart-defines/`) from
   the main checkout. Without `firebase.json`, iOS builds fail in the
   FlutterFire Crashlytics upload step:
   ```bash
   cd <repo-dir> && git ls-files --others --ignored --exclude-standard \
     | grep -vE '(^|/)(build|\.dart_tool|Pods|node_modules)/' \
     | grep -E '(firebase_options.*\.dart|GoogleService-Info\.plist|google-services\.json|(^|/)firebase\.json$|sensitive\.properties|^dart-defines/)' \
     | while read -r f; do mkdir -p "<worktree>/$(dirname "$f")"; cp "$f" "<worktree>/$f"; done
   ```
2. **Android signing.** Never copy release keystores or
   `keystore.properties` into a worktree, and don't write one. Every app
   builds debug APKs without it, signed with the standard debug key, so
   repro with debug builds (anglers-log and activity-log release builds
   fail without it).
3. `flutter pub get` in the worktree's app root. App dependencies on
   `adair-flutter-lib` are relative paths, and a sibling worktree resolves
   them to the main checkout's lib.
4. If the build fails on missing generated files, run the project's
   generators (`flutter gen-l10n`, `gen_tenants.sh` / `gen_proto.sh` in
   pro-iq, `dart run build_runner build`) rather than copying generated
   output.

Remove a worktree this step created at the end (Step 7).

## Step 4 — Device

**Use the user's existing devices. Never create new simulators or AVDs**:
they take up disk space, and the existing ones are known to work. The user
doesn't mind the app's data on them being wiped, so uninstalling the app
for a fresh install is fine. Only the app under test, though: don't erase
the whole device (`simctl erase`, `-wipe-data`), except when the Android
emulator is too full to install the build (see Android below).

**Only one simulator or emulator at a time.** More than one strains the
user's CPU too much. Before booting anything, check what's running (`xcrun
simctl list devices booted`, `adb devices`):

- If a device of the platform you need is already booted, use it, unless
  the user has a `flutter run` session on it (then ask them to stop it).
- If something else is booted, shut it down without asking (`xcrun simctl
  shutdown <udid>`, `adb -s <serial> emu kill`), then boot yours. The one
  exception is a device with the user's own `flutter run` session on it:
  ask them to stop the session instead.
- For a two-platform check, do one platform, shut its device down, then
  boot the other.
- **Always close the Android emulator before opening an iOS simulator, and
  vice versa**, and confirm it's gone (`adb devices` lists nothing; `xcrun
  simctl list devices booted` is empty) before booting the other.

### iOS

Use an existing iPhone simulator (`xcrun simctl list devices available`),
preferably one that's already booted. For an older-OS bug, use an existing
simulator on that runtime if there is one. Otherwise say the OS version
couldn't be tested.

**Access needs the user's OK.** The simulator tools refuse a device until
the user attaches it in the simulator panel and clicks "Let Claude use it".
That's once per device. Call `attach` as soon as the device is booted. If
access hasn't been granted, ask the user right away (they may be working
remotely and unable to see the panel), and offer Android as the fallback
only if the bug isn't iOS-specific.

### Android

Use the user's phone AVD, `Pixel_9_Pro` (`emulator -list-avds`; the
`Screenshots_*` ones belong to the screenshot capture tool). Boot it with
`emulator -avd Pixel_9_Pro -no-audio -no-boot-anim`. It keeps its quick-boot
snapshot, so it boots in seconds.

- **Don't `-wipe-data` routinely.** It redoes several minutes of first-boot
  Google services setup, and a fresh app install doesn't need a fresh
  device. The exception: if an install fails with
  `INSTALL_FAILED_INSUFFICIENT_STORAGE` (check `adb shell df -h /data`),
  shut it down and boot it with `-wipe-data` without asking. Don't
  uninstall the user's other apps to make room instead.
- **Turn off animations** after it boots (`adb shell settings put global
  window_animation_scale 0`, and the same for `transition_animation_scale`
  and `animator_duration_scale`). Turn them back on (`1`) before shutting it
  down, since it's the user's device.
- **Check memory before booting** (`sysctl vm.swapusage`). With swap nearly
  full, the emulator can hang on boot (the VM sits idle and adb shows
  `offline`) or crawl. If that happens, tell the user what's using memory
  rather than retrying.
- **Don't change the AVD's settings** (`config.ini`). If it's too slow to
  work with, tell the user what you saw.
- **If the system stops responding** (`adb shell pm list packages` says
  `Can't find service: package`, or adb stays `offline`), kill it (`adb emu
  kill`) and boot it again.

### Fresh install and run

Start from a **fresh install** every time. Bundle IDs and packages are in
each app's Xcode project and `android/app/build.gradle*`.

- **Android**: build once with `flutter build apk --debug` in the worktree's
  app root, then install with `scripts/android.sh fresh <apk> <package>
  <permissions…>`. It uninstalls, installs, grants permissions up front
  (which skips the system permission dialogs), and launches. That's much
  faster than `flutter run` for each attempt. Read logs with `adb logcat`
  (Flutter output is tagged `flutter`). Use `flutter run` only when you need
  hot reload or the VM service.
- **iOS**: `xcrun simctl uninstall <udid> <bundle id>`, then `flutter run -d
  <udid>` in the background (or `flutter build ios --simulator` + `xcrun
  simctl install` / `launch`).
- **pro-iq**: never against production. Start the emulators without
  exporting on exit, so repro data doesn't leak into the user's saved
  `emulator-data/`:
  ```bash
  (cd functions && npm run build) && firebase emulators:start --project pro-iq \
    --only functions,firestore,auth,storage --import ./emulator-data
  ```
  Then `flutter run -d <device> --flavor <flavor>
  --dart-define-from-file=dart-defines/<tenant>.json
  --dart-define=USE_EMULATOR=true` (flavor and tenant pairs from
  `tenants.yaml`; default `proIq` / `pro-iq`). Sign in with a test account
  from the emulator data, or create one there.
  `start_emulators.sh` exports on exit, so don't use it here.

## Step 5 — Seed, then reproduce

**Seed data** is the exact, minimal set of records the bug needs, with
concrete values (names, dates, numbers, settings, toggles). It's always
written out as a list or table so a human can recreate it, plus a
machine-loadable form where the project supports one:

| Project | Machine-loadable form |
|---|---|
| anglers-log | Entities in `seed.json` format (proto3 JSON with keys, relative timestamps, measurements — see `anglers-log/screenshots/capture/README.md` → Seed format). |
| pro-iq | Firestore documents (path + fields, matching the protos) and Auth users, written to the local emulator via its REST API or the emulator UI. |
| activity-log, tapd | None. Use in-app steps only. |

Load the seed in a way the report can repeat exactly. Usually that means
entering it through the app's own UI from a fresh install. Seed steps are
part of the reproduction and must be verified like the rest. A
machine-loadable seed that wasn't actually loaded (or at least checked,
e.g. anglers-log's `build_seed.dart --check`) is labeled **not loaded** in
the report.

Drive the app:

- **iOS**: `mcp__Claude_Code_iOS_Simulator__control` (`screenshot`, `tap`,
  `swipe`, `text`, `press_key`). Coordinates are device points from the
  latest screenshot.
- **Android**: `scripts/android.sh` in this skill's folder: `shot`, `tap`
  (in the 40% view's coordinates), `type`, `settle`, `focus`, `launch`,
  `fresh`. Run it without arguments for usage. It waits for the screen to
  settle instead of sleeping a fixed time, and types with key events,
  because `adb shell input text` doesn't reach Flutter text fields. Use
  `adb shell uiautomator dump` to find element bounds when a screenshot
  isn't clear.

**Never chain steps blind.** Take a screenshot after every step, or after a
small group of steps whose screens you've already seen, and check that the
step did what it says before moving on. If the screen isn't what you
expected, or `android.sh focus` shows a package other than the app (a
launcher, a Google sign-in, a system dialog), stop and work out what
happened. Never act on screens outside the app beyond dismissing them
(Back/Home). A script of taps that runs ahead of a slow device ends up
tapping on whatever is in front. In one run that was a Google account
sign-in.

**Name screenshots for what they show.** Evidence screenshots are
`<before|after>-<n>-<what>.png`, e.g. `before-3-stale-name.png`. Working
shots taken just to see the screen go in a `work/` subfolder, which Step 7
deletes.

Watch the logs too (`adb logcat`, or the `flutter run` output): an
exception, assertion, or `_log.e` there is often the clearest evidence, so
capture the relevant lines.

**Per-app notes** (fresh-install hurdles, so you don't rediscover them):

| App | Notes |
|---|---|
| anglers-log | Android package `com.cohenadair.anglerslog`. Grant `ACCESS_FINE_LOCATION` and `ACCESS_COARSE_LOCATION` on install. Onboarding: a "Location Accuracy" system dialog (No thanks), Next, Next, Set Permission, Next, then "Not Now" on the Pro page. The first launch of a debug build takes 30–60 s on the emulator. |

Add a row when you learn something about another app.

If the hypothesis doesn't trigger the bug, revise it from what you saw
(read the code again, vary the data) and try again. Stop after a few
genuine attempts and report **Not reproduced** with what was tried. Don't
keep varying things until something unrelated breaks.

**If the reporter's steps don't reproduce it**, ask what else could be
refreshing the screen and hiding the bug, before concluding it's gone. A
keyboard opening or closing changes `MediaQuery` and rebuilds everything
that depends on it. Switching tabs, an unrelated manager firing, or a
`setState` higher up can do the same. Look for a path that changes the same
data without those side effects (e.g. deleting instead of renaming, so no
keyboard is involved). Say in the report that the reporter's steps don't
show the bug and why. In PR mode, also say whether the PR's own manual-test
steps would pass with or without the fix.

Once it reproduces, **replay the final steps once more from a fresh
install** (uninstall, rerun, re-seed) to confirm the written steps alone are
enough. Only that replay makes it verified.

## Step 6 — Report

Write the report to the scratchpad as `repro-<repo-name>-<n>.md` (or
`repro-<slug>.md` without an issue), and show it in chat. Lead with exactly
one status:

- **✅ Reproduced**: verified on `<device>, <OS>`, at `<commit>`.
- **❌ Not reproduced**: the steps were performed and the bug didn't appear.
  Include what was tried and what to ask the reporter.
- **⚠️ Can't verify**: why (Step 2). The steps below are best-effort and
  **unverified**. If part was verified, say where verification ends.

Then:

```markdown
## Environment
- App: <app> @ <commit> (<branch or "origin/<default>">)
- Device: <iPhone 17 Pro simulator, iOS 26.5> / <Pixel_9_Pro emulator, Android 17>
- Backend: <local emulators> (pro-iq only)

## Seed data
<table or list of every record and setting, with concrete values>

<details><summary>Machine-loadable seed</summary>

<seed.json fragment or Firestore documents, when the project has a form>
</details>

## Steps
1. Fresh install, then <first action>.
2. ...

**Expected:** ...
**Actual:** ... ![actual](<image URL>)

## Evidence
<log lines / exception and stack; other images inline>

## Reporter's / PR's steps
<only if they don't show the bug: why (Step 5), and in PR mode whether the
PR's manual-test steps would pass with or without the fix>

## Likely cause
<file:line and one or two sentences, if the code makes it clear; otherwise omit>
```

Make one side-by-side image of the key before/after (or expected/actual)
screens, e.g. `magick a.png b.png -resize 35% +append -crop
<width>x<height>+0+0 +repage before-vs-after.png`.

**Everything goes on GitHub; nothing stays on the computer.** The report
and its images belong in the PR (or issue), and Step 7 deletes the local
copies. Publish the images with `scripts/publish-media.sh <repo-dir>
<owner>/<repo> pr-<n> <files>` (or `issue-<n>`). It pushes them to the
repo's orphan `pr-media` branch and prints a URL for each. In the report,
show the side-by-side image at the top and the other evidence images inline
(`![before, stale list](<url>)`), never local paths. Keep it to the images
that show something: seeded state, the bug, the fix, and anything the text
refers to.

- **PR mode:** post the report as a PR comment (`gh pr comment <n> --repo
  <owner>/<repo> --body-file <report>`) without asking, then fix the PR's
  manual-test steps if needed (see **PR mode**). Link the comment in chat.
- **Run on its own from an issue:** ask whether to post it on the issue.
  That's outward-facing, so publish the images and post only on a yes.
- **Called by `ship-ticket`:** publish the images under `issue-<n>` and
  return the report (with image URLs) and status. `ship-ticket` puts it in
  its PR body. Don't post anything else.

Also show the report in chat, and send the side-by-side image with
`SendUserFile` so the user sees it from another device.

## Step 7 — Clean up

- Stop the `flutter run` process and, for pro-iq, the emulators this skill
  started.
- Shut down devices this skill booted (`adb emu kill`, `xcrun simctl
  shutdown <udid>`), after turning the emulator's animations back on. Leave
  devices that were already running. If you shut down one of the user's
  devices for this run, say which in the final message.
- Never create devices, so there are none to delete. If an earlier run
  left a device it created (e.g. `Repro iPhone`, `Repro_Phone`), delete it
  (`xcrun simctl delete`, `avdmanager delete avd`).
- Delete everything this run wrote locally: screenshots (evidence and
  `work/`), the report, the side-by-side image, and any helper scripts.
  The user doesn't want leftover data on their computer; what matters is
  on GitHub (Step 6). If nothing was posted (the user said no), the report
  in chat and the image sent with `SendUserFile` are the record. When
  called by `ship-ticket`, leave this to its Step 8.
- Remove worktrees this skill created (Step 3's `-repro-<n>`, or PR mode's
  `-pr-<n>-before` / `-pr-<n>-after`) with `git -C <repo-dir> worktree
  remove <path>`, after checking they have no changes you made on purpose.
  Never `--force` over uncommitted changes without looking.
