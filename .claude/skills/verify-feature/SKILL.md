---
name: verify-feature
description: >
  Writes and verifies testing instructions for a feature in one of this
  monorepo's Flutter apps: the seed data needed, step-by-step instructions
  performed on an iOS simulator or Android emulator, and whether the
  feature must be tested on more than one platform (e.g. it calls into
  native code). Anything that can't be verified on a simulator/emulator is
  flagged. Works on an existing PR, or as a step of `ship-ticket`. Use when
  the user says things like "verify this PR", "test PR #12", "write testing
  instructions for this PR", "how do I test this feature", "does this PR
  need testing on Android too", or invokes /verify-feature directly. For a
  bug-fix PR, use `reproduce-bug` instead.
---

# Verify feature

Produces testing instructions a reviewer can follow exactly, every step of
which was performed on a simulator or emulator, plus a reasoned call on
which platforms need testing. "Verified" means performed as written. Steps
that weren't performed are labeled as such.

The device rules are `reproduce-bug`'s, and so is the setup. Read its
Steps 3–5 before starting. They cover worktree prep (including Android
signing), using the user's existing devices with only one simulator or
emulator running at a time (iOS access, emulator memory check), fresh
installs, pro-iq on local
emulators only, `scripts/android.sh`, the never-chain-blind rule, the
screenshot naming, and the per-app notes. Prefer iOS when one platform is
enough. Running the app is the point of this skill. Never kill the user's
own `flutter run` sessions, and never change app code here.

Two device rules to keep in mind (details in `reproduce-bug` Step 4):

- **Always close the Android emulator before opening an iOS simulator, and
  vice versa**, and confirm it's gone (`adb devices` lists nothing; `xcrun
  simctl list devices booted` is empty) before booting the other.
- **If the Android emulator is too full to install the build**
  (`INSTALL_FAILED_INSUFFICIENT_STORAGE`), shut it down and boot it with
  `-wipe-data` without asking. Don't uninstall the user's other apps to
  make room.

## Inputs

- **A PR** (URL, or number with repo), or
- **From `ship-ticket`**: its worktree path and requirements file.

If neither was given, ask for the PR.

## Step 1 — What should the feature do?

**From `ship-ticket`:** the requirements file's requirements and
acceptance criteria, and the worktree's diff against the default branch.

**PR:**

```bash
gh pr view <n> --repo <owner>/<repo> --comments --json \
  title,body,state,baseRefName,baseRefOid,headRefOid,closingIssuesReferences,files
