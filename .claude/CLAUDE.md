# Collaboration preferences

- **Before making any code change**, briefly list any possibly unintended side-effects (other
  features, pages, or tests that may be affected). Do this even when the change is explicitly
  requested. Keep the warning concise — bullet points are fine.

---

# Flutter Coding Conventions

## Dart style

- Always use **double quotes** for string literals.
- Always use **curly braces** for `if` statement bodies, even single-line returns.
- No magic numbers — declare **`static const`** fields at the top of the class for
  elevation, radii, or any fixed value not covered by dimen.dart.
- Boolean variables and fields must use a verb prefix: `is`, `can`, `does`, `has`,
  `should`, `will`, etc. (e.g. `isLoading`, `canEdit`, `hasValue`).
- **Doc comments for instance variables** go directly above each variable declaration,
  not inside the class-level doc header. See `AutocompleteTextInput` in
  `adair-flutter-lib/lib/widgets/autocomplete_text_input.dart` as the reference example.
- **Unused required parameters** must use the wildcard name `_` instead of a named
  identifier (e.g. `void onEvent(BuildContext _)` when `context` isn't needed).

## Wrappers vs. managers

- **Wrappers** (`adair-flutter-lib/lib/wrappers/`) are thin, 1:1 delegations to a
  Firebase or platform SDK. They contain no business logic — only the minimal surface
  area needed to make the underlying API testable. Example: `FirestoreWrapper.doc()`,
  `StorageWrapper.putData()`.
- **Managers** (`adair-flutter-lib/lib/managers/` or `pro-iq/lib/managers/`) contain
  business logic and orchestration. A manager may call one or more wrappers but should
  never call another manager. Example: `StorageManager.uploadBytes()` combines
  `StorageWrapper.putData()` + `StorageWrapper.getDownloadURL()` into one operation.

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
- **User-action errors** (thrown by a button tap outside a form, e.g. toggling a
  group membership): call `_log.e`, then show
  `showErrorSnackBar(context, <message>)` with a meaningful message. Check
  `!mounted` before using `context` after an `await`.
- **Form errors** (thrown while saving a dialog or form): call `_log.e`, then set
  the inline `_error` string and display it via `EmptyOr`/`styleError` — see
  `_AddGroupDialogState._save` in `pro-iq/lib/pages/my_players_page.dart`.

## Spacing & padding

- Always import spacing from `adair_flutter_lib/res/dimen.dart` and use named
  constants (`insetsDefault`, `paddingSmall`, `insetsHorizontalDefault`, etc.).
- Default to `insetsDefault` when no specific size is required.
- Never use raw `EdgeInsets.all(16)` or inline numeric spacing literals.

## Widget structure

- Keep `build()` short. Extract each meaningful section to a `_build*` private
  method. When a `Column` / `Row` has multiple children, each child should be a
  `_build*` call — not an inline widget tree.
- `build()` is always the **first** method in the class; `_build*` helpers follow it.
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

## Icon buttons

- **Action icon buttons** (edit, navigate, add, etc.) must use
  `color: context.colorApp` to distinguish them from decorative icons.
- **Destructive icon buttons** (delete, remove, etc.) must use
  `color: Theme.of(context).colorScheme.error`.

## Pages & async

- Page widgets (`lib/pages/*_page.dart`) must use **`ScrollPage`** from
  `adair_flutter_lib` as their root — not `Scaffold`. **Exception:** pages whose
  primary content is a scrollable list should use a plain `Scaffold` with a
  `ListView` (or `ListView.separated`) so items are built lazily and `ListTile`
  theming (e.g. `tileColor`) works reliably.
- For async content use **`SafeFutureBuilder`** in place of both `FutureBuilder`
  and `StreamBuilder`. The `errorReason` parameter is required.

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

## Protos

- Canonical import: `package:pro_iq/models/gen/protobuf/pro_iq.pb.dart`
  The `models/gen/` (non-`protobuf/`) path is stale — never use it.
- Proto strings default to `""` when unset, not null. Guard with `.isEmpty`,
  not null checks.
- **Every Firestore-backed proto must have `string id = 1;`** as its first field.
  The ID is never stored in Firestore — it is assigned from `snapshot.id` in the
  corresponding `_snapshotTo*` method in `DataManager`:
  ```dart
  Foo? _snapshotToFoo(DocumentSnapshot<Map<String, dynamic>> snapshot) {
    final foo = _snapshotToProtobufType<Foo>(snapshot, () => Foo());
    return foo?..id = snapshot.id;
  }
  ```
  Streams and collections of these types use `List<Foo>`, not `Map<String, Foo>`.
  Never pass a separate `String fooId` alongside a `Foo` object — use `foo.id`.
- **Clear `id` before writing to Firestore.** The `id` field is derived from the
  document ID and must not be stored in the document itself. Call `clearId()`
  before serializing: `(foo..clearId()).toProto3Json()`.

## Tests

- **No `group()`** — use a flat list of `test()` / `testWidgets()` calls inside
  `void main()`.
- **One test per branch** — every `if/else`, `??`, ternary, and `switch` case gets
  its own `test()`. Do not combine branches in a single test.
- Before writing tests, read the implementation and call out any branch that can
  never be reached, explaining why.
- **Never construct real managers in tests.** Always inject mocks via
  `StubbedManagers`. Access lib-level mocks through `managers.lib.*`.
- **Never modify `mocks.mocks.dart`** — it is generated. To regenerate, run
  `pro-iq/gen_mocks.sh` from the repo root.
- Widget tests always use **`pumpContext`** (from
  `adair-flutter-lib/test/test_utils/testable.dart`) — not plain `pumpWidget`.
- Use `tester.pumpAndSettle()` after tap / scroll / stream events.
- Stub sync values with `thenReturn`; stub futures/streams with
  `thenAnswer((_) async => ...)` / `thenAnswer((_) => Stream.value(...))`.
- **Test description casing** — descriptions must start with a capital letter, unless
  the first word is a method or function name being exercised (e.g. `"capitalize returns
  empty string when input is empty"` is fine; `"widget renders without errors"` is not).
- **Test helper functions** — declare as local functions inside `main()`, after
  `setUp`/`tearDown` and before the first `test()`. This placement applies even when
  adding helpers to an existing file — insert them before the first test, not at the
  bottom of `main()`. Name them with a plain lowercase identifier (no leading
  underscore). See `colorCircle` and `openTeamDropdown` in
  `pro-iq/test/pages/all_users_page_test.dart` as the reference example.
- **`*AndSettle` helpers** — use `tapAndSettle`, `ensureVisibleAndSettle`, and
  `enterTextAndSettle` (from `adair-flutter-lib/test/test_utils/widget.dart`)
  instead of the raw `tester.*()` + `tester.pumpAndSettle()` two-liner.
- **No tests for wrappers** — wrappers are thin, 1:1 SDK delegations with no
  business logic. They are made testable by injecting mocks at the call site;
  the wrappers themselves do not have unit test files.
