# Devices: choosing, booting, installing, and driving the app

Shared by `reproduce-bug`, `verify-feature`, and `ship-ticket`. Follow it
whenever a skill runs an app on a simulator or emulator. Device-specific
errors and their fixes are in `.claude/troubleshooting/android.md` and
`ios-xcode-spm.md`.

## Choosing and booting a device

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

## iOS

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

## Android

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

## Fresh install and run

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

## Driving the app

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
shots taken just to see the screen go in a `work/` subfolder, which the
calling skill's clean-up step deletes.

Watch the logs too (`adb logcat`, or the `flutter run` output): an
exception, assertion, or `_log.e` there is often the clearest evidence, so
capture the relevant lines.

**Per-app notes** (fresh-install hurdles, so you don't rediscover them):

| App | Notes |
|---|---|
| anglers-log | Android package `com.cohenadair.anglerslog`. Grant `ACCESS_FINE_LOCATION` and `ACCESS_COARSE_LOCATION` on install. Onboarding: a "Location Accuracy" system dialog (No thanks), Next, Next, Set Permission, Next, then "Not Now" on the Pro page. The first launch of a debug build takes 30–60 s on the emulator. |

Add a row when you learn something about another app.
