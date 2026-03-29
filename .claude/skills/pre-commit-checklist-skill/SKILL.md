---
name: pre-commit-checklist-skill
description: >
  A step-by-step checklist for preparing uncommitted Flutter changes for
  commit and pull request. Use when the user says things like "prepare our
  changes for a pull request", "run through the git pre-commit checklist",
  "pre-commit checklist", or "get the code ready to commit".
---

# Pre-Commit Checklist Skill

Follow every step below in order. Mark each item complete before moving on.

---

## Step 0 — Identify affected submodules

From the **repo root** (`/Users/cohen/Documents/flutter`), run:

```bash
git submodule foreach git diff --stat HEAD
```

Only perform the checklist steps below for submodules that have uncommitted
changes. The Flutter project root for each submodule is the submodule directory
itself (e.g. `pro-iq/`, `adair-flutter-lib/`).

---

## Step 1 — Write / update tests

For each affected Flutter submodule, read every changed `.dart` file under
`lib/` and write or update tests to achieve as close to **100% branch
coverage** as possible.

See [CLAUDE.md](../../.claude/CLAUDE.md) for full testing conventions (no
`group()`, one test per branch, `StubbedManagers`, `pumpContext`, stub
patterns, etc.) and Dart/Flutter style rules.

### File placement

Test files mirror the `lib/` tree under `test/`:
- `lib/pages/foo_page.dart` → `test/pages/foo_page_test.dart`
- `lib/widgets/bar.dart` → `test/widgets/bar_test.dart`
- `lib/managers/baz_manager.dart` → `test/managers/baz_manager_test.dart`
- `lib/utils/string.dart` → `test/utils/string_test.dart`

### Key context from the Adding Players feature

The following areas were touched and need corresponding test coverage:

**adair-flutter-lib**
- `lib/utils/string.dart` — `StringExt.capitalize` getter. Test: empty string
  returns empty; single char returns uppercased; mixed-case string capitalizes
  only first letter; already-uppercase string is unchanged.
- `lib/widgets/text_input_autocomplete.dart` — `TextInputAutocomplete<T>`.
  Widget tests: dropdown appears with options, selecting an option fires
  `onSelected`, editing the field after selection fires `onSelected(null)`,
  `itemBuilder` is used when provided vs. default `Text` label.

**pro-iq**
- `lib/managers/data_manager.dart`:
  - `allUsersStream` now returns `Stream<Map<String, User>>`.
  - `addUser(User)` — new method; test that it calls Firestore `add` with the
    correct proto JSON.
  - `userStream(String userId)` — test empty userId returns `Stream.value(null)`;
    non-empty userId maps Firestore snapshot to a `User`.
- `lib/pages/all_users_page.dart` — `_AddUserDialog`:
  - Form validation: Save is disabled until all required fields are filled
    (first, last, email valid, at least one role).
  - Roles: each checkbox toggles its respective bool independently.
  - `_save()` capitalizes first and last, assembles roles list, calls
    `DataManager.get.addUser`.
- `lib/widgets/user_table.dart` — now receives `Map<String, User> users` and
  `Map<String, Team> teams` directly; coach name is resolved via
  `_coachName(user.coachId)`.
- `lib/pages/mobile_home_page.dart` — `_buildCoach` uses `coachId` and
  `DataManager.get.userStream(user.coachId)`.

---

## Step 2 — Review for duplication and reuse

For each changed `lib/` file and its corresponding test file, look for:

- **Duplicated logic** — the same expression, string interpolation, or algorithm
  appearing more than once in the same file or across nearby files. Extract to a
  shared method, getter, or extension.
- **Missed utilities** — logic that already exists in `adair_flutter_lib` or
  elsewhere in the project (string helpers, spacing constants, widget builders).
  Prefer reusing these over writing new code.
- **Test boilerplate duplication** — repeated `setUp`-style stub blocks, proto
  initialisation, or pump sequences in test files. Move repeated stubs to `setUp`;
  extract shared pump/interaction sequences to local helper functions declared
  inside `main()` immediately after `setUp`/`tearDown`, named with a plain
  lowercase identifier (no leading underscore).
- **Inconsistent patterns** — e.g. mixing `pumpWidget(Testable(...))` and
  `pumpContext` in the same test file. Standardise on `pumpContext` as required
  by CLAUDE.md.

Fix any issues found before moving on.

---

## Step 3 — Identify dead / unreachable code

For each changed file, read the implementation and reason through every branch:
- Is there a guard that makes a later branch unreachable?
- Are there `else` arms that can never trigger given the surrounding logic?
- Are there null checks on values that are already asserted non-null?

