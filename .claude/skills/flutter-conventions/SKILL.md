---
name: flutter-conventions
description: >
  The rules every Dart/Flutter change in this monorepo must follow (pro-iq,
  anglers-log, activity-log, tapd, adair-flutter-lib): Dart style, wrappers
  vs. managers, error handling, spacing/typography, widget structure, pages
  and async, localizations, Firestore/protos, and tests. Load it before
  writing, editing, reviewing, or testing any Dart code, even a one-line
  fix. `flutter-coding-standards` (examples, reuse checks) and
  `flutter-test` (test patterns) build on these rules and don't repeat them.
---

# Flutter Conventions

The single source of truth for code rules. Other skills (`adair-code-audit`,
`flutter-coding-standards`, `flutter-test`, `ship-ticket`,
`crashlytics-triage`) point here instead of restating them.

This file has the rules for all code. Two companion files hold the rest.
Read them whenever the change touches their area:

| File | Read when the change touches |
|---|---|
| [firestore-protos.md](firestore-protos.md) | Firestore, protobuf messages, `DataManager` (mostly pro-iq) |
| [tests.md](tests.md) | Any `test/` file, mocks, or `StubbedManagers` |

**Changing a rule:** edit it here (or in a companion file), never in
`CLAUDE.md` or another skill. A rule for one sub-project goes in that
sub-project's `adair-code-audit` add-on file instead.

## Dart style

- **String literals** use double quotes. **Exception: `import` and `export` directives use single quotes** — do not flag or convert them.
- **Null checks** — always check `== null` (null case first), never `!= null`. This
  applies to **ternaries and `if`/`else` statements**, where both branches are present
  and the ordering choice actually matters. It does **not** apply to a single-branch
  early return (e.g. `if (cached != null) { return cached; }`) — there's no `else` to
  reorder, so `!= null` is fine there. In ternaries, the **positive condition** goes
  first (the condition as written, not its negation). This means null-check ternaries
  naturally put the `null` branch first:

```dart
// Bad — negated condition
errorText != null
    ? context.colorError.withValues(alpha: _backgroundAlpha)
    : null,

// Good — positive condition first; null branch is the consequence
errorText == null
    ? null
    : context.colorError.withValues(alpha: _backgroundAlpha),
```

A non-null-check ternary where the positive condition is first is also correct:

```dart
// Good — positive condition first, non-null both branches
showHeader
    ? Text(Strings.of(context).hint)
    : const SizedBox(),
```

- **Comment line length** — comments must not exceed 80 characters per line (the standard Dart line limit). Wrap long comments onto the next line.

- **Curly braces** — always use curly braces for `if`/`else`/`for`/`while` bodies, even single-statement ones:

```dart
// Bad
if (!mounted) return;

// Good
if (!mounted) {
  return;
}
```

- **Magic numbers** — raw numeric values for sizing, elevation, or radii must be
  declared as `static const` fields at the top of the class, or use the project's
  named spacing constants. Never use inline numeric literals for layout values.
- **`final` constants that could be `static const`** — a `final double _size = 20.0`
  that is not instance-dependent (no constructor parameters, no state) should be
  `static const double _size = 20.0`.
- **Boolean naming** — prefer a 3rd-person verb form over adding a prefix word:
  - Multi-word: use the verb in present-tense 3rd person, e.g. `extendsBodyBehindAppBar`,
    `centersContent`, `restrictsWidth`, `alignsRight`, `obscuresText`, `popsOnTap`,
    `includesYears`. This avoids the extra `should`/`is` word.
  - Single-word or past-participle state: `is` prefix is fine, e.g. `isEnabled`,
    `isRequired`, `isAutofocused`, `isNavRailContent`.
  - Never use `should` as a prefix — it's always replaceable with the verb form above.
- **Doc comments for instance variables** — go directly above each variable declaration,
  not inside the class-level doc comment. See `AutocompleteTextInput` in
  `adair-flutter-lib/lib/widgets/autocomplete_text_input.dart` as the reference.
- **Unused required parameters** — must use the `_` wildcard, not a named identifier
  (e.g. `void onTap(BuildContext _)` when `context` is not used).
- **Dead imports** — remove imports no longer referenced in the file.

- **Inline single-use variables** — do not assign a value to a named variable if
  it is only used once immediately after. Inline the expression at the call site:

