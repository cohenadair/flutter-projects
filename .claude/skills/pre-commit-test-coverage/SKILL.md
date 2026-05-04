---
name: pre-commit-test-coverage
description: >
  Runs Flutter tests with coverage only on the test files that changed and
  outputs a per-file coverage table showing changed-line coverage and total
  coverage. Use when the user says "check test coverage", "run coverage on
  changed files", "pre-commit coverage", or when invoked by the
  pre-commit-checklist-skill.
---

# Pre-Commit Test Coverage Skill

Follow every step below in order.

---

## Step 1 — Identify changed files

Use the same Phase A / Phase B detection as `pre-commit-checklist-skill` Step 0
to determine affected submodules and changed `.dart` files.

### Phase A — uncommitted changes

```bash
git submodule foreach git diff --stat HEAD
```

### Phase B — branch diff (fallback)

Used only when Phase A finds zero uncommitted changes and the current branch is
not `main` or `master`.

```bash
git -C <submodule> diff --stat <base>...HEAD
```

For each affected submodule, build two lists:

- **Changed lib files** — `.dart` files under `lib/` that have edits.
- **Corresponding test files** — mirror each lib file into the `test/` tree:
  - `lib/managers/foo_manager.dart` → `test/managers/foo_manager_test.dart`
  - `lib/pages/bar_page.dart` → `test/pages/bar_page_test.dart`
  - `lib/widgets/baz.dart` → `test/widgets/baz_test.dart`
  - `lib/utils/string.dart` → `test/utils/string_test.dart`

If a changed lib file has no corresponding test file, record it as a warning row
in the final table and skip it in Steps 2–5.

---

## Step 2 — Run tests with coverage

For each affected submodule, run **only** the identified test files with coverage
enabled (single command per submodule):

```bash
cd <submodule-root> && flutter test --coverage \
  test/managers/foo_manager_test.dart \
  test/pages/bar_page_test.dart
```

Coverage output lands at `<submodule-root>/coverage/lcov.info`.

If any test fails, stop and report to the user before proceeding.

---

## Step 3 — Identify changed line numbers

For each changed lib file, extract the new/modified line numbers from the diff:

```bash
# Phase A (uncommitted)
git -C <submodule-root> diff HEAD --unified=0 -- lib/managers/foo_manager.dart

# Phase B (branch diff)
git -C <submodule-root> diff <base>...HEAD --unified=0 -- lib/managers/foo_manager.dart
```

Parse the hunk headers to collect changed line numbers:

- Each `@@ -old +new[,count] @@` header introduces a hunk. The `+new` value is
  the starting line in the new file; `count` (defaulting to 1 if absent) is the
  number of lines in the hunk.
- The set of changed lines is `{new, new+1, ..., new+count-1}`.
- Exclude lines where `count` is 0 (pure deletions — no new lines).

---

## Step 4 — Parse LCOV for per-file metrics

Read `<submodule-root>/coverage/lcov.info`. For each lib file, find its block:

```
SF:lib/managers/foo_manager.dart
DA:12,1        ← line 12 — 1 hit (covered)
DA:15,0        ← line 15 — 0 hits (not covered)
...
LH:34          ← lines hit (total)
LF:47          ← lines found / coverable (total)
end_of_record
```

Record every `DA:<line>,<hits>` entry and the `LH` / `LF` summary values.

---

## Step 5 — Compute coverage metrics

For each lib file:

**Changed coverage**

Cross-reference the changed line numbers (Step 3) with the DA entries (Step 4):

- Only count lines that appear in a DA entry (coverable lines).
- `changed_hit` = count of those lines with hits > 0.
- `changed_coverable` = total count of those lines present in DA.
- Percentage = `changed_hit / changed_coverable * 100` (0% if `changed_coverable` is 0).

**Total coverage**

- Percentage = `LH / LF * 100` from the LCOV block.

---

## Step 6 — Output the table

One row per test file. Use the short filename (no directory path). Format counts
as `hit/total lines (N%)`:

```
| Test File                  | Changed Coverage        | Total Coverage      |
|----------------------------|-------------------------|---------------------|
| foo_manager_test.dart      | 8/10 lines (80%)        | 34/47 lines (72%)   |
| bar_page_test.dart         | 5/5 lines (100%)        | 61/80 lines (76%)   |
```

For lib files with no corresponding test file, append a warning row:

```
| ⚠️ baz_widget.dart (no test file) | —               | —                   |
```

If `changed_coverable` is 0 for a file (all changed lines are non-coverable, e.g.
comments or blank lines), display `n/a` in the Changed Coverage column.