gh pr diff <n> --repo <owner>/<repo>
gh issue view <closing issue> --repo <owner>/<repo> --comments
```

Combine the linked issues (their acceptance criteria especially), the PR
description, and the diff into a list of behaviors to verify. The diff is
the source of truth for what was built. Where it differs from the issue,
verify what was built and note the gap. If the PR is plainly a bug fix,
say so and offer `reproduce-bug` instead.

If the PR already has testing instructions, perform those as written
first, and report which held. Then add any that are missing.

## Step 2 — Code to run

From `ship-ticket`, use its worktree. For a PR, create one at the PR's
head, then prepare it as in `reproduce-bug` Step 3:

```bash
git -C <repo-dir> fetch origin "pull/<n>/head"
git -C <repo-dir> worktree add --detach ../<repo-name>-pr-<n> <headRefOid>
```

## Step 3 — Which platforms?

Decide from the diff, including code the change newly calls. **Test on both
iOS and Android** when it touches any of:

- a plugin or pub package with native code (new or newly used), or a
  method/event channel;
- `ios/`, `android/`, or `macos/` files: `Info.plist`, entitlements,
  `AndroidManifest.xml`, Gradle or Xcode settings, permissions;
- platform branches (`Platform.is*`, `IoWrapper.get.is*`, a platform
  wrapper);
- OS integrations: notifications, in-app purchases, file/photo pickers,
  share sheets, camera, location, maps, deep links, widgets, background
  tasks, platform-adaptive widgets (`.adaptive`, Cupertino vs. Material).

Otherwise one platform is enough, because the change is pure Dart/Flutter
UI and logic. Record which items applied (or that none did). Check which
platforms the project ships (its `ios/`, `android/`, `macos/`, `web/`
folders). pro-iq also ships macOS and web: name them in the call when the
change affects them, but only iOS and Android are verified here.

## Step 4 — Seed data and steps

1. **Seed data**: the minimal records and settings that exercise the
   feature, with concrete values. Use the same format as `reproduce-bug`
   Step 5 (human-readable, plus a machine-loadable form where the project
   has one). Include edge cases worth seeing (empty state, long text, many
   items, a lapsed Pro user) when the feature changes how they behave.
2. **Steps**: from a fresh install, each action and what should be seen
   after it. Every behavior from Step 1 gets one or more steps.

## Step 5 — Perform them

On each platform from Step 3, from a fresh install: load the seed and
perform every step, taking a screenshot after each and checking it matches
what the step says should be seen. Never chain steps blind (`reproduce-bug`
Step 5). Save evidence screenshots as `<platform>-<n>-<what>.png` and
working shots in `work/`, and watch the logs for exceptions and `_log.e`.

- **A step doesn't match**: the feature misbehaves, or an instruction is
  wrong. Re-check the instruction against the code. If the instruction was
  wrong, fix it and redo the step. If the feature is wrong, record it as a
  failure with a screenshot and continue with the steps that don't depend
  on it. Don't fix app code.
- **A step can't be done on a simulator or emulator** (`reproduce-bug` Step
  2's list): verify everything else, and mark that step **⚠️ Unverified**
  with the reason.

When everything is done, replay the final instructions once from a fresh
install, so the written steps alone are known to work.

## Step 6 — Report

Write it to the scratchpad as `verify-<repo-name>-<pr or issue>.md`, and
show it in chat. Lead with one status:

- **✅ Verified**: every step performed and passed on `<devices>`.
- **❌ Failures**: which steps failed and how (screenshots).
- **⚠️ Partly verified**: which steps couldn't be verified, and why.

```markdown
## Environment
- App: <app> @ <commit>
- Devices: <iPhone 17 Pro simulator, iOS 26.5>, <Pixel_9_Pro emulator, Android 17>
- Backend: <local emulators> (pro-iq only)

## Platforms
<Test on iOS and Android, because <items from Step 3> / One platform is enough: pure Dart/Flutter>

## Seed data
<table or list with concrete values>

<details><summary>Machine-loadable seed</summary>
...
</details>

## Steps
1. Fresh install, then ... → <what should be seen> ✅
2. ... → ... ⚠️ Unverified: <why>

## Failures
<only if any: step, expected vs. actual, image>

## Gaps
<only if any: issue asks for X, the PR does Y; existing PR instructions that didn't hold>
```

**Everything goes on GitHub; nothing stays on the computer.** Publish the
evidence images with `reproduce-bug`'s `scripts/publish-media.sh` (folder
`pr-<n>`, or `issue-<n>` from `ship-ticket`) and show them inline in the
report by URL, never by local path. Failures always get an image.

**PR:** post the report as a PR comment (`gh pr comment`) without asking,
and link it in chat. If the PR's own testing instructions didn't hold
(Gaps), replace them in its description with the verified steps, and touch
nothing else there. **From `ship-ticket`:** return the report (with image
URLs) and status. `ship-ticket` puts it in its PR body.

Also show the report in chat, and send the key image with `SendUserFile`.

## Step 7 — Clean up

As in `reproduce-bug` Step 7: stop `flutter run` and any pro-iq emulators
this skill started, shut down devices it booted, delete every local file
this run wrote (screenshots, report, scripts), and remove the PR worktree it created (`git -C <repo-dir>
worktree remove ../<repo-name>-pr-<n>`). Leave `ship-ticket`'s worktree
alone.
