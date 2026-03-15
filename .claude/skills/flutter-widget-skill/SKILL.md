---
name: flutter-widget-skill
description: >
  Coding conventions and patterns for building Flutter widgets in the pro-iq monorepo
  (and its shared lib, adair-flutter-lib). Use this skill whenever creating, refactoring,
  or reviewing any Flutter widget, page, or UI component — including StatelessWidgets,
  StatefulWidgets, reusable widgets in lib/widgets/, and page files in lib/pages/.
  Trigger on any Flutter UI request: new widgets, layout changes, theming, avatar/card
  components, or questions about where to put a new widget.
---

# Flutter Widget Skill

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

## Coding preferences

### 1. Padding & spacing — use `inset*` constants

Always import from `adair_flutter_lib/res/dimen.dart` and use the named constants.
Default to `insetsDefault` when no specific size is needed.

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

### 2. No magic numbers — declare constants at the top of the class

Elevation, radii, font sizes, fixed spacing that isn't from dimen.dart — all go as
`static const` fields at the top of the widget class.

```dart
class _ProfileCard extends StatelessWidget {
  static const _elevation = 4.0;
  static const _coachTopSpacing = 1.0;
  // ...
}
```

### 3. Curly braces — always use them for `if` statement bodies

Every `if` body must use curly braces, even for single-line returns.

```dart
// Prefer:
if (isColorReadable(primary, background)) {
  return primary;
}

// Never:
if (isColorReadable(primary, background)) return primary;
```

### 4. Strings use double quotes

Always use double quotes for Dart string literals.

```dart
// Prefer:
Text("Coach: ")
const Avatar(initials: "MR")

// Never:
Text('Coach: ')
const Avatar(initials: 'MR')
```

### 4. Keep `build()` short — extract to small `_build*` methods

Avoid long `build()` methods. Each meaningful piece of UI should be extracted to its
own `_build*` method. A good rule of thumb: if a widget has a `Column` or `Row`,
each child should be a `_build*` call rather than an inline widget tree.

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

### 5. Conditional widgets — invert and return early

When a widget should only appear under a condition, invert the condition and return
`const SizedBox()` early. Avoid inline `if` spreads in widget lists.

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

### 6. Page widgets — use `ScrollPage` as the root

All new page widgets (files in `lib/pages/`, named `*_page.dart`) should use
`ScrollPage` from `adair_flutter_lib` as their root widget instead of `Scaffold`.

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

### 7. Future-based widgets — use `SafeFutureBuilder`

Whenever a widget's content is driven by a `Future`, use `SafeFutureBuilder`
instead of the standard `FutureBuilder`. It handles loading/error states and
logs errors automatically.

```dart
import 'package:adair_flutter_lib/widgets/safe_future_builder.dart';

SafeFutureBuilder(
  future: DataManager.get.currentUser(),
  errorReason: "Loading current user",   // required — describes the future's purpose
  builder: (context, user) {
    if (user == null) return const SizedBox();
    return _ProfileCard(user: user);
  },
  loadingBuilder: (_) => const CircularProgressIndicator(),  // optional
  errorBuilder: (_) => const Text("Failed to load"),         // optional
)
```

- `errorReason` is **required** — use a short human-readable description
- Falls back to an empty `SizedBox()` when `loadingBuilder`/`errorBuilder` are omitted
- `isErrorFatal: true` can be set to mark the error as fatal in Firebase

---

## Existing reusable widgets

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
