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

## Pages & async

- Page widgets (`lib/pages/*_page.dart`) must use **`ScrollPage`** from
  `adair_flutter_lib` as their root — not `Scaffold`.
- For async content use **`SafeFutureBuilder`** in place of both `FutureBuilder`
  and `StreamBuilder`. The `errorReason` parameter is required.

## Localizations

- Never modify `*_localizations*.dart` files directly — they are generated.
- After editing any `.arb` file, regenerate with `flutter gen-l10n` from the project root.

## Protos

- Canonical import: `package:pro_iq/models/gen/protobuf/pro_iq.pb.dart`
  The `models/gen/` (non-`protobuf/`) path is stale — never use it.
- Proto strings default to `""` when unset, not null. Guard with `.isEmpty`,
  not null checks.

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
- **Test helper functions** — declare as local functions inside `main()`, immediately
  after `setUp`/`tearDown`. Name them with a plain lowercase identifier (no leading
  underscore). See `colorCircle` and `openTeamDropdown` in
  `pro-iq/test/pages/all_users_page_test.dart` as the reference example.
- **`*AndSettle` helpers** — use `tapAndSettle`, `ensureVisibleAndSettle`, and
  `enterTextAndSettle` (from `adair-flutter-lib/test/test_utils/widget.dart`)
  instead of the raw `tester.*()` + `tester.pumpAndSettle()` two-liner.
