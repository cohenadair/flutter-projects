---
name: flutter-code-review
description: >
  Systematic Flutter code review, in two modes. Pre-commit mode (default):
  prepares uncommitted Flutter changes for commit and pull request, running
  review agents scoped to the diff plus test-writing, formatting, coverage,
  and ARB translation checks — trigger on "prepare our changes for a pull
  request", "run through the pre-commit checklist", "pre-commit checklist",
  "get the code ready to commit", "do a code review", "find bugs", "check
  conventions", or similar with no explicit whole-codebase scope. Full-audit
  mode: comprehensive review of the entire codebase — trigger only when the
  user explicitly asks for the whole codebase, e.g. "audit the codebase",
  "review the whole codebase", "full codebase review". Also use proactively
  after large refactors or before a release.
---

# Flutter Code Review

A systematic review of a Flutter codebase for bugs, convention violations,
code quality issues, and efficiency/cost problems — either scoped to
uncommitted/branch changes (pre-commit mode, the default) or across the whole
codebase (full-audit mode, explicit opt-in only).

**Start immediately.** Do not enter plan mode, present a plan, or ask for
confirmation before launching Step 2's exploration agents — launching those
four agents in parallel is the first action of this skill, right after Step 1
(or immediately, in full-audit mode). Plan mode only ever applies later, at
Step 4, after findings exist to review.

---

## Mode selection

Both modes share one pipeline; steps marked **(pre-commit only)** or
**(full-audit only)** are skipped in the other mode.

- **Pre-commit mode (default)** — used for any request that doesn't
  explicitly name the whole codebase, including "prepare our changes for a
  pull request", "run through the pre-commit checklist", "pre-commit
  checklist", "get the code ready to commit", "do a code review", "find
  bugs", "check conventions", "code health check", "what's wrong with the
  code", or any other request to look at or improve the code without a
  stated scope. Scope = uncommitted changes (Step 1).
- **Full-audit mode** — used **only** when the user explicitly asks to
  review the entire codebase, e.g. "audit the codebase", "review the whole
  codebase", "full codebase review", "check the entire codebase", or
  proactive use after a large refactor / before a release. Scope = entire
  codebase; Step 1 is skipped entirely.

Do not ask the user which mode they want. If scope isn't explicitly stated,
default to pre-commit mode — the user will say so explicitly when they want
the whole codebase reviewed instead.

---

## Before launching agents — read CLAUDE.md

Read `.claude/CLAUDE.md` (and any sub-project CLAUDE.md files) before
briefing the exploration agents. Three things to extract:

1. **Project-specific conventions** — naming rules, base classes, shared
   libraries, spacing/constant systems, test utilities, import paths. These
   get folded into Agent 2's checklist alongside the universal checks below.
2. **Project architecture** — does the project have a wrapper/manager
   pattern? A shared lib? Separate sub-projects? Agent 3 needs this to know
   where extracted shared code should live.
3. **Whether the project/submodule uses Firebase** (Firestore, Storage,
   Cloud Functions) — check `pubspec.yaml` dependencies and CLAUDE.md. Agent
   4 only runs its Firebase-cost checks when this is true.

If no CLAUDE.md exists, proceed with the universal checks only.

---

## Step 1 — Determine scope **(pre-commit mode only)**

Both detection phases below operate **only on submodules** — the root repo
is always excluded.

### Phase A — uncommitted changes

From the **repo root** (`/Users/cohen/Documents/flutter-projects`), run:

```bash
git submodule foreach git diff --stat HEAD
```

If **any** submodule reports changes, use those submodules for the rest of
this skill. Skip Phase B entirely.

Also check for changed TypeScript files in Cloud Functions directories:

```bash
git -C pro-iq diff --stat HEAD -- functions/src/
```

If any non-test `.ts` files appear, include `pro-iq/functions` in the
affected set.

### Phase B — branch diff (fallback)

Used only when Phase A finds **zero** uncommitted changes in any submodule
AND the current branch is not `main` or `master`.

