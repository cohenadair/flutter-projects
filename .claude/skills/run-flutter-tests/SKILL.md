---
name: run-flutter-tests
description: >
  Runs dart format and flutter test across all Flutter submodules in this
  repo (pro-iq, adair-flutter-lib, anglers-log, activity-log, tapd). Use
  when the user says "run all tests", "run flutter tests", "test
  everything", "run all flutter tests", or similar.
---

# Run Flutter Tests Skill

Run `dart format lib test && flutter test` in all five Flutter roots **in
parallel** (single message, five independent Bash calls). Paths are relative
to the monorepo root (the checkout holding this `.claude/`, which may be a
worktree):

| Submodule | Working directory |
|-----------|------------------|
| `pro-iq` | `pro-iq` |
| `adair-flutter-lib` | `adair-flutter-lib` |
| `anglers-log/mobile` | `anglers-log/mobile` |
| `activity-log/mobile` | `activity-log/mobile` |
| `tapd/mobile` | `tapd/mobile` |

Command for each:

```bash
cd <monorepo root>/<working-directory> && dart format lib test 2>&1 | tail -3 && flutter test 2>&1 | tail -5
```

After all five complete, output a summary table:

| Project | Tests Run | Passed | Failed |
|---------|-----------|--------|--------|
| `pro-iq` | N | N | N |
| `adair-flutter-lib` | N | N | N |
| `anglers-log/mobile` | N | N | N |
| `activity-log/mobile` | N | N | N |
| `tapd/mobile` | N | N | N |
| **Total** | **N** | **N** | **N** |

Parse the test count from the final `flutter test` output line (e.g.
`+173: All tests passed!` → 173 passed, 0 failed; `+170 -3: ...` → 170
passed, 3 failed).

If any submodule has failures, list the failing test names below the table.

If a run fails with mockito errors (`MissingStubError`, "Cannot call `when`
within a stub response"), check `.claude/troubleshooting/flutter-dart.md` →
Tests & mocks before touching test code.
