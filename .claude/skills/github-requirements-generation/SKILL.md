---
name: github-requirements-generation
description: >
  Generates a filled-out implementation requirements template from a GitHub
  issue, scoped to this Flutter monorepo. Use whenever the user references a
  GitHub issue and wants a requirements doc, feature spec, or coding-agent
  prompt — including phrases like "fill out the template for issue #X",
  "generate requirements for this issue", "write the spec for this feature",
  "prepare this issue for implementation", or "make a prompt for this issue".
  Always invoke this skill when the user pastes or mentions a GitHub issue URL
  alongside any request related to planning, speccing, or implementing a feature.
---

# GitHub Requirements Generation

This skill turns a GitHub issue into a filled-out implementation prompt that a
coding agent (or you in a later session) can act on directly.

---

## Step 1 — Get the issue URL

If the user didn't provide a GitHub issue URL, ask:

> Which GitHub issue should I use? Please paste the URL (e.g.
> `https://github.com/owner/repo/issues/42`).

Once you have it, fetch the issue with:

```bash
gh issue view <NUMBER> --repo <OWNER>/<REPO>
```

Extract:
- Issue title
- Body (description, bullet points, AC if any)
- Labels (they often hint at the affected app: `pro-iq`, `anglers-log`, etc.)
- Milestone / project column (signals priority / release context)

---

## Step 2 — Identify the affected project

This monorepo contains multiple Flutter sub-projects. Determine which one the
issue targets from the repo name, labels, or issue body. Common sub-projects:

| Sub-project | Root dir |
|---|---|
| activity-log | `activity-log/mobile/` |
| anglers-log | `anglers-log/` |
| pro-iq | `pro-iq/` |
| adair-flutter-lib | `adair-flutter-lib/` |

If it's ambiguous, ask the user before exploring.

---

## Step 3 — Explore the codebase

Use the **Explore** subagent (or targeted `find`/`grep` calls) to gather
everything needed to fill the template accurately. You are looking for:

1. **Relevant files** — models, pages, widgets, services, managers, wrappers
   that the feature will touch or that provide the best reference.
2. **Existing patterns to reuse** — similar features already implemented (e.g.
   a boolean flag already filtered from stats, an existing dialog or checkbox
   pattern, a matching DB migration).
3. **Dependencies already in `pubspec.yaml`** — list only what's relevant to
   this feature (state management, DB layer, routing, Firebase, etc.).
4. **Data layer** — how data is stored (SQLite, Firestore, proto, plain model)
   and what migrations / serialization changes are needed.
5. **Reference examples** — the single most similar existing feature or file
   that a developer should read first.

Keep the exploration focused. Two or three targeted searches are usually enough.

---

## Step 4 — Fill out the template

Produce the completed template as rendered Markdown (no fenced wrapper). Do
not add commentary before or after it unless you have a specific question or
caveat — the output should be clean and copy-pasteable directly into a notes
app (e.g. Obsidian).

Use this exact template structure:

```
Implement [FEATURE NAME] in the Flutter app.

## Context
* **App:** [App name — one sentence describing what it does]
* **Relevant files:** [List key files — widgets, models, services, managers]
* **Dependencies available:** [Only those relevant to this feature]

## Requirements
* [Concrete requirement derived from the issue. One bullet per distinct behaviour.]
* [...]

## Technical implementation details
* [How to implement it — specific classes, methods, patterns, DB migrations,
   field names. Reference the existing pattern it should mirror where one exists.]
* [...]

## Acceptance criteria
- [ ] [Testable, specific. Mirrors the issue's AC if provided, expanded where
       the issue was vague.]
- [ ] [...]

## Do NOT
* Add new packages without flagging it first.
* Add or write unit tests.

## Reference examples
* Similar feature for reference: `lib/[path/to/similar_feature.dart]`
* [Add more only if genuinely useful — omit this section if nothing relevant exists.]

## Output expected
1. Implementation files (create or modify as needed).
2. A list of agents and skills you will or did utilize.
3. Brief summary of what was changed and why.
4. Any identified gaps in implementation or new coding/UX inconsistencies.
```

### Filling-in guidelines

**Feature name** — derive from the issue title; keep it short and imperative
(e.g. "Activity Archiving", "Session Notes", "Dark Mode Toggle").

**Requirements** — translate the issue body + AC into concrete, unambiguous
bullets. If the issue says "hide from stats", spell out *what* "stats" means
in this codebase (which queries, which pages).

**Technical implementation details** — this is the most valuable section. Name
the exact files, classes, and methods that need to change. If there's an
existing pattern to mirror (e.g. `isBanked` on `Session` for a new boolean
filter), name it explicitly with the file path.

**Acceptance criteria** — use the issue's AC verbatim when it exists, then
expand with anything the issue implied but didn't state. Each item must be
independently testable.

**Reference examples** — point to the single most analogous existing
implementation in the codebase. If nothing is close, omit the section.

---

## Step 5 — Caveats

After the template block, add a brief "Notes" section (outside the block) if
any of the following apply:

- A new pub package is likely needed — flag it and suggest candidates.
- The issue's scope is ambiguous in a way that could affect implementation
  significantly — call it out and ask the user to clarify before handing off.
- The issue touches shared library code (`adair-flutter-lib`) in addition to
  the app — mention this so the implementer knows to update both.
- The feature requires a database migration or breaking serialization change —
  flag it so it doesn't get overlooked.