For each submodule, determine its base branch and list changed files:

```bash
# Determine base branch (try main first, then master)
git -C <submodule> rev-parse --verify main 2>/dev/null && echo main || echo master

# List files changed relative to base
git -C <submodule> diff --stat <base>...HEAD
```

Submodules with output from the diff command are the affected submodules.
The changed `.dart` files drive the rest of this skill, exactly as
uncommitted files do in Phase A. Note in the scope report that branch-diff
mode is active (e.g. "Branch diff mode: comparing to main").

### Edge cases

- **On main/master with no uncommitted changes:** Nothing to prepare — tell
  the user and stop.
- **Submodule has neither `main` nor `master`:** Skip that submodule and
  note it in the scope report.

The Flutter project root for each submodule is the submodule directory
itself (e.g. `pro-iq/`, `adair-flutter-lib/`).

---

## Step 2 — Parallel Exploration

Launch **four Explore agents in parallel** (single message, all four tool
calls at once). Each agent has a distinct focus so findings don't overlap.

In pre-commit mode, brief all four agents with: **"Only examine these
files: `<list from Step 1>`. Do not report findings in any other files.
However, for any code introduced or modified in these files, search the
broader codebase to check whether equivalent code already exists elsewhere
— and flag it as a duplication finding if so."** In full-audit mode, agents
examine the whole codebase.

### Agent 1 — Bugs & Crashes

Universal Flutter checks:

- **Uncaught force casts** — `value as SomeType` without a surrounding try/catch can
  throw `CastError`. Prefer an `is` check or wrap with try/catch + logging.
- **Empty or logging-free catch blocks** — every `catch` must at minimum log the
  exception. Silent swallowing hides real failures.
- **`setState` or `context` after async gap without `!mounted` guard** — any use of
  `setState`, `Navigator`, or `context` following an `await` must be preceded by
  `if (!mounted) return;`.
- **Unhandled stream errors** — `.listen()` calls without `onError`. Note: if the stream
  already calls `.handleError()` upstream, the absence of `onError` on `.listen()` may be
  intentional — check before flagging.
- **Futures not awaited** — calls to async methods whose return value is discarded
  (`unawaited` futures) can silently fail.
- **State that was previously recomputed per-build now cached in a field** — when a
  refactor (e.g. a platform-branching cleanup) moves a value that used to be read fresh
  from a live object on every build (e.g. `controller.value.aspectRatio` inside
  `build()`) into a field that's only assigned once (e.g. on initial load), check every
  other place the underlying live value can change (advancing to the next item in a
  list/queue, seeking, switching tabs) and confirm the field is updated there too.
  Diff the before/after data flow, not just the before/after widget tree.

If the project uses **Firestore + protobuf**, also check:

- **Missing `clearId()` (or equivalent) before writes** — ID fields derived from document
  IDs must be cleared before serializing to Firestore. Look for the project's pattern
  (e.g., `..clearId()` before `.toProto3Json()`) and flag write paths that skip it.
- **Proto/value-type null checks** — fields that default to a zero-value (empty string,
  0, false) must be guarded with `.isEmpty` / `== 0` etc., not null checks.
- **Proto presence-check pattern by field type** — `string` fields must use
  `.isEmpty`/`.isNotEmpty`; every other field type (numeric, message, enum, etc.) must
  use the generated `has*()` method. Flag a `string` field checked via `has*()`, or a
  non-string field checked via a manual default-value comparison. If the same field is
  checked both ways at different call sites in the diff, that's a stronger signal.
- **Eagerly-started side-effecting futures not tracked for cleanup on failure** — when
  code kicks off an async side effect (e.g. an upload) that writes to external storage
  before or during a `try` block, check whether that side effect's target path is
  recorded somewhere a failure-cleanup mechanism (e.g. an "orphan cleanup" pending-doc
  pattern) can find it — even if the side effect itself swallows its own errors and
  never throws. A future that "never throws" can still leak state if nothing tracks
  what it wrote.

