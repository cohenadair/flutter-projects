---
name: run-flutter-tests
description: >
  Runs dart format and flutter test across all Flutter submodules in this
  repo. Use when the user says "run all tests", "run flutter tests",
  "test everything", "run all flutter tests", or similar.
---

# Run Flutter Tests Skill

Run `dart format lib test && flutter test` in all four submodules **in
parallel** (single Bash message, four independent tool calls):

| Submodule | Working directory |
|-----------|------------------|
| `pro-iq` | `/Users/cohen/Documents/flutter-projects/pro-iq` |
| `adair-flutter-lib` | `/Users/cohen/Documents/flutter-projects/adair-flutter-lib` |
| `anglers-log/mobile` | `/Users/cohen/Documents/flutter-projects/anglers-log/mobile` |
| `activity-log/mobile` | `/Users/cohen/Documents/flutter-projects/activity-log/mobile` |

Command for each:

```bash
cd <working-directory> && dart format lib test 2>&1 | tail -3 && flutter test 2>&1 | tail -5
```

After all four complete, output a summary table:

| Project | Tests Run | Passed | Failed |
|---------|-----------|--------|--------|
| `pro-iq` | N | N | N |
| `adair-flutter-lib` | N | N | N |
| `anglers-log/mobile` | N | N | N |
| `activity-log/mobile` | N | N | N |
| **Total** | **N** | **N** | **N** |

Parse the test count from the final `flutter test` output line (e.g.
`+173: All tests passed!` → 173 passed, 0 failed; `+170 -3: ...` → 170
passed, 3 failed).

If any submodule has failures, list the failing test names below the table.
