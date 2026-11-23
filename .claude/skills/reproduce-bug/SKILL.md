---
name: reproduce-bug
description: >
  Reproduces a bug in one of this monorepo's Flutter apps on an iOS simulator
  or Android emulator, and writes definitive, verified reproduction steps
  with the exact seed data needed — or flags clearly when the bug can't be
  verified on a simulator/emulator, and why. Given an existing bug-fix PR, it
  reproduces the bug without the PR's changes and confirms the PR fixes it.
  Runs on its own or as a step of `ship-ticket` (which also reuses it to
  confirm a fix). Use when the user says things like "reproduce this bug",
  "reproduce issue #42", "can you repro this", "verify this bug report",
  "write repro steps for <issue URL>", "is this bug real", "does PR #12 fix
  the bug", "verify this fix PR", or invokes /reproduce-bug directly.
---

# Reproduce bug

Turns a bug report (a GitHub issue, or a description) into reproduction
steps that were actually performed on a simulator or emulator, starting
from a fresh install with a known, minimal set of seed data. The output is
only "verified" if every step was performed exactly as written and the bug
was seen. Anything less is labeled as such — never present plausible-looking
steps as verified.

**Running the app is the point of this skill.** Never kill the user's own
`flutter run` sessions (ask them to stop one if it's on the device you
need), and run only **one simulator or emulator at a time** ([devices.md](devices.md)).

Don't change app code in this skill. Temporary debug logging is fine only in
a throwaway worktree, and must be removed before reporting.

## Inputs

- **The bug**: a GitHub issue URL or number (with repo), a free-text
  description, or a **PR** that fixes it (see **PR mode** below). If none
  was given, ask for it.
- **Code to run** (optional): a worktree path. `ship-ticket` passes its
  worktree; when run on its own, Step 3 creates one at the default branch's
  remote tip.
- **Platform** (optional): `ios`, `android`, or both. Otherwise Step 2
  decides.

When `ship-ticket` invokes this skill to confirm a fix, it passes the report
from the earlier run. Re-run that report's exact steps and seed against the
fixed worktree. Don't re-derive them, so before and after are comparable.

## PR mode

Given a PR, answer two questions: does the bug reproduce without the PR's
changes, and is it gone with them?

```bash
gh pr view <n> --repo <owner>/<repo> --comments --json \
  title,body,state,baseRefName,baseRefOid,headRefOid,closingIssuesReferences,files
gh pr diff <n> --repo <owner>/<repo>
```

1. **The bug**: read the issues the PR closes (`closingIssuesReferences`,
   or `#n` references in the body) as in Step 1, plus the PR's own
   description and diff. The diff often shows exactly what triggers the
   bug. If the PR is plainly a feature rather than a fix, say so and offer
   `verify-feature` instead.
2. **Existing repro steps**: if the PR body or linked issue already has
   reproduction steps (e.g. from `ship-ticket` or `crashlytics-triage`),
   replay those as written instead of deriving new ones. Report whether
   they hold, and correct them if they don't.
3. **Two worktrees**, prepared as in Step 3:
   ```bash
   git -C <repo-dir> fetch origin <baseRefName> "pull/<n>/head"
   BASE=$(git -C <repo-dir> merge-base <baseRefOid> <headRefOid>)
   git -C <repo-dir> worktree add --detach ../<repo-name>-pr-<n>-before "$BASE"
   git -C <repo-dir> worktree add --detach ../<repo-name>-pr-<n>-after <headRefOid>
   ```
   The merge base is the base branch as the PR author saw it, so the only
   difference between the two is the PR. `pull/<n>/head` works for PRs
   from forks too.
4. **Before**: Steps 2–5 in the `before` worktree. If it's not reproduced
   there, stop and report that. Testing the fix proves nothing if the bug
   never appears.
5. **After**: replay the exact same seed and steps, on the same device(s),
   in the `after` worktree.