Document findings inline as comments or report them to the user before
committing. Do **not** silently delete unreachable code without flagging it.

---

## Step 4 — Format

For each affected Flutter submodule, run from its project root:

```bash
dart format lib test
```

Example:
```bash
cd /Users/cohen/Documents/flutter/pro-iq && dart format lib test
cd /Users/cohen/Documents/flutter/adair-flutter-lib && dart format lib test
```

---

## Step 5 — Run tests

For each affected Flutter submodule, run from its project root:

```bash
flutter test
```

All tests must pass. If any fail, investigate and fix before proceeding.

---

## Step 6 — Check ARB translation coverage

Skip this step if no `.arb` files were changed in the affected submodules.

For each affected submodule that has `.arb` changes, compare the keys in the base
English file against each locale file that requires full translation coverage. Use
`jq` to diff non-metadata (non-`@`-prefixed) keys:

```bash
# adair-flutter-lib — check Spanish
diff \
  <(jq -r 'keys[] | select(startswith("@") | not)' adair-flutter-lib/lib/l10n/adair_flutter_lib_en.arb | sort) \
  <(jq -r 'keys[] | select(startswith("@") | not)' adair-flutter-lib/lib/l10n/adair_flutter_lib_es.arb | sort)

# anglers-log — check Spanish
diff \
  <(jq -r 'keys[] | select(startswith("@") | not)' anglers-log/mobile/lib/l10n/localizations_en.arb | sort) \
  <(jq -r 'keys[] | select(startswith("@") | not)' anglers-log/mobile/lib/l10n/localizations_es.arb | sort)
```

**Locale rules — which files need full coverage:**

| Project | Base | Requires full coverage | Skip (spelling variants only) |
|---------|------|------------------------|-------------------------------|
| `adair-flutter-lib` | `adair_flutter_lib_en.arb` | `adair_flutter_lib_es.arb` | `adair_flutter_lib_en_US.arb` |
| `anglers-log/mobile` | `localizations_en.arb` (Canadian English) | `localizations_es.arb` | `localizations_en_US.arb`, `localizations_en_GB.arb` |
| `pro-iq` | `pro_iq_en.arb` | *(no other locales)* | — |

`_en_US.arb` holds US-spelling overrides (e.g. "canceled") and `_en_GB.arb` holds
British-spelling overrides — neither needs every key.

**If missing keys are found:** translate them directly. Use the English value,
surrounding strings in the file, and the app domain to infer the correct translation.
Do not use placeholder text. Add the translated entry to the locale file in the same
position as it appears in the base English file, preserving the existing formatting.

---

## Reminders — generated files & regeneration scripts

See [CLAUDE.md](../../.claude/CLAUDE.md) for style and coding rules. Never
edit these files by hand; they are always regenerated:

| File | Regenerate with | From |
|------|----------------|------|
| `pro-iq/test/mocks/mocks.mocks.dart` | `pro-iq/gen_mocks.sh` | repo root |
| `pro-iq/lib/l10n/gen/pro_iq_localizations*.dart` | `flutter gen-l10n` | `pro-iq/` |
| `pro-iq/lib/models/gen/protobuf/pro_iq.pb.dart` (and siblings) | `gen_proto.sh` | repo root |

**When to regenerate:**
- `gen_mocks.sh` — any time a class that is mocked (e.g. `DataManager`) has a
  new method or a changed method signature.
- `flutter gen-l10n` — any time a `.arb` file is edited.
- `gen_proto.sh` — any time `protobuf/pro_iq.proto` is changed.

---

## Expected output

After completing the checklist, output a brief report directly in the chat
(no output file needed) that lists each step with a checkmark and any notes,
complications, or items requiring the user's attention. Example format:

```
✅ Step 0 — Affected submodules: pro-iq, adair-flutter-lib
✅ Step 1 — Tests: added 12 tests to data_manager_test.dart; added
            text_input_autocomplete_test.dart (8 tests). No unreachable
            paths found.
✅ Step 2 — Duplication: extracted User.fullName extension; moved repeated
            stream stubs to setUp; promoted 2 local helpers to top-level.
⚠️  Step 3 — Dead code: `_buildRolesRequired` has a branch that can never
             return non-null when _isPlayer/_isAdmin/_isCoach are all false
             simultaneously in the current call site — flagged for review.
✅ Step 4 — Formatting: dart format applied, 3 files changed.
✅ Step 5 — Tests: all 47 tests pass.
✅ Step 6 — ARB: 2 missing keys in adair_flutter_lib_es.arb (inputNameLabel,
            inputDescriptionLabel) — translated and added.
```
