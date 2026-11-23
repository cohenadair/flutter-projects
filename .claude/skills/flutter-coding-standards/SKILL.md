---
name: flutter-coding-standards
description: >
  Worked examples, reusable-code checks, and project layout for Flutter code
  in this monorepo (pro-iq, anglers-log, activity-log, tapd, and the shared
  adair-flutter-lib). Use whenever creating, refactoring, or reviewing a
  widget, page, manager, wrapper, or utility, or deciding where new code
  goes or whether something reusable already exists. The rules themselves
  are in `flutter-conventions`; load both.
---

# Flutter Coding Standards Skill

The rules live in the `flutter-conventions` skill. This skill adds worked
examples, the check for reusable code, and where things live. When an
example here and a rule there disagree, the rule wins: fix the example.

## Project layout

Each app's Flutter root and its main `lib/` folders:

| App | Flutter root | Notable `lib/` folders |
|---|---|---|
| pro-iq | `pro-iq/` | `managers/`, `wrappers/`, `riverpod/`, `models/gen/protobuf/` |
| anglers-log | `anglers-log/mobile/` | `database/`, `map/`, `channels/`, `model/`, `wrappers/` |
| activity-log | `activity-log/mobile/` | `database/`, `model/`, `i18n/`, `wrappers/` |
| tapd | `tapd/mobile/` | `components/`, `effects/`, `overlays/`, `managers/`, `wrappers/` |
| adair-flutter-lib | `adair-flutter-lib/` | shared `managers/`, `wrappers/`, `widgets/`, `pages/`, `utils/` |

Every app also has `pages/` (one page per `*_page.dart`), `widgets/`,
`utils/`, and `l10n/`. Shared resources come from adair-flutter-lib:

- `res/dimen.dart`: padding, spacing, and size constants
- `res/style.dart`: font weight constants and text style helpers
- `res/theme.dart`: theme extension helpers (`colorApp`, `colorError`, …)

---

## Check for reusable code before writing new code

Before implementing a new widget, manager method, or utility function, search for
existing code that already does — or could be adapted to do — what you need. Writing
a new class/method when an equivalent (or near-equivalent) one exists is a duplication
bug, not a style nit.

**Widgets** — nearly all custom widgets in this codebase extend `StatelessWidget` or
`StatefulWidget` (with its paired `State<T>` subclass). Before writing a new one:
- Grep for the class declarations, not just filenames — a matching widget may be
  private and defined inside a page file rather than living in `lib/widgets/`:
  ```
  grep -rn "extends StatelessWidget\|extends StatefulWidget" lib/widgets/ lib/pages/
  ```
- Skim `lib/widgets/` (and `adair-flutter-lib/lib/widgets/` for cross-app widgets) for
  anything visually or structurally similar to what you're about to build.
- Check the **Existing reusable code** reference below. It's a non-exhaustive sample
  of commonly reused pieces, not a substitute for actually searching.

**Non-widget logic** (managers, utils, wrappers) — search `lib/managers/`,
`adair-flutter-lib/lib/managers/`, `lib/utils/`, and `adair-flutter-lib/lib/utils/` for
a method that already covers the behavior, e.g.:
```
grep -rn "formatBytes\|isColorReadable\|<keyword for what you need>" lib/utils/ adair-flutter-lib/lib/utils/
```

If you find something close but not exact, **prefer extending or parameterizing it**
(adding an optional parameter, extracting a shared base) over copy-pasting and
modifying — copy-pasted variants are exactly what `adair-code-audit`'s duplication
check (Agent 3) will later flag as tech debt. If nothing reusable exists, say so
explicitly before writing the new code, so the user can confirm you didn't miss it.

---

## Examples

### Padding & spacing

```dart
import 'package:adair_flutter_lib/res/dimen.dart';

// Prefer:
Padding(padding: insetsDefault, ...)
SizedBox(width: paddingDefault)

// Never:
Padding(padding: EdgeInsets.all(16), ...)
SizedBox(width: 16)
```

Key constants:
| Constant | Value |
|---|---|
| `paddingTiny` | 4 |
| `paddingSmall` | 8 |
| `paddingMedium` | 12 |
| `paddingDefault` | 16 |
| `paddingLarge` | 24 |
| `paddingXL` | 32 |
| `insetsDefault` | `EdgeInsets.all(16)` |
| `insetsSmall` | `EdgeInsets.all(8)` |
| `insetsHorizontalDefault` | left+right 16 |
| `insetsVerticalDefault` | top+bottom 16 |
| *(and many directional variants)* | |

For values not covered by dimen.dart (e.g. a 1px hairline gap), declare a named
`static const` at the top of the class rather than inlining the literal.

### No magic numbers

```dart
class _ProfileCard extends StatelessWidget {
  static const _elevation = 4.0;
  static const _coachTopSpacing = 1.0;
  // ...
}
```

### No `@visibleForTesting` fields to shorten waits

The rule is in `flutter-conventions` → Constants & helper functions.

```dart
// Bad — production field exists only for tests:
static const _defaultAuthenticateTimeout = Duration(minutes: 1);
@visibleForTesting
Duration authenticateTimeout = _defaultAuthenticateTimeout;

// Good:
static const _authenticateTimeout = Duration(minutes: 1);

// Test:
FakeAsync().run((async) {
  manager.signIn();
  async.elapse(const Duration(minutes: 1));
});
```

### Curly braces / double quotes

