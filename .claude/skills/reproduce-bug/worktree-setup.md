# Preparing a worktree to build and run an app

Shared by `reproduce-bug`, `verify-feature`, `ship-ticket`, and
`crashlytics-triage`. A fresh git worktree has none of the gitignored
config the apps need, so prepare it before building:

1. **Copy gitignored config** the build needs (Firebase options and plists,
   `firebase.json`, `sensitive.properties`, pro-iq's `dart-defines/`) from
   the main checkout. Without `firebase.json`, iOS builds fail in the
   FlutterFire Crashlytics upload step. Public apps' secrets (e.g.
   `sensitive.properties`) are symlinks into iCloud `projects/keys`; `cp -P`
   copies the link, not the key, so no copy of a key lands in the worktree:
   ```bash
   cd <repo-dir> && git ls-files --others --ignored --exclude-standard \
     | grep -vE '(^|/)(build|\.dart_tool|Pods|node_modules)/' \
     | grep -E '(firebase_options.*\.dart|GoogleService-Info\.plist|google-services\.json|(^|/)firebase\.json$|sensitive\.properties|^dart-defines/)' \
     | while read -r f; do mkdir -p "<worktree>/$(dirname "$f")"; cp -P "$f" "<worktree>/$f"; done
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

If a build fails anyway, search `.claude/troubleshooting/` for the error
(e.g. `ios-xcode-spm.md` → Worktrees).
