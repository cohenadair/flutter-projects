---
name: release-testing-checklist
description: >
  Compiles a manual QA checklist covering everything changed since a Flutter
  sub-project's last release, and saves it as a note in the user's Obsidian
  vault (Notes/Dev/<project>/Testing Checklists/v<version>.md). Use when the
  user says things like "create a release testing checklist", "release
  testing checklist", "QA checklist for the next release", or asks to do "the
  same thing we did for Activity Log" / "the same thing we did last time" for
  release testing.
---

# Release Testing Checklist Skill

Turns the commit range since a sub-project's last tagged release into an
Obsidian note the user can manually work through and check off, device by
device. It does **not** create a GitHub issue unless the user asks for one
afterwards (see Step 7). Reference examples this skill was built from (older
runs, posted as GitHub issues):
[anglers-log#1136](https://github.com/cohenadair/anglers-log/issues/1136) and
[activity-log#141](https://github.com/cohenadair/activity-log/issues/141).

---

## Terminology

| Term | Meaning |
|---|---|
| **sub-project** | The Flutter app being tested (e.g. `anglers-log`, `pro-iq`, `activity-log`) |
| **sub-project dir** | Local path, e.g. `/Users/cohen/Documents/flutter-projects/anglers-log` |
| **`{version}`** | The **upcoming** release version the checklist is titled for, e.g. `2.7.19` — this is one version ahead of the last tag, not the tag itself |
| **platform** | An OS/target the sub-project ships to (`iOS`, `Android`, `macOS`, ...) — see the platform reference table below |

---

## Platform reference table

The platforms a sub-project ships to, used by the sub-list rule in Step 4.
Keep this updated as projects add/drop platforms.

The **Obsidian folder** column is the project's folder under
`/Users/cohen/Library/Mobile Documents/iCloud~md~obsidian/Documents/Notes/Dev/`
(see Step 5).

| Sub-project | Platforms | Obsidian folder |
|---|---|---|
| Activity Log | iOS, Android | `Activity Log` |
| Anglers' Log | iOS, Android | `Anglers' Log` |
| Pro IQ | iOS, Android, macOS | `Freelance/Pro IQ` |
| Tapd | iOS, Android | `Tapd` |

If the sub-project isn't in this table, ask the user which platforms it
ships to and which Obsidian folder it uses, then add a row here so future
runs don't have to ask again.

---

## Step 1 — Determine sub-project, repo, target version, and platforms

1. Ask which sub-project if not already clear from context.
2. **Repo owner is per-project, not always `cohenadair`.** Check
   `git -C <sub-project dir> remote -v` before running any `gh` command — e.g.
   `pro-iq` lives under `Pro-IQ-Inc/pro-iq`.
3. Ask the user for `{version}` (it names the note, `v{version}.md`) if they
   haven't already given one.
   This is typically the next unreleased version, even if `pubspec.yaml`
   hasn't been bumped yet — don't assume it must match the current
   `pubspec.yaml` version.
4. Look up the sub-project's platforms in the **platform reference table**
   above. If it's missing, ask the user and add a row to this file before
   continuing (see that section for how). These platforms are what Step 4's
   sub-list rule checks against for the rest of the run.

---

## Step 2 — Find the commit range since the last release

```bash
cd <sub-project dir>
git fetch origin --tags -q
git tag --sort=-version:refname | grep '^v' | head -1   # last release tag
git log v{prev-version}..HEAD --oneline                  # commits in scope
git diff v{prev-version}..HEAD --stat                     # files touched, for a first pass at scope
```

If `pubspec.yaml`'s version hasn't bumped since the last tag, say so — it
confirms none of this range has shipped yet, which is worth surfacing to the
user (as opposed to a checklist for a release already partially in the
field).

---

## Step 3 — Read every commit's actual diff, not just its message

**This is the step that makes the checklist useful — do not skip it.** A
list of commit subject lines makes a changelog, not a test plan. For each
commit in range:

```bash
git show <sha>
```

Read the real diff to understand:
- What user-facing behavior actually changed (not just which file/class).
- What the *previous* buggy/missing behavior was, if it's a fix — the
  checklist item should test the specific failure mode that was fixed, not
  just "feature X still works."
- Whether the change is platform-specific (an iOS-only API, an Android-only
  permission flow, a macOS-only menu bar behavior, etc.) or shared code that
  every one of the project's platforms (per the platform reference table)
  exercises.
- Related test file diffs in the same commit — they often describe the exact
  scenario worth manually verifying (e.g. a new `testWidgets` case for a
  denied-permission path is a strong hint for a checklist item).

Group commits that touch the same feature/flow together mentally before
writing items — several small commits often collapse into one coherent
checklist section (e.g. three commits touching the same permission utility
become one "Location Permissions" section, not three disconnected items).

---

## Step 4 — Write the checklist

Structure, matching the reference issues:

```markdown
# {Project Display Name} Release Testing Checklist (since v{prev-version})

## {Feature Area}
- [ ] {Action to take} — {expected result}.
- [ ] {Action to take} — {expected result}.

## {Another Feature Area}
...

## General Regression
- [ ] {End-to-end flow that touches multiple changed areas}.
```

Guidelines for each item:
- **Phrase as action → expected result**, e.g. "Deny the camera permission
  prompt — shows the specific 'Permission denied...' message, no crash,"
  not a restatement of the commit message.
- For a bug fix, test the **specific failure mode**, not just the happy path
  (e.g. if the fix was "don't crash on double-tap," the item is the
  double-tap, not just "tap once and it works").
- Group into `##` sections by feature/page area, not by commit.
- End with a **General Regression** section: 3–5 broader end-to-end flows
  that exercise multiple changed areas together, plus fresh-install and
  upgrade-path checks.

### Platform sub-list rule

Use the sub-project's platform list from the **platform reference table**
(Step 1.4) — this is not hardcoded to iOS/Android. Pro IQ, for example, has
three: iOS, Android, macOS.

Add a sub-list with one item per platform the sub-project ships to, under a
checklist item, **only when the behavior goes through native platform code
and is testable on all of those platforms**: in-app purchases, ads, OS
permissions, app lifecycle (background/foreground), connectivity checks,
device/package info plugins, store install/upgrade, Firebase SDKs, and native
build/config changes. Shared Dart logic and Flutter UI (game rules, layout,
stats, form validation, and so on) behave identically on every platform, so
those items get **no** sub-list, even when they have UI. Test them once, on
any platform:

```markdown
- [ ] Deny the camera permission prompt — shows the specific error message, no crash.
  - [ ] iOS
  - [ ] Android
```

```markdown
- [ ] Open the settings window — new toggle appears and persists after restart.
  - [ ] iOS
  - [ ] Android
  - [ ] macOS
```

- If the change/behavior applies to **some but not all** of the project's
  platforms, do not add a sub-list — annotate inline instead, matching the
  reference issues' style: `(iOS only — no Android equivalent)` or `(Android
  only — fix was in the native notification layout)`. Name the specific
  platform(s) the item actually applies to.
- If the item is platform-agnostic pure logic (e.g. a stats calculation, a
  date-range bug) with no UI/OS-permission surface, leave it with no
  sub-list and no annotation at all.
- Never add a sub-list with items other than the exact platform names from
  the reference table, and never a partial subset of the project's
  platforms — a partial list belongs as an inline annotation instead.

---

## Step 5 — Save the checklist to Obsidian

Write the checklist to the user's Obsidian vault — a local file, so no
confirmation is needed before writing it:

```
/Users/cohen/Library/Mobile Documents/iCloud~md~obsidian/Documents/Notes/Dev/{Obsidian folder}/Testing Checklists/v{version}.md
```

- `{Obsidian folder}` comes from the **platform reference table**, e.g.
  `Anglers' Log` or `Freelance/Pro IQ`.
- The filename is the version with a `v` prefix: `v2.7.19.md`.
- Create `Testing Checklists/` if it doesn't exist yet (`mkdir -p`). The path
  has spaces and apostrophes, so quote it in every shell command.
- **If `v{version}.md` already exists, don't overwrite it** — it may already
  have items checked off. Show the user what's there and ask whether to
  replace it, merge new items into it, or stop.
- The note body is the Step 4 markdown as-is; Obsidian renders `- [ ]` and
  nested `  - [ ]` as checkable boxes.

Then give the user the full path, and a short summary of the sections and
item count. Revise the note in place if they ask for changes.

---

## Step 6 — Closing the loop

The user works through the checklist themselves in Obsidian (checking items
off, one device/platform at a time). Don't check off items, rename, move, or
delete the note on the user's behalf.

---

## Step 7 — GitHub issue (only if asked)

Don't create a GitHub issue as part of this skill. If the user later asks to
post the checklist as an issue, that's publishing public content: show the
full body and get explicit confirmation first, then:

```bash
gh issue create --repo <owner>/<repo> \
  --title "v{version} Release testing checklist" \
  --body-file "<path to the Obsidian note>"
```

The repo owner is per-project (Step 1.2). Report the issue URL back to the
user.
