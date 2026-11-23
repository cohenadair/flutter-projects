# Release builds & stores

The release skills own their own error tables (see the README). This file
holds the incidents and quirks behind them.

## Release builds

### Release shipped without merged fixes

- **Seen:** activity-log `2.0.5+2026111701`.
- **Cause:** the build compiles the local checkout; merged PRs weren't
  pulled.
- **Fix:** pull the app repo and adair-flutter-lib (`--ff-only`) before
  every non-retry build. `build-and-upload-release` Step 4.

### Release gave every user Pro for free

- **Seen:** anglers-log `2.8.0+2026092502`.
- **Cause:** a local dev override in adair-flutter-lib's
  `SubscriptionManager` (`bool get isPro => true;`) compiled into the
  release.
- **Fix:** `build-and-upload-release` Step 5 checks and reverts it before
  every build.

### Release upload picked up another session's uncommitted edit

- **Seen:** activity-log `2.0.5+2026111702` (Android).
- **Fix:** before every run, check for other builds of the project and
  re-check `git status` (`build-and-upload-release` Step 7).

### Version prompt silently does nothing

- **Cause:** `bump_pubspec_version.sh`'s `read -p` only fires on a real TTY,
  which a tool invocation isn't.
- **Fix:** always pass `--version=X.Y.Z` explicitly.