```dart
// Bad:
final activity = Activity.fromMap(map);
expect(activity.createdAt, 0);

// Good:
expect(Activity.fromMap(map).createdAt, 0);
```

## Dependency versions

- **Pin or update a pub package version in `pubspec.yaml` only.** Never hand-edit
  a lock file (`pubspec.lock`, iOS `Podfile.lock`, etc.) to change a version —
  lock files are regenerated output (`flutter pub get`, `pod install`), not a
  source of truth. Editing a lock file directly can leave it inconsistent with
  `pubspec.yaml` and silently reverts on the next resolve.

## Dev tooling

- `screenshots/capture/` and each app's `screenshots/capture/` are dev
  tooling (host CLIs and an on-device capture harness), not app code. The
  app-code rules don't apply there: `TimeManager` instead of `DateTime`,
  `_log.e` in every `catch` (there's no Crashlytics), wrappers for
  third-party libraries, and generated mocks. The Dart style, constants, and
  test conventions still do.

## Wrappers vs. managers

- **Wrappers** (`adair-flutter-lib/lib/wrappers/`) are thin, 1:1 delegations to a
  Firebase or platform SDK. They contain no business logic — only the minimal surface
  area needed to make the underlying API testable. Example: `FirestoreWrapper.doc()`,
  `StorageWrapper.putData()`.
- **Every third-party library must have a wrapper** so its methods can be mocked in
  tests. If a pub package class is used directly in production code (e.g.
  `VideoPlayerController`), create a wrapper around it before writing
  tests. Place it in `wrappers/` following the standard singleton pattern.
- **Managers** (`adair-flutter-lib/lib/managers/` or `pro-iq/lib/managers/`) contain
  business logic and orchestration. A manager may call one or more wrappers and may
  also call other managers freely. Example: `StorageManager.uploadBytes()` combines
  `StorageWrapper.putData()` + `StorageWrapper.getDownloadURL()` into one operation.
- **Sign-out cleanup lives in managers.** Each manager overrides
  `Manager.onSignOut()` to clear its own per-user state; it runs while the
  user is still authenticated, so auth-gated writes (e.g. removing an FCM
  token, flushing usage) work. UI calls `AuthManager.get.signOut()` (from
  `adair_flutter_lib/managers/auth_manager.dart`), never a page-level or
  util sign-out helper. A manager only gets the hook if it's in
  `AdairFlutterLibApp.managers`.
- **Singleton constructors stay private.** Never give a manager (or wrapper)
  a public or `@visibleForTesting` constructor — only the private `._()`.
  Tests swap instances with `set()` (a mock) or `reset()` (a fresh real
  instance, then use `.get`). **Exception:** anglers-log's `AppManager`
  keeps its public constructor for now, because `TestAppManager` in
  `test/app_manager_test.dart` subclasses it (see its TODO).
- **Managers aren't Riverpod consumers.** Singletons have no `Ref`, so they
  can't read providers like `currentUserProvider`. When a manager needs the
  current user, the caller passes it in.
- **Always use `TimeManager` for the current time — never raw `DateTime`.** Use
  `TimeManager.get.currentTimestamp` / `currentDateTime` (from
  `adair_flutter_lib/managers/time_manager.dart`) instead of `DateTime.now()`,
  even when the value is time-zone independent (e.g. an epoch timestamp), so time
  can be stubbed in tests. `TimeManager.get.init()` must be awaited at startup
  with the app's other managers before any use — if an app doesn't init it yet
  (e.g. tapd, which also has its own unrelated `TimeManager`), add the init
  rather than falling back to `DateTime`.

## Moving a wrapper or manager to adair-flutter-lib

When a wrapper or manager that exists in a downstream project (`pro-iq`,
`anglers-log`, etc.) is useful across multiple projects, move it to
`adair-flutter-lib`. Follow these steps:

1. **Create** the new file in `adair-flutter-lib/lib/wrappers/` (or `managers/`)
   using the standard singleton pattern (`get get`, `@visibleForTesting` set/reset).
2. **Add the package** to `adair-flutter-lib/pubspec.yaml` if the wrapper depends on
   a new pub package.
3. **Add the mock** to `adair-flutter-lib/test/mocks/mocks.dart`
   (`@GenerateMocks([MyWrapper])`) and expose a `MockMyWrapper` field on
   `adair-flutter-lib/test/test_utils/stubbed_managers.dart`, calling
   `MyWrapper.set(myWrapper)` in its constructor.
4. **Delete** the original file from the downstream project.
5. **Update all call sites** in the downstream project: change imports to
   `package:adair_flutter_lib/wrappers/my_wrapper.dart` and replace
   service-locator patterns (e.g., `AppManager.get.myWrapper`,
   `MyWrapper.of(context)`) with `MyWrapper.get`.
6. **Update downstream test stubs**: remove the local `MockMyWrapper` field and
   `when(app.myWrapper).thenReturn(...)` stub. Downstream tests now access the
   mock via `managers.lib.myWrapper` (set automatically by adair-flutter-lib's
   `StubbedManagers` constructor).
7. **Regenerate mocks** in both `adair-flutter-lib` and the downstream project:
   `dart run build_runner build`.

## Error handling

- **No empty `catch` blocks.** Every `catch` must at minimum call
  `_log.e(e, reason: "…")` to log the exception to Firebase Crashlytics. Declare
  `_log` at the file level: `final _log = Log("ClassName");`.
  **Exception:** a caller may skip `_log.e` when the callee's documented
  contract is that it logs every failure before rethrowing (e.g.
  `VideoUpload.uploadClips`), so the error isn't recorded twice. Leave a
  comment in the `catch` saying where it's logged; the catch still handles
  the error (e.g. shows a snackbar), so it isn't empty.
- **User-action errors** (thrown by a button tap outside a form, e.g. toggling a
  group membership): call `_log.e`, then show
  `showErrorSnackBar(context, <message>)` with a meaningful message. Check
  `!mounted` before using `context` after an `await`.
- **Form errors** (thrown while saving a dialog or form): call `_log.e`, then set
  the inline `_error` string and display it with `ErrorText` (from
  `adair_flutter_lib/widgets/error_text.dart`) — see
  `_SaveItemDialogState._save` in `pro-iq/lib/widgets/save_item_dialog.dart`.

## Spacing & padding

- Always import spacing from `adair_flutter_lib/res/dimen.dart` and use named
  constants (`insetsDefault`, `paddingSmall`, `insetsHorizontalDefault`, etc.).
- Default to `insetsDefault` when no specific size is required.
- Never use raw `EdgeInsets.all(16)` or inline numeric spacing literals.

## Typography & styling

- **Font sizes**: Never use hardcoded font size constants. Always use
  `Theme.of(context).textTheme.*` styles (e.g. `labelSmall`, `bodyMedium`,
  `headlineMedium`). Use the closest available style even if it differs by 1–2pt
  from the design.
- **Font weight**: Use `fontWeightBold` (`FontWeight.w500`) or `fontWeightBoldTitle`
  (`FontWeight.w700`) from `adair_flutter_lib/res/style.dart`. Do not define custom
  `FontWeight` constants.
- **Letter spacing**: Never adjust `letterSpacing` unless explicitly requested.
- **Card border radius**: Derive from `Theme.of(context).cardTheme.shape` via a
  helper rather than a hardcoded constant.
- **Dividers**: Use `MinDivider` from `adair_flutter_lib/widgets/min_divider.dart`.
  It supports `color`, and `width` (fixed-width rule).

## Constants & helper functions

- Constants and helper functions belong to the class that uses them (as
  `static const` / `static` members). Define file-level constants or top-level
  functions **only** when they are shared across multiple classes or are part of a
  public utility API (e.g. functions in `adair-flutter-lib/lib/utils/`).
- Byte count formatting (e.g. `"110.5 MB"`): use `formatBytes` from
  `adair_flutter_lib/utils/string.dart`.

- **No `@visibleForTesting` fields to shorten waits.** Don't add a mutable
  `@visibleForTesting` field just so a test can shrink a timeout, delay, or
  interval; it bloats production code for the test's sake. Keep the value a
  private `static const`, and have the test hardcode the same duration and
  advance fake time past it (`FakeAsync().run` from
  `package:quiver/testing/async.dart` in unit tests, `tester.pump(duration)`
  in widget tests). Example in `flutter-coding-standards`.

## Widget structure

- Keep `build()` short. Extract each meaningful section to a `_build*` private
  method. When a `Column` / `Row` has multiple children, each child should be a
  `_build*` call — not an inline widget tree.
- `build()` comes after lifecycle methods (`initState`, `dispose`, `didUpdateWidget`, etc.) but before any other methods; `_build*` helpers follow it.
- Conditional widgets: invert the condition and `return const SizedBox()` early.
  Do **not** use `if (cond) ...[widget]` spread syntax inside widget lists.

```dart
// Prefer:
Widget _buildCoach(BuildContext context) {
  if (user.coachName.isEmpty) {
    return const SizedBox();
  }
  return Text(user.coachName);
}
```

  **Exception: `TableRow.children`.** Every row in a `Table` must have the same
  number of children in the same column order, so a whole column must
  appear/disappear together across the header row and every data row. Use
  `if (cond) cell` directly in each row's `children` list, applying the exact
  same conditions in the same order across all rows, instead of forcing a
  `_build*` + early-return `SizedBox()` per cell.
- **Don't pass `BuildContext` to helper methods in a `State`/`ConsumerState`
  class.** The state already has an inherited `context` getter — reference it
  directly instead of threading a `context` parameter through every `_build*`
  or private method. Only `build(BuildContext context)` itself (and other
  framework-overridden signatures) should declare the parameter. This does
  **not** apply to `StatelessWidget`/`ConsumerWidget`, which have no instance
  `context` and must receive it as a parameter.

## Icon buttons

- Icon buttons get the app's default "elevated" styling for free from
  `iconButtonTheme` (see `pro-iq/lib/main.dart`) — don't pass `color:` or a
  custom `style:` unless deviating below.
- **Destructive icon buttons** (delete, remove, etc.) must pass
  `style: errorIconButtonStyle(context)` from
  `pro_iq/lib/res/icon_button_style.dart`.
- **Compact icon buttons** overlaid on cards/thumbnails (e.g. video card,
  `EditPhotoBadge`) use `condensedElevatedIconButtonStyle(context)` /
  `condensedErrorIconButtonStyle(context)` instead of the default variants.
  Never pass a custom `iconSize`/size override — add a new style function if
  a third size is ever needed.

## Pages & async

- Page widgets (`lib/pages/*_page.dart`) must use **`ScrollPage`** from
  `adair_flutter_lib` as their root — not `Scaffold`. **Exception:** pages whose
  primary content is a scrollable list should use a plain `Scaffold` with a
  `ListView` (or `ListView.separated`) so items are built lazily and `ListTile`
  theming (e.g. `tileColor`) works reliably.
- For async content use **`AsyncBuilder.future`** or **`AsyncBuilder.stream`**
  in place of `FutureBuilder` and `StreamBuilder`. The `errorReason` parameter
  is required. Import: `package:adair_flutter_lib/widgets/async_builder.dart`.

## Async / setState pattern

In async methods that contain a `try`/`catch`, use local variables to collect results
and make a **single `setState` call at the end** of the method. Do not call `setState`
inside `try` or `catch` blocks.

```dart
// Prefer:
Future<void> _doWork() async {
  setState(() => _isBusy = true);
  var result = "";
  var error = "";
  try {
    result = await someAsyncCall();
  } catch (_) {
    error = "Something went wrong.";
  }
  if (!mounted) {
    return;
  }
  setState(() {
    _isBusy = false;
    _result = result;
    _error = error;
  });
}
```

See `_ResetPasswordDialogState._sendReset` in
`adair-flutter-lib/lib/pages/sign_in_page.dart` as the reference example.

## Localizations

- Never modify `*_localizations*.dart` files directly — they are generated.
- After editing any `.arb` file, regenerate with `flutter gen-l10n` from the project root.
- Only add strings to `*_en_US.arb` when the US spelling differs from the base `*_en.arb` string (e.g. "canceled" vs "cancelled"). Do not mirror new strings into `_en_US.arb` otherwise.
- **Translate every new key into all other supported languages in the same change —
  never defer it.** `flutter gen-l10n` silently falls back to the base-locale string
  for any locale missing a key, so an untranslated string still compiles, builds, and
  displays (in the base language) with no error — it's easy to miss in review and easy
  to ship by accident. When you add a key to a base ARB file, add the same key with a
  real translation (not placeholder or copied-English text) to every other locale file
  that requires full coverage, in the same edit. Each sub-project's
  `<submodule>/.claude/skills/adair-code-audit/SKILL.md` → **Step 10 — ARB locale
  rules** lists which of its locale files require full coverage vs. which are
  spelling-variant-only and can be skipped.