Check that `FutureBuilder` and `StreamBuilder` are never used directly — they must be
replaced with `AsyncBuilder.future` / `AsyncBuilder.stream` (from
`package:adair_flutter_lib/widgets/async_builder.dart`). The `errorReason` parameter
is required on every `AsyncBuilder` instance.

### Agent 2 — Coding Convention Violations

These are the universal Dart/Flutter conventions for all projects in this repo. Also
fold in any additional project-specific conventions found in the project's CLAUDE.md.

**Dart style**
- **String literals** — double quotes, not single quotes. **Exception: `import` and `export` directives always use single quotes** — do not flag them.
- **If bodies** — always use curly braces, even for single-line returns.
- **Magic numbers** — raw numeric values for sizing, elevation, or radii must be
  declared as `static const` fields at the top of the class, or use the project's
  named spacing constants. Never use inline numeric literals for layout values.
- **Boolean naming** — prefer a 3rd-person verb form over adding a prefix word:
  - Multi-word: use the verb in present-tense 3rd person, e.g. `extendsBodyBehindAppBar`,
    `centersContent`, `restrictsWidth`, `alignsRight`, `obscuresText`, `popsOnTap`,
    `includesYears`. This avoids the extra `should`/`is` word.
  - Single-word or past-participle state: `is` prefix is fine, e.g. `isEnabled`,
    `isRequired`, `isAutofocused`, `isNavRailContent`.
  - Never use `should` as a prefix — it's always replaceable with the verb form above.
- **`final` constants that could be `static const`** — a `final double _size = 20.0`
  that is not instance-dependent (no constructor parameters, no state) should be
  `static const double _size = 20.0`.
- **Doc comments for instance variables** — go directly above each variable declaration,
  not inside the class-level doc comment. See `AutocompleteTextInput` in
  `adair-flutter-lib/lib/widgets/autocomplete_text_input.dart` as the reference.
- **Unused required parameters** — must use the `_` wildcard, not a named identifier
  (e.g. `void onTap(BuildContext _)` when `context` is not used).

**Widget structure**
- **Widget method order** — `build()` must appear after lifecycle methods (`initState`,
  `dispose`, `didUpdateWidget`, etc.) but before any other methods or helpers.
- **Conditional widgets** — `if (cond) ...[widget]` spread syntax inside a widget list
  is a violation when the condition could instead be handled by a `_build*` method that
  returns `const SizedBox()` early. (Spread is fine in `actions:` lists and similar
  places where there is no single widget to return.)

**Imports**
- **Dead imports** — imports that are no longer referenced anywhere in the file.

**Project-specific checks (from CLAUDE.md)**
Append any additional rules found in the project's CLAUDE.md here. Examples of what
to look for:
- Custom spacing/constant system (e.g., named padding constants instead of raw numbers)
- Required base classes for pages, dialogs, or async builders
- Specific color extensions for action vs. destructive icons
- Stale or non-canonical import paths
- Test utility conventions (custom pump helpers, assertion helpers, `group()` ban, etc.)

### Agent 3 — Code Quality & Duplication

- **Identical private methods across files** — the same `_buildError()`, `_buildLoading()`,
  or similar helper appearing verbatim in multiple files is a candidate for a shared widget
  or mixin.
- **Repeated inline widget structures** — the same structural pattern (e.g.,
  `Row([Icon, SizedBox, Text])`) appearing in 3+ methods in the same file is a candidate
  for a private helper method.
- **`setState` inside `try`/`catch`** — the correct async pattern is a single `setState`
  call at the end of the method, after the try/catch block. An opening `setState` to set
  busy/loading state at the top is fine; one inside `try` or `catch` is not.
- **Error state not cleared at the start of a save** — async save methods that show
  inline errors should reset the error field (`_error = ""`) alongside the busy flag in
  the opening `setState`, so stale errors don't persist into the next attempt.
- **Architecture violations** (if the project uses a wrapper/manager pattern):
  - Business logic inside wrappers (wrappers should be thin, 1:1 SDK delegations to a
    single third-party library — they must not call other wrappers).
  - Generic-enough wrappers or managers living in a sub-project that should be moved to
    `adair-flutter-lib`.
  Note: managers may freely call other managers. Only wrappers are prohibited from
  cross-dependency.
