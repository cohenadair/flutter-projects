---
name: flutter-test
description: >
  Patterns and worked examples for writing Flutter unit tests and widget
  tests in this monorepo (pro-iq, anglers-log, activity-log, tapd,
  adair-flutter-lib). The test rules themselves are in `flutter-conventions`
  (`tests.md`); load both.
  Use this skill whenever writing, reviewing, or scaffolding any Flutter test —
  including unit tests for business logic, widget tests for UI components, or
  tests for manager/singleton classes. Trigger on requests like "write tests
  for", "add a unit test", "add a widget test", "test this widget", "test this
  class", or any time a .dart test file is being created or modified.
---

# Flutter Test Skill

The rules (no `group()`, one test per branch, `pumpContext`, description
casing, helper placement, …) are in `flutter-conventions` →
[tests.md](../flutter-conventions/tests.md). This skill adds patterns and
examples. When an example here and a rule there disagree, the rule wins:
fix the example.

## Singleton / Manager pattern

All managers follow the pattern in
`adair-flutter-lib/lib/managers/manager.dart` (extends `Manager`) and
`adair-flutter-lib/lib/managers/properties_manager.dart`:

```dart
class MyManager extends Manager {
  static var _instance = MyManager._();
  static MyManager get get => _instance;

  @visibleForTesting
  static void set(MyManager manager) => _instance = manager;

  @visibleForTesting
  static void reset() => _instance = MyManager._();

  MyManager._();

  @override
  Future<void> init() async { ... }
}
```

Tests never construct real managers. They inject mocks via the `set()` method,
which `StubbedManagers` handles automatically.

---

## StubbedManagers

All singleton stubbing goes through `StubbedManagers`. The class hierarchy is:

```
adair-flutter-lib StubbedManagers   ← base; mocks lib managers/wrappers
        ↑
project StubbedManagers             ← wraps lib via `lib` field; adds
                                       project-specific managers
```

**Reference files:**
- Base: `adair-flutter-lib/test/test_utils/stubbed_managers.dart`
- Simple project example: `pro-iq/test/stubbed_managers.dart`
- Complex project example: `anglers-log/mobile/test/mocks/stubbed_managers.dart`

### Minimal project StubbedManagers shape (pro-iq style)

```dart
class StubbedManagers {
  late final s.StubbedManagers lib;   // adair-flutter-lib's StubbedManagers
  late final MockMyManager myManager;

  static Future<StubbedManagers> create() async =>
      StubbedManagers._(await s.StubbedManagers.create());

  StubbedManagers._(this.lib) {
    myManager = MockMyManager();
    MyManager.set(myManager);
    // project-specific localization setup if needed
  }
}
```

### How to use in tests

```dart
late StubbedManagers managers;

setUp(() async {
  managers = await StubbedManagers.create();
  // configure stubs specific to this test file
  when(managers.myManager.someProperty).thenReturn(someValue);
});
```

Access lib-level mocks through `managers.lib`:

```dart
when(managers.lib.subscriptionManager.isFree).thenReturn(true);
when(managers.lib.timeManager.currentDateTime).thenReturn(DateTime(2024));
```

---

## Unit tests

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';

void main() {
  late StubbedManagers managers;

  setUp(() async {
    managers = await StubbedManagers.create();
  });

  test("Returns cached value when cache is valid", () {
    when(managers.myManager.isCacheValid).thenReturn(true);
    when(managers.myManager.cachedValue).thenReturn(42);
    expect(MyClass().compute(), 42);
  });

  test("Recomputes when cache is invalid", () {
    when(managers.myManager.isCacheValid).thenReturn(false);
    expect(MyClass().compute(), isNot(42));
  });
}
```

- Use `verify()` / `verifyNever()` to assert that methods were (or were not)
  called when behavior, not just return value, is the thing under test.

---

## Widget tests

Widget tests always use `pumpContext` from
`adair-flutter-lib/test/test_utils/testable.dart`. This wraps the widget in a
`Testable` (which provides a Material app, theme, and localizations) and
returns the live `BuildContext`.

**Signature:**

```dart
Future<BuildContext> pumpContext(
  WidgetTester tester,
  Widget Function(BuildContext) builder, {
  MediaQueryData mediaQueryData = const MediaQueryData(),
  ThemeData? theme,
  ThemeMode? themeMode,
  Locale? locale,
  bool useMaterial3 = false,
  List<LocalizationsDelegate> localizations = const [],
}) async { ... }
```

### Typical widget test

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';

// Import pumpContext from adair-flutter-lib's testable library
// (exact import path depends on the project)

void main() {
  late StubbedManagers managers;

  setUp(() async {
    managers = await StubbedManagers.create();
  });

  testWidgets("Shows label when value is non-null", (tester) async {
    await pumpContext(tester, (_) => MyWidget(value: "hello"));
    expect(find.text("hello"), findsOneWidget);
  });

  testWidgets("Shows placeholder when value is null", (tester) async {
    await pumpContext(tester, (_) => MyWidget(value: null));
    expect(find.text("—"), findsOneWidget);
  });
}
```

### Accessing BuildContext

```dart
testWidgets("Uses theme color", (tester) async {
  final context = await pumpContext(tester, (ctx) => MyWidget());
  expect(Theme.of(context).colorScheme.primary, isNotNull);
});
```

### Pumping after interaction

Use the `*AndSettle` helpers from `adair-flutter-lib/test/test_utils/widget.dart`
(`tapAndSettle`, `enterTextAndSettle`, `ensureVisibleAndSettle`), or
`tester.pumpAndSettle()` after stream events:

```dart
testWidgets("Tapping button triggers callback", (tester) async {
  var tapped = false;
  await pumpContext(tester, (_) => MyButton(onTap: () => tapped = true));
  await tapAndSettle(tester, find.byType(MyButton));
  expect(tapped, isTrue);
});
```

---

## Code-path analysis checklist

Before writing tests for a class or function, read through the implementation
and note:

1. **All branches** — `if/else`, `switch`, early returns, `assert`.
2. **Ternary operators** — both the true and false cases need separate tests.
3. **Null checks** — `??`, `?.`, `!` (verify the non-null path and the null
   fallback).
4. **Async paths** — success, failure, and empty stream/future cases.
5. **Impossible paths** — if a branch can never execute given the class
   invariants or type system, call it out explicitly before listing the tests.
   Example: "The `else` branch on line 42 is unreachable because `_items` is
   initialized in the constructor and never set to null."

---

## Mockito quick reference

```dart
// Stub return value
when(mock.method()).thenReturn(value);
when(mock.asyncMethod()).thenAnswer((_) async => value);

// Stub a stream
when(mock.stream).thenAnswer((_) => Stream.value(event));
when(mock.stream).thenAnswer((_) => const Stream.empty());

// Verify called
verify(mock.method()).called(1);
verifyNever(mock.method());

// Capture arguments
final captured = verify(mock.method(captureAny)).captured;

// Named arguments
when(mock.method(any, named: anyNamed("named"))).thenReturn(value);
```