```dart
// Prefer:
if (isColorReadable(primary, background)) {
  return primary;
}
Text("Coach: ")
const Text("MR")

// Never:
if (isColorReadable(primary, background)) return primary;
Text('Coach: ')
const Text('MR')
```

### build() structure

```dart
// Prefer:
Column(
  children: [
    _buildName(context),
    _buildTeam(context),
    _buildCoach(context),
  ],
)

// Avoid:
Column(
  children: [
    Text(user.name, style: ...),
    Text(user.team, style: ...),
    Text(user.coach, style: ...),
  ],
)
```

`build()` comes after the lifecycle methods (`initState`, `dispose`, …) and
before every other method. All `_build*` helpers are placed *after* it.

### `BuildContext` in helper functions

Only pass `BuildContext` as a parameter to a `_build*` helper when the helper is on a
`StatelessWidget` (which has no `context` field) or when it genuinely needs a *different*
context than the one available on `this`. In a `State` subclass, `context` is already
accessible as a field — pass it only if the helper is `static` or defined outside the class.

```dart
// StatefulWidget — context is a field; no need to pass it
class _MyPageState extends State<MyPage> {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildTitle(),   // no context param needed
        _buildBody(),
      ],
    );
  }

  Widget _buildTitle() => Text("Hello", style: Theme.of(context).textTheme.titleLarge);
  Widget _buildBody() => Padding(padding: insetsDefault, child: Text(_data));
}

// StatelessWidget — must pass context because there is no field
class MyCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildTitle(context),   // context param required here
      ],
    );
  }

  Widget _buildTitle(BuildContext context) =>
      Text("Hello", style: Theme.of(context).textTheme.titleLarge);
}
```

### Conditional widgets

```dart
// Prefer:
Widget _buildCoach(BuildContext context) {
  if (user.coachName.isEmpty) {
    return const SizedBox();
  }

  return Text(user.coachName, ...);
}

// Avoid:
if (user.coachName.isNotEmpty) ...[
  Text(user.coachName, ...),
],
```

### ScrollPage

```dart
import 'package:adair_flutter_lib/pages/scroll_page.dart';

class MyPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ScrollPage(
      appBar: AppBar(title: const Text("My Page")),
      padding: insetsDefault,
      children: [
        _buildContent(context),
      ],
    );
  }
}
```

Key parameters:
| Parameter | Purpose |
|---|---|
| `appBar` | Optional `AppBar` |
| `children` | Main scrollable content |
| `footer` | Persistent bottom buttons (non-scrolling) |
| `padding` | Padding around children (use `insets*` constants) |
| `spacing` | Gap between each child (use `padding*` constants) |
| `onRefresh` | Pull-to-refresh callback |
| `centersContent` | Center children horizontally |
| `restrictsWidth` | Cap content width for wide screens |

### AsyncBuilder

```dart
import 'package:adair_flutter_lib/widgets/async_builder.dart';

AsyncBuilder.future(
  future: DataManager.get.currentUser(),
  errorReason: "Loading current user",   // required — describes the future's purpose
  builder: (context, user) {
    if (user == null) {
      return const SizedBox();
    }
    return _ProfileCard(user: user);
  },
  loadingBuilder: (_) => const CircularProgressIndicator(),  // optional
  errorBuilder: (_) => const Text("Failed to load"),         // optional
)

// For streams:
AsyncBuilder.stream(
  stream: DataManager.get.usersStream(),
  errorReason: "Loading users",
  builder: (context, users) => UserList(users: users),
)
```

- `errorReason` is **required** — use a short human-readable description
- Falls back to an empty `SizedBox()` when `loadingBuilder`/`errorBuilder` are omitted
- `isErrorFatal: true` can be set to mark the error as fatal in Firebase

---

## Existing reusable code

Non-exhaustive: a quick-reference sample of pieces that come up often. Always
search the codebase (see "Check for reusable code before writing new code" above)
rather than assuming this list is complete. If an entry here has moved or
been renamed, fix it.

### `ProfilePicture` — `pro-iq/lib/widgets/profile_picture.dart`

Circular profile picture for a `User`. Shows the network photo at
`user.profilePicturePath` when there is one; falls back to the user's
initials if there isn't, or if loading fails.

```dart
ProfilePicture(user: user)            // default 72pt
ProfilePicture(user: user, size: 40)  // optional size
```

### `_ProfileCard` — `pro-iq/lib/pages/player_home_page.dart` (private, in-page)

Card on the player home page showing a `User`'s picture and details.

### `formatBytes` — `adair_flutter_lib/utils/string.dart`

Formats a byte count into a human-readable string (e.g. `"110.5 MB"`). Use this
instead of writing a new byte-formatting helper.

```dart
formatBytes(fileSizeInBytes)
```

---

## Theming

Always use theme-aware values, never hardcoded colors. Theme mode and seed
color vary per app (pro-iq: per tenant, via `TenantConfig.get.themeMode`
and `TenantConfig.get.seedColor`), so code must look right in both light
and dark.

```dart
// Colors
Theme.of(context).colorScheme.primary
Theme.of(context).colorScheme.onSurface
Theme.of(context).colorScheme.outline
Theme.of(context).colorScheme.secondaryContainer

// Text styles
Theme.of(context).textTheme.titleLarge
Theme.of(context).textTheme.labelMedium
Theme.of(context).textTheme.bodySmall
```

For proto fields (pro-iq's `User` and others), read the `.proto` source:
`pro-iq/protobuf/pro_iq.proto`. Don't copy field lists into this skill.
