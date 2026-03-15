---
name: flutter-test-skill
description: >
  Guidelines and patterns for writing Flutter unit tests and widget tests in
  the pro-iq monorepo and related projects (adair-flutter-lib, anglers-log).
  Use this skill whenever writing, reviewing, or scaffolding any Flutter test —
  including unit tests for business logic, widget tests for UI components, or
  tests for manager/singleton classes. Trigger on requests like "write tests
  for", "add a unit test", "add a widget test", "test this widget", "test this
  class", or any time a .dart test file is being created or modified.
---

# Flutter Test Skill

## Core rules (always apply)

- **No test groups.** Never use `group()`. Use a flat list of `test()` /
  `testWidgets()` calls inside `void main()`.
- **Full code-path coverage.** Every branch must be exercised — including both
  sides of every `if`, `else`, `??`, `? :`, and `switch` case. Write a
  separate test for each branch; don't combine them.
- **Identify impossible code paths.** While reading the code under test, flag
  any branch that can never be reached and explain why. Do this before writing
  the tests.

---

## Singleton / Manager pattern

All managers follow the pattern in
`adair-flutter-lib/lib/managers/manager.dart` (implements `Manager`) and
`adair-flutter-lib/lib/managers/properties_manager.dart`:

```dart
class MyManager implements Manager {
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

  test('returns cached value when cache is valid', () {
    when(managers.myManager.isCacheValid).thenReturn(true);
    when(managers.myManager.cachedValue).thenReturn(42);
    expect(MyClass().compute(), 42);
  });

  test('recomputes when cache is invalid', () {
    when(managers.myManager.isCacheValid).thenReturn(false);
    expect(MyClass().compute(), isNot(42));
  });
}
```

- One `test()` per logical branch (including each side of a ternary).
- Use `verify()` / `verifyNever()` to assert that methods were (or were not)
  called when behavior, not just return value, is the thing under test.
- Prefer `thenReturn` for synchronous values, `thenAnswer((_) async => ...)`
  for futures/streams.

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

  testWidgets('shows label when value is non-null', (tester) async {
    await pumpContext(tester, (_) => MyWidget(value: 'hello'));
    expect(find.text('hello'), findsOneWidget);
  });

  testWidgets('shows placeholder when value is null', (tester) async {
    await pumpContext(tester, (_) => MyWidget(value: null));
    expect(find.text('—'), findsOneWidget);
  });
}
```

### Accessing BuildContext

```dart
testWidgets('uses theme color', (tester) async {
  final context = await pumpContext(tester, (ctx) => MyWidget());
  expect(Theme.of(context).colorScheme.primary, isNotNull);
});
```

### Pumping after interaction

Use `tester.pumpAndSettle()` after tap/scroll/stream events:

```dart
testWidgets('tapping button triggers callback', (tester) async {
  var tapped = false;
  await pumpContext(tester, (_) => MyButton(onTap: () => tapped = true));
  await tester.tap(find.byType(MyButton));
  await tester.pumpAndSettle();
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
when(mock.method(any, named: anyNamed('named'))).thenReturn(value);
```
