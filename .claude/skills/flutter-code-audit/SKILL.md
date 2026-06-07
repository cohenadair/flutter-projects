---
name: flutter-code-audit
description: >
  Comprehensive audit of any Flutter codebase. Use this skill whenever the user asks for
  a code review, audit, health check, or wants to find bugs, convention violations, code
  smells, or quality issues across the codebase. Trigger on: "audit the codebase", "do a
  code review", "find bugs", "check conventions", "code health check", "what's wrong with
  the code", or any similar request to systematically review Flutter/Dart code for issues.
  Also use proactively after large refactors or before a release.
---

# Flutter Code Audit

A systematic review of a Flutter codebase for bugs, convention violations, and code
quality issues.

---

## Before launching agents — read CLAUDE.md

Read `.claude/CLAUDE.md` (and any sub-project CLAUDE.md files) before briefing the
exploration agents. Two things to extract:

1. **Project-specific conventions** — naming rules, base classes, shared libraries,
   spacing/constant systems, test utilities, import paths. These get folded into Agent 2's
   checklist alongside the universal checks below.
2. **Project architecture** — does the project have a wrapper/manager pattern? A shared
   lib? Separate sub-projects? Agent 3 needs this to know where extracted shared code
   should live.

If no CLAUDE.md exists, proceed with the universal checks only.

---

## Scope — full codebase vs. changed files only

If the user's request asks to audit only **uncommitted changes** (e.g. "audit my changes", "review changed files", "check my diff", "only look at what I changed"), determine the changed-file list before launching any agents:

```bash
git diff --name-only HEAD          # modified/deleted tracked files (staged + unstaged)
git ls-files --others --exclude-standard  # new untracked files
```

Collect the union of both outputs. If the list is empty, tell the user there are no uncommitted changes and stop.

Pass the list to all three Phase 1 agents with the instruction: **"Only examine these files: `<list>`. Do not report findings in any other files. However, for any code introduced or modified in these files, search the broader codebase to check whether equivalent code already exists elsewhere — and flag it as a duplication finding if so."**

If the user does not specify changed-files-only, proceed with the full codebase audit as normal.

---

## Phase 1 — Parallel Exploration

Launch **three Explore agents in parallel** (single message, all three tool calls at once).
Each agent has a distinct focus so findings don't overlap.

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

If the project uses **Firestore + protobuf**, also check:

- **Missing `clearId()` (or equivalent) before writes** — ID fields derived from document
  IDs must be cleared before serializing to Firestore. Look for the project's pattern
  (e.g., `..clearId()` before `.toProto3Json()`) and flag write paths that skip it.
- **Proto/value-type null checks** — fields that default to a zero-value (empty string,
  0, false) must be guarded with `.isEmpty` / `== 0` etc., not null checks.

If the project uses a custom async widget builder (`SafeFutureBuilder` or similar),
check that any required error-handling parameters are always provided.

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
- **Dead code** — unreferenced variables, methods, or classes.

---

## Phase 2 — Compile Findings

After all three agents finish, compile results into a plan file at
`.claude/plans/flutter-audit-<date>.md`.

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
```

Use `~` before line numbers to signal approximation. Include the problematic code snippet
inline when it helps clarify the issue.

---

## Phase 3 — User Review & False Positive Handling

After presenting the findings, enter plan mode and wait for the user to review.

Common false positives to anticipate across any Flutter project:

- **Custom Scaffold / root widget** — a page using `Scaffold` directly may be intentional
  (e.g., a navigation shell with `IndexedStack`, or a list-first page). Check the
  project's convention before flagging.
- **Spread syntax in widget lists** — only flag when there is a single conditional widget
  that could use early return; list comprehensions and multi-widget spreads in `actions:`
  or `children:` are often correct.
- **Stream `onError`** — if the stream pipeline already applies `.handleError()` upstream,
  the absence of `onError` on `.listen()` may be deliberate. Understand the error-handling
  architecture before flagging.
- **`clearId()` / zero-value clearing on new objects** — when a proto or model is freshly
  constructed with default field values, clearing those fields before writing is about
  explicitness and safety rather than a functional bug. Still worth doing, but low severity.
- **Single-line if without braces** — some projects explicitly allow this for `return`
  statements. Check CLAUDE.md before flagging.

When the user dismisses a finding:
- Remove it from the plan.
- If the dismissal reveals an ambiguity or gap in `CLAUDE.md`, update the relevant rule
  there too — so the same thing isn't flagged again in a future audit.

---

## Phase 4 — Implementation

Once the user approves the revised finding list, exit plan mode and implement all fixes.

### Fix ordering: bugs first, then conventions, then quality

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

### CLAUDE.md updates

If a finding reveals a rule that's ambiguous or missing from `CLAUDE.md`, update it as
part of this fix pass — not as a separate follow-up.

### Skill self-update

After completing fixes, review whether any finding revealed:
- A check that Agent 1, 2, or 3 **should have caught but didn't** (gap in the checklist).
- A **false positive pattern** that recurred (add it to the Phase 3 false-positive list).
- A **fix recipe** for Phase 4 that's missing or unclear.

If any of the above apply, update **this file** (`flutter-code-audit/SKILL.md`) in the
same commit — not as a separate follow-up.

---

## Verification

After all fixes:
1. Run `flutter analyze` across all sub-projects.
2. Run `flutter test` across all sub-projects.
3. For any write-path fixes (e.g., ID field clearing before Firestore writes), note in
   the summary that the fix should be manually verified in dev against the actual stored
   document.
