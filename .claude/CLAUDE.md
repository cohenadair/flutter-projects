# Collaboration preferences

- **Before making any code change**, briefly list any possibly unintended side-effects (other
  features, pages, or tests that may be affected). Do this even when the change is explicitly
  requested. Keep the warning concise — bullet points are fine.
- **PR titles start with the issue they fix**, as `#<n>: ` (e.g. `#921: Add
  setting to copy catches at the current date and time`). Use the issue the
  PR closes (`Fixes #n` / `Closes #n`). A PR with no linked GitHub issue
  (e.g. a Crashlytics-only fix) keeps a plain title.

---

# Flutter code

- **Before writing, editing, reviewing, or testing any Dart code — even a
  one-line fix — load the `flutter-conventions` skill.** It holds every
  coding, architecture, Firestore/proto, and test rule for this monorepo.
  Change those rules there, not here.
