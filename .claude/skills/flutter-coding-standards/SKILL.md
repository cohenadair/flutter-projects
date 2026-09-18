---
name: flutter-coding-standards
description: >
  Coding conventions, patterns, and reuse checks for Flutter code in the pro-iq monorepo
  (and its shared lib, adair-flutter-lib). Use this skill whenever creating, refactoring,
  or reviewing any Flutter widget, page, manager, or utility — including StatelessWidget
  and StatefulWidget subclasses in lib/widgets/ and lib/pages/, and non-widget logic in
  lib/managers/, lib/utils/, and lib/wrappers/. Trigger on any Flutter implementation
  request: new widgets, layout changes, theming, new manager/utility methods, or
  questions about where to put new code or whether something reusable already exists.
---

# Flutter Coding Standards Skill

## Project layout

```
pro-iq/lib/
  pages/        # Full-screen pages (one widget per file, named *_page.dart)
  widgets/      # Reusable widgets shared across pages
  models/gen/protobuf/   # Protobuf-generated data classes (canonical, up-to-date)
  managers/     # Data access layer (DataManager, etc.)
  res/          # App-specific resources
adair-flutter-lib/lib/
  res/dimen.dart   # Padding, spacing, and size constants — always import from here
  res/style.dart   # Font weight constants and text style helpers
  res/theme.dart   # Theme extension helpers (colorApp, colorOnApp, etc.)
  widgets/         # Shared cross-app widgets
```

**Canonical protobuf import path:**
```dart
import 'package:pro_iq/models/gen/protobuf/pro_iq.pb.dart';
```
The `models/gen/` (non-`protobuf/`) files are stale — always use the `protobuf/` subdirectory.

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
- Check the **Existing reusable code** reference below — it's a non-exhaustive sample
  of the most commonly reused pieces, not a substitute for actually searching.

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

### Curly braces / double quotes

```dart
// Prefer:
if (isColorReadable(primary, background)) {
  return primary;
}
Text("Coach: ")
const Avatar(initials: "MR")

// Never:
if (isColorReadable(primary, background)) return primary;
Text('Coach: ')
const Avatar(initials: 'MR')
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

The primary `build()` method is always the **first** method in the class body.
All `_build*` helpers are placed *after* it.

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
| `centerContent` | Center children horizontally |
| `restrictWidth` | Cap content width for wide screens |

### AsyncBuilder

```dart
import 'package:adair_flutter_lib/widgets/async_builder.dart';

AsyncBuilder.future(
  future: DataManager.get.currentUser(),
  errorReason: "Loading current user",   // required — describes the future's purpose
  builder: (context, user) {
    if (user == null) return const SizedBox();
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

Non-exhaustive — a quick-reference sample of pieces that come up often. Always
search the codebase (see "Check for reusable code before writing new code" above)
rather than assuming this list is complete.

### `Avatar` — `lib/widgets/avatar.dart`

Circular avatar using `CircleAvatar`. Shows a network photo when available;
falls back to the user's initials if the URL is null, empty, or fails to load.
Background color is derived deterministically from the initials string.

```dart
Avatar(
  initials: "MR",          // required — typically first[0]+last[0] uppercased
  photoUrl: user.photoUrl.isEmpty ? null : user.photoUrl,  // optional
  radius: 36,               // optional, default 36
)
```

Derive initials from a `User` proto like this:
```dart
String get _initials => [
  if (user.first.isNotEmpty) user.first[0],
  if (user.last.isNotEmpty) user.last[0],
].join().toUpperCase();
```

### `_ProfileCard` — `lib/pages/mobile_home_page.dart` (private, in-page)

M3 elevated card displaying a `User`'s avatar, name, team, and coach.
Coach row is omitted when `user.coachName` is empty.

```dart
_ProfileCard(user: someUser)
```

### `formatBytes` — `adair_flutter_lib/utils/string.dart`

Formats a byte count into a human-readable string (e.g. `"110.5 MB"`). Use this
instead of writing a new byte-formatting helper.

```dart
formatBytes(fileSizeInBytes)
```

---

## Theming

The app uses `ThemeMode.dark` with a teal seed color. Always use theme-aware
values — never hardcode light-theme colors like `#1C1B1F` or `#F6F2FA`.

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

---

## Protobuf `User` fields

```
string first       // given name
string last        // family name
string email
repeated string roles
string team        // e.g. "Chicago Bulls"
string photo_url   // network image URL, may be empty string
string coach_name  // e.g. "Coach Derrick Owens", may be empty string
```

Proto strings default to `""` (not null) when unset — guard with `.isEmpty`
rather than null checks.
