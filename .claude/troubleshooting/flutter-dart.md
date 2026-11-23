# Flutter & Dart

## Compiler & language

### `--dart-define` value is empty at runtime

- **Symptom:** `String.fromEnvironment(...)` (or `int`/`bool`) returns `""`
  / the default even though the `--dart-define` or
  `--dart-define-from-file` value is set. `flutter analyze` is clean. In
  pro-iq, every tenant asset path ended in a trailing slash
  (`"assets/tenants/pro-iq/"`) and failed to load.
- **Seen:** pro-iq (`lib/tenant_config.dart`), 2026-08-21.
- **Cause:** Flutter's frontend only folds `fromEnvironment` in a
  compile-time constant expression. Inlined into a non-const expression
  (e.g. a string interpolation) without `const`, it silently returns the
  default.
- **Fix:** keep `const` on the call itself, even mid-expression:
  `"${const String.fromEnvironment("KEY")}"`.
- **Didn't work:** testing with bare `dart run`; the standalone VM resolves
  these at runtime regardless of const-ness. Test with
  `flutter test --dart-define=KEY=value`.
- **Related:** memory `feedback_const_from_environment.md`.

## Widgets

### "ListTile wrapped in a ColoredBox" assertion

- **Symptom:** Flutter asserts that a `ListTile` is wrapped in a
  `ColoredBox`, although a `Material` ancestor exists.
- **Seen:** adair-flutter-lib (`lib/widgets/nav_rail_content.dart`).
- **Cause:** a `ColoredBox` (or `Container(color:)`) sits *between* the
  nearest `Material` and the `ListTile`. `ListTile` paints `tileColor` with
  `Ink` on its nearest `Material`, which the colored box would cover. It's
  about the path, not whether `Material` exists.
- **Fix:** make the nearest ancestor a `Material(color: ...)` instead of
  `Container(color: ...)` / `ColoredBox`.

## Flutter upgrades

### Flutter 3.50 / `material_ui` migration gotchas

- **Seen:** all projects, 2026-11-12 (Flutter 3.50 / Dart 3.14, moving from
  `package:flutter/material.dart` to `material_ui` / `cupertino_ui`).
- **Non-English Material strings fall back to English:** `flutter gen-l10n`
  still generates a `localizationsDelegates` list of the *legacy* Material
  delegates. Don't spread `X.localizationsDelegates` into a `MaterialApp`;
  use `X.delegate` + `...GlobalMaterialLocalizations.delegates`
  (material_ui).
- **Ambiguous-import errors in generated l10n after `dart fix --apply`:**
  it rewrites the generated files. Re-run `flutter gen-l10n` after any
  `dart fix --apply`. It also adds `pkg: any` deps to `pubspec.yaml` via
  `depend_on_referenced_packages`; revert those.
- **Legacy-material dependencies (Syncfusion, fl_chart, mapbox) can't find
  `Theme` / `MaterialLocalizations`:** apps wrap `MaterialApp` with
  `materialUiCompatibilityBuilder` (adair-flutter-lib `utils/widget.dart`).
  The bridge maps only colorScheme/textTheme/platform/visualDensity. Remove
  it once the deps migrate.
- **Android:** AGP 9.3.1 / Gradle 9.5.0 / KGP 2.4.20, but
  `android.builtInKotlin=false` stays until plugins (including our own
  `adair_install_attribution`) stop applying KGP.
- **Xcode 27 compile error `init(stringRepresentation:)` is ambiguous:**
  purchases-ios < ~5.90 (purchases_flutter 10.1–10.2). adair-flutter-lib
  now requires `purchases_flutter ^10.13.1`.
- **Related:** memory `project_flutter_350_material_ui_migration.md`.

## Tests & mocks

### Confusing mockito failures after adding a manager/wrapper member

- **Symptom:** `MissingStubError`, `noSuchMethod`, a type-cast error on a
  mock, or cascading "Cannot call `when` within a stub response" errors in
  unrelated tests.
- **Cause:** `test/mocks/mocks.mocks.dart` is stale; a member added to the
  real class doesn't appear in the generated mock.
- **Fix:** regenerate (`./gen_mocks.sh` in the app, or
  `dart run build_runner build` in adair-flutter-lib). Never hand-edit the
  generated file.
- **Related:** `adair-code-audit` Step 8.

### build_runner: "Cannot recurse at later or equal phase"

- **Symptom:** build_runner 2.16+ fails with
  `Cannot recurse at later or equal phase`.
- **Cause:** mockito's builder running over files other than
  `test/mocks/mocks.dart`.
- **Fix:** keep each project's `build.yaml` limiting mockito's builder to
  `test/mocks/mocks.dart`.

### "Won't compile" claims from read-only review agents

- **Symptom:** an Explore agent reports code that won't compile (often an
  extension method like `firstWhereOrNull`).
- **Cause:** agents can't run the analyzer and miss extensions resolved via
  re-exports.
- **Fix:** run `dart analyze lib test` from the Flutter root before
  reporting any compile-error finding.