The report (Step 6) then has two statuses: **Before** (✅ Reproduced / ❌
Not reproduced / ⚠️ Can't verify) and **After** (✅ Fixed / ❌ Still
reproduces / ⚠️ Can't verify). It also says whether the PR's own repro
steps held up. Post it on the PR (Step 6) without asking: the user wants
PR-mode results on the PR. If the PR's own manual-test steps wouldn't show
the bug, also replace them in its description with the verified steps.
Touch nothing else in the description.

## Step 1 — Read the bug

```bash
gh issue view <n> --repo <owner>/<repo> --comments
```

Get the expected vs. actual behavior, any steps the reporter gave, the
platform/OS/app version, screenshots, and labels (`ios`, `android`, `crash`,
`bug-ui`, `regression`, `pro`). Map the repo to its sub-project:

| Repo | App root | Data layer |
|---|---|---|
| `cohenadair/anglers-log` | `anglers-log/mobile/` | SQLite (protobuf rows) |
| `cohenadair/activity-log` | `activity-log/mobile/` | SQLite + shared_preferences |
| `cohenadair/tapd` | `tapd/mobile/` | shared_preferences (+ RevenueCat) |
| `Pro-IQ-Inc/pro-iq` | `pro-iq/` | Firestore, Auth, Storage, Functions |
| `cohenadair/adair-flutter-lib` | the app it was seen in | — |

Then read the code the bug points at, and work out a hypothesis: the
specific data and action sequence that should trigger it. That is what Step
5 tries to make happen. A reporter's steps are a starting point, not the
answer. Shrink them to the minimum that still triggers the bug.

## Step 2 — Decide whether it can be verified, and on what

Pick the platform: the one the issue names. If the issue doesn't name one,
use iOS. The simulator runs at native speed on Apple Silicon, while the
Android emulator is several times slower on this Mac (16 GB of RAM, usually
swapping) and much less reliable. Use both when the code path differs per
platform (`Platform.is*`, `IoWrapper.get.is*`, plugins with native code,
`ios/` or `android/` config). Use Android alone only when the bug is
Android-specific.

Some bugs can't be verified on a simulator or emulator. Find out before
spending time on it. Common reasons:

- Needs a physical device: camera, real GPS movement, Bluetooth, background
  execution and app suspension timing, push notification delivery,
  performance on old hardware, a specific device model.
- Needs real accounts or production data: a real user's Firestore data,
  production-only Firebase config, App Store/Play receipts, real RevenueCat
  purchases or subscription states (test values for the user's own app are
  fine; real credentials never are).
- Needs an OS version or locale/region setup that no available runtime
  provides.
- Depends on an external service's state you can't control.

If it can't be verified, don't stop. Go to Step 6 and report **Can't
verify**, with the reason and best-effort steps marked unverified. If only
part can be done (e.g. the data setup works, but the trigger needs a real
purchase), verify that part and say exactly where verification ends.

## Step 3 — Code to run

If a worktree path was passed in, use it. Otherwise create a throwaway one
at the remote tip of the default branch, so the repro reflects what's
shipped and not the user's uncommitted work:

```bash
DEFAULT=$(gh repo view <owner>/<repo> --json defaultBranchRef -q .defaultBranchRef.name)
git -C <repo-dir> fetch origin "$DEFAULT"
git -C <repo-dir> worktree add --detach ../<repo-name>-repro-<n> "origin/$DEFAULT"
```

Then prepare it as [worktree-setup.md](worktree-setup.md) describes (gitignored
config, no release keystores, `flutter pub get`, generators).

Remove a worktree this step created at the end (Step 7).

## Step 4 — Device

Follow [devices.md](devices.md): use the user's existing devices, only one
simulator or emulator at a time, iOS access needs the user's OK, the
Android memory check, a fresh install every time, and pro-iq against local
emulators only.

## Step 5 — Seed, then reproduce

**Seed data** is the exact, minimal set of records the bug needs, with
concrete values (names, dates, numbers, settings, toggles). It's always
written out as a list or table so a human can recreate it, plus a
machine-loadable form where the project supports one:

| Project | Machine-loadable form |
|---|---|
| anglers-log | Entities in `seed.json` format (proto3 JSON with keys, relative timestamps, measurements — see `anglers-log/screenshots/capture/README.md` → Seed format). |
| pro-iq | Firestore documents (path + fields, matching the protos) and Auth users, written to the local emulator via its REST API or the emulator UI. |
| activity-log, tapd | None. Use in-app steps only. |

**Never seed through the Firebase MCP.** The Firebase plugin's
`mcp__plugin_firebase_firebase__firestore_*` tools talk to the **production**
project (`pro-iq`), not the local emulator. Write seed data only to the
emulator. The read-only tools (`firestore_get_document`,
`firestore_query_collection`, `firestore_list_collections`) are fine for
looking up the real shape of a production document a bug report mentions.
Copy that shape into the emulator seed with any personal data replaced.

Load the seed in a way the report can repeat exactly. Usually that means
entering it through the app's own UI from a fresh install. Seed steps are
part of the reproduction and must be verified like the rest. A
machine-loadable seed that wasn't actually loaded (or at least checked,
e.g. anglers-log's `build_seed.dart --check`) is labeled **not loaded** in
the report.

Drive the app as [devices.md](devices.md) → **Driving the app** describes:
screenshot after every step and check it (never chain steps blind), name
evidence screenshots `<before|after>-<n>-<what>.png`, watch the logs, and
use the per-app notes there (add a row when you learn something about an
app).

If the hypothesis doesn't trigger the bug, revise it from what you saw
(read the code again, vary the data) and try again. Stop after a few
genuine attempts and report **Not reproduced** with what was tried. Don't
keep varying things until something unrelated breaks.

**If the reporter's steps don't reproduce it**, ask what else could be
refreshing the screen and hiding the bug, before concluding it's gone. A
keyboard opening or closing changes `MediaQuery` and rebuilds everything
that depends on it. Switching tabs, an unrelated manager firing, or a
`setState` higher up can do the same. Look for a path that changes the same
data without those side effects (e.g. deleting instead of renaming, so no
keyboard is involved). Say in the report that the reporter's steps don't
show the bug and why. In PR mode, also say whether the PR's own manual-test
steps would pass with or without the fix.

Once it reproduces, **replay the final steps once more from a fresh
install** (uninstall, rerun, re-seed) to confirm the written steps alone are
enough. Only that replay makes it verified.

## Step 6 — Report

Write the report to the scratchpad as `repro-<repo-name>-<n>.md` (or
`repro-<slug>.md` without an issue), and show it in chat. Lead with exactly
one status:

- **✅ Reproduced**: verified on `<device>, <OS>`, at `<commit>`.
- **❌ Not reproduced**: the steps were performed and the bug didn't appear.
  Include what was tried and what to ask the reporter.
- **⚠️ Can't verify**: why (Step 2). The steps below are best-effort and
  **unverified**. If part was verified, say where verification ends.

Then:

```markdown
## Environment
- App: <app> @ <commit> (<branch or "origin/<default>">)
- Device: <iPhone 17 Pro simulator, iOS 26.5> / <Pixel_9_Pro emulator, Android 17>
- Backend: <local emulators> (pro-iq only)

## Seed data
<table or list of every record and setting, with concrete values>

<details><summary>Machine-loadable seed</summary>

<seed.json fragment or Firestore documents, when the project has a form>
</details>

## Steps
1. Fresh install, then <first action>.
2. ...

**Expected:** ...
**Actual:** ... ![actual](<image URL>)

## Evidence
<log lines / exception and stack; other images inline>

## Reporter's / PR's steps
<only if they don't show the bug: why (Step 5), and in PR mode whether the
PR's manual-test steps would pass with or without the fix>

## Likely cause
<file:line and one or two sentences, if the code makes it clear; otherwise omit>
```

Make one side-by-side image of the key before/after (or expected/actual)
screens, e.g. `magick a.png b.png -resize 35% +append -crop
<width>x<height>+0+0 +repage before-vs-after.png`.

**Everything goes on GitHub; nothing stays on the computer.** The report
and its images belong in the PR (or issue), and Step 7 deletes the local
copies. Publish the images with `scripts/publish-media.sh <repo-dir>
<owner>/<repo> pr-<n> <files>` (or `issue-<n>`). It pushes them to the
repo's orphan `pr-media` branch and prints a URL for each. In the report,
show the side-by-side image at the top and the other evidence images inline
(`![before, stale list](<url>)`), never local paths. Keep it to the images
that show something: seeded state, the bug, the fix, and anything the text
refers to.

- **PR mode:** post the report as a PR comment (`gh pr comment <n> --repo
  <owner>/<repo> --body-file <report>`) without asking, then fix the PR's
  manual-test steps if needed (see **PR mode**). Link the comment in chat.
- **Run on its own from an issue:** ask whether to post it on the issue.
  That's outward-facing, so publish the images and post only on a yes.
- **Called by `ship-ticket`:** publish the images under `issue-<n>` and
  return the report (with image URLs) and status. `ship-ticket` puts it in
  its PR body. Don't post anything else.

Also show the report in chat, and send the side-by-side image with
`SendUserFile` so the user sees it from another device.

## Step 7 — Clean up

- Stop the `flutter run` process and, for pro-iq, the emulators this skill
  started.
- Shut down devices this skill booted (`adb emu kill`, `xcrun simctl
  shutdown <udid>`), after turning the emulator's animations back on. Leave
  devices that were already running. If you shut down one of the user's
  devices for this run, say which in the final message.
- Never create devices, so there are none to delete. If an earlier run
  left a device it created (e.g. `Repro iPhone`, `Repro_Phone`), delete it
  (`xcrun simctl delete`, `avdmanager delete avd`).
- Delete everything this run wrote locally: screenshots (evidence and
  `work/`), the report, the side-by-side image, and any helper scripts.
  The user doesn't want leftover data on their computer; what matters is
  on GitHub (Step 6). If nothing was posted (the user said no), the report
  in chat and the image sent with `SendUserFile` are the record. When
  called by `ship-ticket`, leave this to its Step 8.
- Remove worktrees this skill created (Step 3's `-repro-<n>`, or PR mode's
  `-pr-<n>-before` / `-pr-<n>-after`) with `git -C <repo-dir> worktree
  remove <path>`, after checking they have no changes you made on purpose.
  Never `--force` over uncommitted changes without looking.
