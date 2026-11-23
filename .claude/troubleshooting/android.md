# Android

## Emulator

### Emulator hangs on boot (`offline` in adb) or crawls

- **Symptom:** the VM sits idle and `adb devices` shows `offline`, or the
  emulator is extremely slow.
- **Cause:** this Mac has 16 GB of RAM and is often swapping; with swap
  nearly full the emulator can't boot properly.
- **Fix:** check `sysctl vm.swapusage` before booting. If it's nearly full,
  tell the user what's using memory rather than retrying. Don't change the
  AVD's `config.ini`.
- **Related:** `reproduce-bug` Step 4.

### `Can't find service: package` / adb stays `offline` after boot

- **Cause:** the emulator's system server stopped responding.
- **Fix:** `adb emu kill`, then boot it again.

### `INSTALL_FAILED_INSUFFICIENT_STORAGE`

- **Fix:** check `adb shell df -h /data`, shut the emulator down and boot it
  with `-wipe-data` (allowed without asking). Don't uninstall the user's
  other apps to make room.

### `adb shell input text` doesn't type into Flutter text fields

- **Fix:** type with key events; `reproduce-bug/scripts/android.sh type`
  does this.

### Taps land on a Google sign-in or system screen

- **Cause:** a script of taps ran ahead of a slow emulator.
- **Fix:** never chain steps blind; screenshot after each step and check
  `android.sh focus` shows the app's package.

## Builds

### Release build fails without `keystore.properties`

- **Cause:** anglers-log and activity-log release builds need
  `android/keystore.properties` and the release keystore, which are
  gitignored and never copied into worktrees.
- **Fix:** for repros and verification, build debug APKs
  (`flutter build apk --debug`). Never copy release keystores into a
  worktree.
