# iOS, macOS, Xcode & Swift Package Manager

All four apps are on SPM (pro-iq 2026-08-18; activity-log, anglers-log; tapd
2026-09-19). CocoaPods is gone everywhere.

## Swift Package Manager

### `Could not resolve package dependencies` during a release build

- **Symptom:** iOS/macOS build fails resolving packages, a missing `.zip`
  under `SourcePackages/artifacts`, or an archive that "does not contain a
  binary artifact".
- **Seen:** activity-log `2.0.5+2026111702`, 2026-11-17.
- **Cause:** a concurrent build (another session's `flutter run`, or Xcode)
  resolving packages into the same `build/ios/SourcePackages`.
- **Fix:** make sure nothing else is building the project, then
  `rm -rf <flutter dir>/build/ios/SourcePackages` (or `build/macos/...`)
  and rebuild. Don't clear a healthy cache pre-emptively.
- **Related:** `build-and-upload-release` Step 7 and Step 9.

### `/FirebaseCrashlytics/upload-symbols: No such file` after removing CocoaPods

- **Symptom:** build fails in a Run Script phase calling
  `${PODS_ROOT}/FirebaseCrashlytics/upload-symbols`.
- **Seen:** tapd, 2026-09-19.
- **Cause:** a legacy CocoaPods Crashlytics phase left behind after
  `pod deintegrate` + `flutterfire reconfigure`.
- **Fix:** delete that one Run Script phase; the FlutterFire phase replaces
  it.

### FlutterFire Crashlytics phase can't find its script / dSYMs with SPM

- **Symptom:** the FlutterFire upload-symbols phase fails to find its script
  once CocoaPods is gone, or can't find SPM-built frameworks.
- **Cause:** `flutterfire_cli` < 1.4.1 bug (fixed in 1.4.1, PR #453); and
  `flutter build ipa` clones SPM packages into
  `${SRCROOT}/../build/ios/SourcePackages`, outside BUILD_DIR/DerivedData.
- **Fix:** use `flutterfire_cli` ≥ 1.4.1 (installed globally on this Mac).
  tapd's phase in `ios/Runner.xcodeproj/project.pbxproj` is hand-patched to
  also search `${SRCROOT}/../build/ios/SourcePackages`. Re-running
  `flutterfire reconfigure` overwrites that patch; re-apply it.

### Migrating an app from CocoaPods to SPM

- **Plugin SPM-readiness gaps** only show up by actually running
  `flutter build` with SPM on (`video_player_avfoundation` and
  `permission_handler_apple` needed scoped `flutter pub upgrade` bumps).
- **Strip CocoaPods with `pod deintegrate`**, not by hand-editing
  `project.pbxproj`. It does *not* remove the stale `Pods/Pods.xcodeproj`
  reference in `Runner.xcworkspace/contents.xcworkspacedata`; remove that by
  hand.
- **Build-time regression** after removing the hand-written
  `FirebaseFirestore` git-pod override while still on CocoaPods (~3x)
  disappears once fully on SPM (prebuilt abseil/gRPC binaries).
- `flutter config --enable-swift-package-manager` is `true` machine-wide.
- **Related:** memory `project_spm_migration.md`.

## Xcode & signing

### Simulator tool: `Xcode is installed but not selected`

- **Symptom:** the iOS Simulator tool's `attach` fails with `Run sudo
  xcode-select -s /Applications/Xcode.app/Contents/Developer`.
- **Fix:** it needs the user's password, so the user runs that command
  themselves. Tell them right away and wait; don't switch to driving the
  Simulator app another way without saying so.

### Simulator tool: `The user has not granted Claude access to "iPhone …"`

- **Fix:** the user attaches the device in the simulator panel and clicks
  "Let Claude use it" (once per device). Ask right away, since they may be
  away from the screen; offer Android only if the bug isn't iOS-specific.
- **Related:** `reproduce-bug` → devices.md.

### `.ipa` export fails with "No Accounts" / "missing Xcode-Token"

- **Seen:** tapd, 2026-09-19.
- **Cause:** the Apple ID session in Xcode expired.
- **Fix:** the user signs in again in Xcode → Settings → Accounts. Not
  something to work around from a script.

## Worktrees

### iOS build fails in the FlutterFire Crashlytics step in a fresh worktree

- **Cause:** gitignored config (`firebase.json`, Firebase options, plists)
  isn't copied into new git worktrees.
- **Fix:** copy the gitignored config from the main checkout, as
  `reproduce-bug` Step 3 describes.
- **macOS too (pro-iq, 2026-11-23):** `flutter build macos` in a fresh
  worktree fails in turn with `Did not find the file passed to
  "--dart-define-from-file"`, then `Build input file cannot be found:
  '.../macos/Runner/GoogleService-Info.plist'` (the tenant-copy script phase
  runs after Xcode's input check), then `PathNotFoundException ...
  firebase.json` in the FlutterFire symbol-upload phase. Copy all four up
  front: `dart-defines/`, `firebase.json`,
  `lib/firebase_options/<tenant>.dart` → `lib/firebase_options.dart`, and
  `macos/Runner/Firebase/<tenant>/GoogleService-Info.plist` →
  `macos/Runner/`. The first clean release build compiles every SPM package
  for arm64 and x86_64. It can take 30+ minutes under memory pressure and
  look hung (xcodebuild at 0% CPU while `swift-frontend` runs).
