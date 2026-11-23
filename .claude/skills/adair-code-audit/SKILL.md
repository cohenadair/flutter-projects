---
name: adair-code-audit
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

# Adair Code Audit

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

## Before launching agents — read the conventions

Load the `flutter-conventions` skill (`SKILL.md`, `tests.md`, and
`firestore-protos.md`), and read `.claude/CLAUDE.md` plus any sub-project
`CLAUDE.md`, before briefing the exploration agents. Three things to
extract:

1. **Conventions** — every rule in `flutter-conventions`, plus any
   sub-project rules. They become Agent 2's checklist.
2. **Project architecture** — does the project have a wrapper/manager
   pattern? A shared lib? Separate sub-projects? Agent 3 needs this to know
   where extracted shared code should live.
3. **Whether the project/submodule uses Firebase** (Firestore, Storage,
   Cloud Functions) — check `pubspec.yaml` dependencies. Agent 4 only runs
   its Firebase-cost checks when this is true.

---

## Project-level additions

This skill holds only rules that apply to every sub-project. Anything that
applies to one sub-project lives in that sub-project's own skill of the same
name, at `<submodule>/.claude/skills/adair-code-audit/SKILL.md`. Such a file
is **not** standalone: it only adds to this skill. If a run starts from one
(e.g. `tapd:adair-code-audit`), follow this root skill and apply its additions.

For every submodule in scope (Step 1, or all submodules in full-audit mode),
read its project-level file, if it has one, before briefing the agents. Apply
its additions at the step they name. They typically cover:
- the Flutter root, when it isn't the submodule directory;
- extra scope, such as non-Dart code like Cloud Functions;
- extra agent checks;
- extra Step 4 false positives;
- test, mock-regeneration and generated-file commands;
- ARB locale rules.

Pass the relevant items to each agent.

Current project-level files:
- `tapd/.claude/skills/adair-code-audit/SKILL.md`
- `pro-iq/.claude/skills/adair-code-audit/SKILL.md`
- `anglers-log/.claude/skills/adair-code-audit/SKILL.md`
- `adair-flutter-lib/.claude/skills/adair-code-audit/SKILL.md`

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

Also run any extra scope checks from the affected submodules' project-level
files, e.g. a check for changed non-Dart code such as Cloud Functions.

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
itself, unless its project-level file names a subfolder (monorepo-style
submodules). Run `flutter`/`dart` commands from that Flutter root.

If the user narrows scope (e.g. "of all staged <submodule> changes"), honour it:
use `git diff --cached` for that submodule instead of `git diff HEAD`, and
tell the agents to read the staged diff. Unstaged edits made by Step 5 don't
alter the index, so never unstage or stash to isolate changes.

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

Each agent's checklist is in [agents.md](agents.md). Read it and give each
agent its full section (Agent 1 — Bugs & Crashes, Agent 2 — Coding
Convention Violations, Agent 3 — Code Quality & Duplication, Agent 4 —
Efficiency & Firebase Cost), plus that agent's additions from each affected
submodule's project-level file.

---

## Step 3 — Compile Findings

After all four agents finish, compile results.

- **Full-audit mode**: write to a plan file at
  `.claude/plans/flutter-audit-<date>.md`.
- **Pre-commit mode**: hold the findings in-memory to prefix the final
  checklist report (Step 11) — no separate plan file needed unless the
  findings are extensive enough that plan-mode review is warranted.

Present findings as severity-grouped **lists, not tables**. The plan
preview panel is narrow, so tables wrap badly. Each finding carries its
own proposed fix and side effects, so the user reviews one self-contained
item at a time. Don't put fixes or side effects in a separate section at
the end; the user would have to scroll back and forth between them.

```
### 🔴 Bugs & Potential Crashes

- **B1 — Short title**
  - *File:* `path/to/file.dart` ~42
  - *Issue:* What's wrong and how it fails.
  - *Fix:* The concrete change, including any tests to add or update.
  - *Side effects:* Other features, pages or tests affected, or "None".

### 🟡 Convention Violations

- **C1 — Widget structure: build() after helpers**
  - *File:* `path/to/file.dart` ~15
  - *Issue:* `build()` appears after `_helper()`.
  - *Fix:* Move `build()` above the `_build*` helpers.
  - *Side effects:* None.

### 🔵 Code Quality & Duplication

- **Q1 — Duplicated _buildError()**
  - *Files:* `file_a.dart`, `file_b.dart`
  - *Issue:* …
  - *Fix:* …
  - *Side effects:* …

### 🟢 Efficiency & Firebase Cost (suggestions)

- **E1 — Unbounded query**
  - *File:* `path/to/file.dart` ~30
  - *Issue:* The Firestore query is missing `.limit()`.
  - *Fix:* …
  - *Side effects:* …

### Dismissed (not planning to act)

- **Finding:** why it's a false positive or not worth acting on.
```

Use `~` before line numbers to signal approximation. Include the problematic code snippet
inline when it helps clarify the issue. Split long issue or fix text into
nested bullets rather than long sentences.

---

## Step 4 — User Review & False Positive Handling

After presenting the findings, enter plan mode and wait for the user to review.

Common false positives to anticipate across any Flutter project. Also apply
the Step 4 false positives in each affected submodule's project-level file.

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
  statements. Check `flutter-conventions` before flagging.