- **Naming-issue TODOs** — TODO/FIXME comments that explicitly call out a misleading or
  wrong name (class, method, variable, file) are a finding. List them — they represent
  confirmed tech debt.
- **Dead or unreachable code** — unreferenced variables, methods, or classes, and
  branches that can never execute given the surrounding logic. For every changed/audited
  file, reason through each `if`/`else`, guard clause, and null check: is there an
  earlier guard that makes a later branch unreachable? Is there a null check on a value
  already asserted non-null? Report these explicitly rather than silently deleting code
  — the user may know a reason it's there.

### Agent 4 — Efficiency & Firebase Cost

Findings from this agent are lower-confidence than bugs — many are legitimate
tradeoffs, not defects. Flag them as suggestions, not required fixes, and let
the user decide during review (Step 4).

**Code efficiency**
- **Expensive work inside `build()`** — sorting, filtering, or mapping a list on every
  rebuild instead of memoizing/caching the result outside `build()`.
- **Missing `const` constructors** — widgets that could be `const` but aren't, causing
  avoidable rebuilds.
- **Heavy synchronous work on the UI thread** — CPU-bound work (parsing, image
  processing, large collection transforms) that should move to `compute()` or an
  isolate instead of blocking the frame.
- **Repeated redundant computation** — the same derived value recomputed in multiple
  nearby methods instead of computed once and reused.
- **Nested-loop lookups** — an `O(n*m)` search (looping a list inside a loop) where a
  `Map`/`Set` lookup would be `O(n)`.
- **Loading a full list into memory** where pagination or streaming would do (e.g. a
  `ListView` fed by a fully-materialized list instead of `ListView.builder` with lazy
  data).

**Firebase cost efficiency** (only when the project/submodule uses Firebase — check
`pubspec.yaml` and CLAUDE.md before running these checks; skip entirely otherwise)
- **Unbounded queries** — Firestore queries missing `.limit()`.
- **Over-fetching** — reading an entire collection where a targeted query or a
  single-doc `get()` would work.
- **N+1 query patterns** — looping single-document fetches instead of a batched or
  `whereIn` query.
- **Long-lived or leaked listeners** — `.snapshots()` subscriptions that outlive their
  need, or aren't cancelled in `dispose()`.
- **Listening to a whole collection** when only specific documents are actually used.
- **Redundant writes** — writes that set fields to their already-current value, or
  frequent small writes that could be batched into one.
- **Full Storage object downloads** where only metadata (size, content type) is needed.

---

## Step 3 — Compile Findings

After all four agents finish, compile results.

- **Full-audit mode**: write to a plan file at
  `.claude/plans/flutter-audit-<date>.md`.
- **Pre-commit mode**: hold the findings in-memory to prefix the final
  checklist report (Step 11) — no separate plan file needed unless the
  findings are extensive enough that plan-mode review is warranted.

Present findings as severity-grouped tables:

```
### 🔴 Bugs & Potential Crashes
| # | File | Line | Issue |
|---|------|------|-------|
| B1 | path/to/file.dart | ~42 | Short description |

### 🟡 Convention Violations
| # | File | Line | Convention | Issue |
|---|------|------|-----------|-------|
| C1 | ... | ~15 | Widget structure | build() appears after _helper() |

### 🔵 Code Quality & Duplication
| # | Files | Issue |
|---|-------|-------|
| Q1 | file_a.dart, file_b.dart | Identical _buildError() in both files |

### 🟢 Efficiency & Firebase Cost (suggestions)
| # | File | Line | Issue |
|---|------|------|-------|
| E1 | path/to/file.dart | ~30 | Unbounded Firestore query missing .limit() |
```

Use `~` before line numbers to signal approximation. Include the problematic code snippet
inline when it helps clarify the issue.

---

## Step 4 — User Review & False Positive Handling

