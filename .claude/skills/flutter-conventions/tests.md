# Test conventions

Part of the `flutter-conventions` skill ([SKILL.md](SKILL.md)). Patterns
and examples (StubbedManagers shapes, mockito reference) are in the
`flutter-test` skill.

## Rules

- **No `group()`** — use a flat list of `test()` / `testWidgets()` calls inside
  `void main()`.
- **One test per branch** — every `if/else`, `??`, ternary, and `switch` case gets
  its own `test()`. Do not combine branches in a single test.
- Before writing tests, read the implementation and call out any branch that can
  never be reached, explaining why.
- **Never construct real managers in tests.** Always inject mocks via
  `StubbedManagers`. Access lib-level mocks through `managers.lib.*`.
- **Never modify `mocks.mocks.dart`** — it is generated. To regenerate, run
  `./gen_mocks.sh` from the Flutter root (e.g. `pro-iq/`, `tapd/mobile/`).
  Each project's `build.yaml` limits mockito's builder to
  `test/mocks/mocks.dart`; keep it, or build_runner 2.16+ fails with
  "Cannot recurse at later or equal phase".
- Widget tests always use **`pumpContext`** (from
  `adair-flutter-lib/test/test_utils/testable.dart`) — never
  `tester.pumpWidget(Testable(...))`. `pumpContext` wraps `Testable` internally;
  `tester.pumpAndSettle()` is still called separately after the pump:
  ```dart
  // Bad:
  await tester.pumpWidget(Testable((_) => MyWidget()));
  await tester.pumpAndSettle();

  // Good:
  await pumpContext(tester, (_) => MyWidget());
  await tester.pumpAndSettle();
  ```
- Use `tester.pumpAndSettle()` after tap / scroll / stream events.
- Stub sync values with `thenReturn`; stub futures/streams with
  `thenAnswer((_) async => ...)` / `thenAnswer((_) => Stream.value(...))`.
- **Test description casing** — descriptions must start with a capital letter, unless
  the first word is a method or function name being exercised (e.g. `"capitalize returns
  empty string when input is empty"` is fine; `"widget renders without errors"` is not).
- **Test names/descriptions must never be split across lines.** Keep the
  `test()`/`testWidgets()` description as a single string literal, as concise
  as possible. If it exceeds the 80-character line limit, that's fine — do not
  wrap it with string concatenation (`"foo " "bar"`) or a multi-line literal:
  ```dart
  // Bad:
  test(
    "Activity panel still shows the selected player after they're removed "
    "from the live players map",
    () async { ... },
  );

  // Good:
  test(
    "Activity panel still shows the selected player after removal",
    () async { ... },
  );
  ```
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
- **Widget callback parameters** — when a widget's functional parameters (e.g.
  `DropTarget.onDragDone`) cannot be triggered via `tester.tap` or similar gestures,
  find the widget in the tree and invoke the callback directly:
  ```dart
  final dropTarget = tester.widget<DropTarget>(find.byType(DropTarget).first);
  dropTarget.onDragDone!(DropDoneDetails(...));
  await tester.pumpAndSettle();
  ```
- **Mock generation** — when a class used in production code has no mock yet (e.g.
  `UploadTask`), add it to the appropriate `mocks.dart` file under
  `@GenerateMocks([...])` and regenerate with `gen_mocks.sh` (pro-iq) or
  `dart run build_runner build` (adair-flutter-lib). Never write mock classes by hand.