- **"Won't compile" claims from read-only agents** — agents can't run the
  analyzer, and extension methods (e.g. `firstWhereOrNull`) often resolve via
  re-exports they can't see. Run `dart analyze lib test` from the Flutter
  root before listing any compile-error finding.
- **Efficiency/cost suggestions (Agent 4)** — a missing `.limit()` or a full collection
  read may be intentional (e.g. an admin tool, a small bounded collection). Treat these
  as discussion points, not defects, unless the collection is known to be large/growing.

When the user dismisses a finding:
- Remove it from the findings.
- If the dismissal reveals an ambiguity or gap in `flutter-conventions`, update the relevant rule
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
- Before hoisting a per-item lookup into a parent's `build()` ("resolve once per
  list"), check who rebuilds on change. If the listener lives in a child (e.g.
  `ManageableListPage`'s `EntityListenerBuilder`), only the child rebuilds and the
  parent's hoisted value goes stale — keep the lookup in the item builder instead.

### Convention updates

If a finding reveals a rule that's ambiguous or missing from `flutter-conventions`, update it as
part of this fix pass — not as a separate follow-up.

---

## Step 6 — Write / update tests **(pre-commit mode only)**

For each affected Flutter submodule, read every changed `.dart` file under
`lib/` — including any files touched by Step 5's fixes — and write or update
tests to achieve as close to **100% branch coverage** as possible.

See `flutter-conventions` → [tests.md](../flutter-conventions/tests.md) for full testing conventions (no
`group()`, one test per branch, `StubbedManagers`, `pumpContext`, stub
patterns, etc.) and Dart/Flutter style rules.

### File placement

Test files mirror the `lib/` tree under `test/`:
- `lib/pages/foo_page.dart` → `test/pages/foo_page_test.dart`
- `lib/widgets/bar.dart` → `test/widgets/bar_test.dart`
- `lib/managers/baz_manager.dart` → `test/managers/baz_manager_test.dart`
- `lib/utils/string.dart` → `test/utils/string_test.dart`

### Non-Dart code

Tests for non-Dart code in scope, such as Cloud Functions, follow the
patterns in that submodule's project-level file. Apply the same
one-test-per-branch rule as Dart.

---

## Step 7 — Format

For each affected Flutter submodule, run from its project root:

```bash
dart format lib test
```

Example:
```bash
cd /Users/cohen/Documents/flutter-projects/<flutter-root> && dart format lib test
```

In full-audit mode, run this across every submodule; in pre-commit mode, run
it only on the affected submodules from Step 1.

---

## Step 8 — Run tests

For each affected Flutter submodule, run from its project root:

```bash
flutter test
```

Also run the test commands for any non-Dart code in scope, as given in the
project-level file.

All tests must pass. If any fail, investigate and fix:

- If the fix is in a **test file** (wrong stub, missing mock, incorrect assertion) → fix it directly.
- If the fix is in an **implementation file** (`lib/`, or non-Dart source) → flag the issue to the user with a description of the problem and wait for approval before making any change.

If tests fail with a mockito `MissingStubError` or a `noSuchMethod`/type cast
error on a mock, check whether `test/mocks/mocks.mocks.dart` is stale
relative to the real class before touching test setup code — a class member
added to a manager/wrapper doesn't automatically appear in the generated
mock. Regenerate with the submodule's mock-generation command (see its
project-level file) rather than hand-editing the generated file. This
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

For non-Dart code in scope, get coverage as the project-level file
describes.

Apply the same threshold to Dart and non-Dart coverage:

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
diff \
  <(jq -r 'keys[] | select(startswith("@") | not)' <base>.arb | sort) \
  <(jq -r 'keys[] | select(startswith("@") | not)' <locale>.arb | sort)
```

**Locale rules:** each submodule's project-level file has a Step 10 table.
It lists the base file, the locale files that need every key, and the
spelling-variant files that can be skipped.

Spelling-variant files such as `_en_US.arb` (US spelling, e.g. "canceled")
and `_en_GB.arb` (British spelling) hold only overrides, so they never need
every key. If a submodule with `.arb` changes has no locale table, ask the
user which files need full coverage and add a table to its project-level
file.

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
   - lib/pages/player_home_page.dart — sign-out now unregisters the FCM
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

Follow the `skill-maintenance` Retro at the end of every run. For this
skill, look especially for:
- A check that Agent 1, 2, 3, or 4 **should have caught but didn't** (a gap
  in the checklist; a convention gap goes in `flutter-conventions`).
- A **false positive pattern** that recurred (add it to Step 4's list).
- A **fix recipe** for Step 5 that's missing or unclear.

Where a rule goes: one for every sub-project in **this file**; one for a
single sub-project in that sub-project's project-level file
(`<submodule>/.claude/skills/adair-code-audit/SKILL.md`; create it and list
it under **Project-level additions** if needed). Never put sub-project
paths, versions, class names, or commands in this file.

---

## Reminders — generated files & regeneration scripts

See the `flutter-conventions` skill for style and coding rules. Never
edit generated files by hand, such as mocks, localizations and protobuf
output. Each project-level file lists its own generated files and the
commands that regenerate them.

---

## Verification

After all fixes (both modes):
1. Run `flutter analyze` across all affected sub-projects.
2. Run `flutter test` across all affected sub-projects (Step 8 already does
   this; re-confirm green after any post-report changes).
3. For any write-path fixes (e.g., ID field clearing before Firestore writes),
   note in the summary that the fix should be manually verified in dev
   against the actual stored document.