After presenting the findings, enter plan mode and wait for the user to review.

Common false positives to anticipate across any Flutter project:

- **Custom Scaffold / root widget** — a page using `Scaffold` directly may be intentional
  (e.g., a navigation shell with `IndexedStack`, or a list-first page). Check the
  project's convention before flagging.
- **Spread syntax in widget lists** — only flag when there is a single conditional widget
  that could use early return; list comprehensions and multi-widget spreads in `actions:`
  or `children:` are often correct.
- **`if (cond) cell` in `TableRow.children`** — not a violation. A `Table`'s rows must all
  have matching column counts, so a column can only appear/disappear as a whole across the
  header row and every data row. This requires the conditional-spread form; only flag it if
  the same conditions are *not* applied identically (and in the same order) across all rows.
- **Stream `onError`** — if the stream pipeline already applies `.handleError()` upstream,
  the absence of `onError` on `.listen()` may be deliberate. Understand the error-handling
  architecture before flagging.
- **`clearId()` / zero-value clearing on new objects** — when a proto or model is freshly
  constructed with default field values, clearing those fields before writing is about
  explicitness and safety rather than a functional bug. Still worth doing, but low severity.
- **Single-line if without braces** — some projects explicitly allow this for `return`
  statements. Check CLAUDE.md before flagging.
- **Efficiency/cost suggestions (Agent 4)** — a missing `.limit()` or a full collection
  read may be intentional (e.g. an admin tool, a small bounded collection). Treat these
  as discussion points, not defects, unless the collection is known to be large/growing.

When the user dismisses a finding:
- Remove it from the findings.
- If the dismissal reveals an ambiguity or gap in `CLAUDE.md`, update the relevant rule
  there too — so the same thing isn't flagged again in a future review.

---

## Step 5 — Implement Approved Fixes

Once the user approves the revised finding list, exit plan mode and implement all fixes.

### Fix ordering: bugs first, then conventions, then quality, then efficiency/cost

**Bug fixes:**
- Force cast — wrap in try/catch with logging and rethrow.
- Empty catch — add a log call at minimum.
- Missing `!mounted` — add `if (!mounted) return;` before the first post-await use of
  `setState` or `context`.
- Missing ID clear before write — chain the clear call before serialization.

**Convention fixes:**
- Widget method order — reorder so lifecycle methods come first, then `build()`, then
  `_build*` helpers, then other private methods.
- Conditional widgets — extract to a `_build*` method that returns `const SizedBox()`
  early.
- Test helper placement — move helper functions above the first `test()` call in `main()`.

**Quality fixes:**
- Extracted shared widgets or helpers go in `adair-flutter-lib/lib/widgets/` (or
  `managers/` / `wrappers/` / `utils/` as appropriate) and are imported via
  `package:adair_flutter_lib/…`. If the extracted code is specific to the current
  project, put it in the project's own `lib/widgets/` or `lib/utils/` instead.
- When removing a duplicated method, check whether any of its imports are now unused in
  the file and remove them too.
- Error state fix — add `_error = ""` alongside `_isSaving = true` in the opening
  `setState` of async save methods.

**Efficiency/cost fixes (only the ones the user approved):**
- Memoize/cache expensive `build()`-time computation in a field, recomputed only when
  the underlying input changes.
- Add `const` to widget constructors where the arguments are all compile-time constant.
- Add `.limit()` to unbounded queries; replace looped single-doc fetches with a batched
  or `whereIn` query; cancel listeners in `dispose()`.

### CLAUDE.md updates

If a finding reveals a rule that's ambiguous or missing from `CLAUDE.md`, update it as
part of this fix pass — not as a separate follow-up.

---

## Step 6 — Write / update tests **(pre-commit mode only)**

For each affected Flutter submodule, read every changed `.dart` file under
`lib/` — including any files touched by Step 5's fixes — and write or update
tests to achieve as close to **100% branch coverage** as possible.

See [CLAUDE.md](../../.claude/CLAUDE.md) for full testing conventions (no
`group()`, one test per branch, `StubbedManagers`, `pumpContext`, stub
patterns, etc.) and Dart/Flutter style rules.

### File placement

Test files mirror the `lib/` tree under `test/`:
- `lib/pages/foo_page.dart` → `test/pages/foo_page_test.dart`
- `lib/widgets/bar.dart` → `test/widgets/bar_test.dart`
- `lib/managers/baz_manager.dart` → `test/managers/baz_manager_test.dart`
- `lib/utils/string.dart` → `test/utils/string_test.dart`

### TypeScript Cloud Functions

For any non-test `.ts` file changed under `*/functions/src/` (i.e. files that
are **not** `*.test.ts`), write or update tests in the collocated `.test.ts`
file (e.g. `functions/src/index.ts` → `functions/src/index.test.ts`).

Apply the same one-test-per-branch rule as Dart. Key patterns for
`pro-iq/functions/src/index.test.ts`:

- All `jest.mock(...)` calls must be at the top of the file, before any
  imports — Jest hoists them automatically.
- Mock `firebase-functions/v2/firestore` to expose Firestore trigger handlers
  directly (same pattern as the existing `onCall` mock):
  ```ts
  jest.mock("firebase-functions/v2/firestore", () => ({
    onDocumentCreated: (_path: string, handler: (event: unknown) => unknown) => handler,
    onDocumentUpdated: (_path: string, handler: (event: unknown) => unknown) => handler,
  }));
  ```
- Write narrow type aliases for each handler and small helper functions to
  invoke them with synthetic event objects (see `callOnVideoCreated` /
  `callOnVideoUpdated` in `index.test.ts` as the reference example).
- Run tests with:
  ```bash
  cd pro-iq/functions && npm test
  ```

---

## Step 7 — Format

For each affected Flutter submodule, run from its project root:

```bash
dart format lib test
```

Example:
```bash
cd /Users/cohen/Documents/flutter-projects/pro-iq && dart format lib test
cd /Users/cohen/Documents/flutter-projects/adair-flutter-lib && dart format lib test
```

In full-audit mode, run this across every submodule; in pre-commit mode, run
it only on the affected submodules from Step 1.

---

## Step 8 — Run tests

For each affected Flutter submodule, run from its project root:

```bash
flutter test
```

For each affected Cloud Functions directory (e.g. `pro-iq/functions/`), run:

```bash
cd pro-iq/functions && npm test
```

All tests must pass. If any fail, investigate and fix:

- If the fix is in a **test file** (wrong stub, missing mock, incorrect assertion) → fix it directly.
- If the fix is in an **implementation file** (`lib/` or `functions/src/`) → flag the issue to the user with a description of the problem and wait for approval before making any change.

If tests fail with a mockito `MissingStubError` or a `noSuchMethod`/type cast
error on a mock, check whether `test/mocks/mocks.mocks.dart` is stale
relative to the real class before touching test setup code — a class member
added to a manager/wrapper doesn't automatically appear in the generated
mock. Regenerate with `gen_mocks.sh` (pro-iq) or `dart run build_runner
build` (adair-flutter-lib) rather than hand-editing the generated file. This
same staleness can also cause confusing cascading mockito failures (e.g.
"Cannot call `when` within a stub response") in unrelated tests within the
same run — don't assume those are real regressions before checking the mock
is current.

Re-run until all tests pass before proceeding.

---

## Step 9 — Check test coverage **(pre-commit mode only)**

Run the `pre-commit-test-coverage` skill on the affected Flutter submodules and
test files identified in Step 1. All tests must already pass (Step 8) before
running this step.

For affected Cloud Functions directories, Jest reports coverage automatically
when `npm test` runs (configured via `jest.config.js`). Review the per-file
coverage table it prints.

Apply the same threshold to both Dart and TypeScript coverage:

- **Changed coverage** below **90%** is flagged. For each such file, report a
  one-line explanation of what's uncovered and why (e.g. "the `catch` block
  on line 42 has no test", "the `else` branch of the role check on line 78
  is untested") — not just the percentage.
- Then ask the user whether to write tests to close each gap. Do **not**
  write those tests automatically — this is a decision point, not an
  auto-fix.
- **Total coverage** is informational — note any significant regressions but
  do not block on this metric.

Report the table (with per-file shortfall explanations) verbatim in the
coverage line of the final checklist output (Step 11).

---

## Step 10 — Check ARB translation coverage **(pre-commit mode only)**

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

## Step 11 — Final Report

**Full-audit mode**: the findings compiled in Step 3 (as revised through
Step 4) *are* the deliverable — no further mechanical steps apply. Confirm
the plan file is up to date after Step 5's fixes.

**Pre-commit mode**: output a brief report directly in the chat (no output
file needed) that lists each step with a checkmark and any notes,
complications, or items requiring the user's attention — prefixed with a
short summary of what Step 3/4's review agents found and fixed, so the whole
run reads as one coherent report. End the report with an **Ad-hoc Testing
Areas** section (see below). Example format:

```
✅ Review — Agents found 2 bugs (fixed), 3 convention violations (fixed),
            1 duplication (extracted), 2 efficiency suggestions (1 applied,
            1 dismissed — bounded collection).
✅ Step 1 — Affected submodules: pro-iq, adair-flutter-lib
✅ Step 6 — Tests: added 12 tests to data_manager_test.dart; added
            text_input_autocomplete_test.dart (8 tests).
✅ Step 7 — Formatting: dart format applied, 3 files changed.
✅ Step 8 — Tests: all 47 tests pass.
⚠️  Step 9 — Coverage:
   | data_manager_test.dart | 8/10 lines (80%) — line 42 catch block untested | 34/47 lines (72%) |
   | all_users_page_test.dart | 5/5 lines (100%) | 61/80 lines (76%) |
✅ Step 10 — ARB: 2 missing keys in adair_flutter_lib_es.arb (inputNameLabel,
            inputDescriptionLabel) — translated and added.

🔎 Ad-hoc Testing Areas — parts of the app changed incidentally to the core
   feature/fix, worth a manual spot-check since tests may not fully exercise
   the interaction path:
   - lib/pages/mobile_home_page.dart — sign-out now unregisters the FCM
     token first; verify sign-out still completes normally.
   - lib/pages/players_page.dart — refactored to a shared selection
     controller; verify player selection, select-all, and group toggling.
```

### Ad-hoc Testing Areas (pre-commit mode only)

List every part of the app that was changed *incidentally* to the core
feature/fix being committed — refactors, shared-widget extractions, rewired
callbacks, or sibling call sites touched along the way, as opposed to the
new/changed behavior that was the actual point of the diff. These are the
spots automated tests are least likely to catch a paper cut in (a rewired
callback, a moved widget, a changed signature), so call them out for the
user to spot-check by hand.

Derive the list by comparing the diff's core intent (the feature/fix being
committed, as stated by the user or evident from the primary new files) against
every changed region from Step 1's scope. Anything not serving that core
intent goes in the list. For each entry: `file — one-line description of
what changed and why it's incidental`. Omit the whole section if the diff
has no such incidental changes (e.g. a single-purpose bug fix that touched
only the buggy code path).

---

## Skill self-update

After completing a run, review whether any finding revealed:
- A check that Agent 1, 2, 3, or 4 **should have caught but didn't** (gap in
  the checklist).
- A **false positive pattern** that recurred (add it to Step 4's
  false-positive list).
- A **fix recipe** for Step 5 that's missing or unclear.

If any of the above apply, update **this file**
(`flutter-code-review/SKILL.md`) in the same commit — not as a separate
follow-up.

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

## Verification

After all fixes (both modes):
1. Run `flutter analyze` across all affected sub-projects.
2. Run `flutter test` across all affected sub-projects (Step 8 already does
   this; re-confirm green after any post-report changes).
3. For any write-path fixes (e.g., ID field clearing before Firestore writes),
   note in the summary that the fix should be manually verified in dev
   against the actual stored document.
