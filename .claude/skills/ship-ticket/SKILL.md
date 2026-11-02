---
name: ship-ticket
description: >
  Implements a GitHub issue end to end in its own git worktree and opens a
  pull request. Bugs are reproduced first on an iOS simulator or Android
  emulator (via the `reproduce-bug` skill), fixed, and confirmed fixed on
  the same steps. Features get seed data, verified testing instructions,
  and a call on whether they must be tested on more than one platform (via
  the `verify-feature` skill). For an existing PR, use `reproduce-bug` or
  `verify-feature` directly.
  Use when the user says things like "ship issue #42", "implement this
  issue and open a PR", "fix <issue URL>", "work on ticket 42", "take this
  issue to a PR", or invokes /ship-ticket directly. Also use (Step 9 only)
  when the user says to merge a verified ticket or PR, e.g. "merge it",
  "merge PR 14", "ship it". For a requirements doc without implementing,
  use `github-requirements-generation` instead.
---

# Ship ticket

One GitHub issue → one worktree → one PR (two if `adair-flutter-lib` must
change too). Invoking this skill authorizes committing and pushing the
issue's branch and opening its PR (Step 7). It doesn't authorize anything
beyond that.

**Running the app is part of this skill.** Never kill the user's own
`flutter run` sessions, though; ask them to stop one if it's in the way.

## Step 1 — Read the issue

```bash
gh issue view <n> --repo <owner>/<repo> --comments
```

If no issue was given, ask for the URL. Map the repo to its sub-project
using the table in `reproduce-bug` Step 1.

Check that nobody's already on it: `gh pr list --repo <owner>/<repo>
--state open --search "<n> in:title,body"` and `git -C <repo-dir> ls-remote
--heads origin issue-<n>`. If there's a PR or branch, stop and ask.

**Bug or feature?** It's a bug if it has a `bug`, `bug-ui`, `crash`, or
`regression` label, or if the body describes existing behavior that's
wrong. Everything else (features, enhancements, refactors, UX changes) is a
feature. Say which you picked and why in one line. Ask only if it's
genuinely both (e.g. "this is broken, and also add X"). Then the bug part
gets Step 3's bug path and the rest the feature path.

## Step 2 — Worktree

```bash
DEFAULT=$(gh repo view <owner>/<repo> --json defaultBranchRef -q .defaultBranchRef.name)
git -C <repo-dir> fetch origin "$DEFAULT"
git -C <repo-dir> worktree add ../<repo-name>-issue-<n> -b issue-<n> "origin/$DEFAULT"
```

The worktree is a sibling of the submodule inside the monorepo root, so the
apps' relative `adair-flutter-lib` paths still resolve. Prepare it exactly
as `reproduce-bug` Step 3 describes (copy gitignored config, never a
`keystore.properties` or release keystore, `flutter pub get`, generators
if needed). Do all remaining work, including tests and
`dart format`, in the worktree, never in the main checkout.

**If `adair-flutter-lib` must change too**, create a second worktree for it
the same way (`../adair-flutter-lib-issue-<n>`, branch `issue-<n>` from
lib's default branch). Point the app worktree at it with a
`pubspec_overrides.yaml` in the app root:

```yaml
dependency_overrides:
  adair_flutter_lib:
    path: <relative path to ../adair-flutter-lib-issue-<n>>
```

Never commit that file. Delete it before committing the app (Step 7).

## Step 3 — Understand before changing

**Bug:** run the `reproduce-bug` skill with this worktree (it's still at the
default branch tip, so it shows the bug as shipped). Keep its report: the PR
uses it, and Step 6 replays it.

- **✅ Reproduced**: continue.
- **❌ Not reproduced**: stop and show the report. Ask whether to fix from
  the code alone, ask the reporter for more, or drop it. Don't guess-fix.
- **⚠️ Can't verify**: continue if the cause is clear from the code, and
  carry the flag into the PR. Otherwise stop and ask.

**Feature:** work out the requirements with the `github-requirements-generation`
skill's Steps 2, 3, and 5 (project, exploration, template). Write the result
to the scratchpad as `requirements-<repo-name>-<n>.md` instead of asking
for a path, and ignore its "Do NOT add or write unit tests" line, since
this skill writes tests. If its caveats find ambiguous scope, a new
package, or a migration or breaking serialization change, stop and ask
before implementing.

## Step 4 — Implement

- List possible side effects before changing code (root `CLAUDE.md`).
- Follow `flutter-coding-standards` for widgets and logic, and
  `flutter-test` for tests.
- **Bugs**: add a test that reproduces the bug. Confirm it fails for the
  right reason: temporarily revert the fix with `Edit` (never `git stash`),
  check that the test fails with the same symptom the repro showed, then
  reapply the fix.
- New ARB strings get real translations in every required locale in the
  same change.

## Step 5 — Review

Run the `adair-code-audit` skill in pre-commit mode. Its Step 1 scans the
main checkout's submodules, so give it the scope explicitly: the
uncommitted changes in this worktree (and the lib worktree, if any). Its
own steps cover format, tests, coverage, and ARB coverage, plus a findings
review with the user.

## Step 6 — Verify on a device

Both skills below use `reproduce-bug`'s device setup (the user's existing
devices, one simulator or emulator at a time, fresh install, pro-iq on
local emulators only), run from this worktree.

**Bug:** run `reproduce-bug` again in confirm mode, passing the Step 3
report. It replays the same seed and steps on the same platform(s). Result:

- **Verified fixed**: the bug no longer appears, and the screen now shows
  the expected behavior. Screenshot it.
- **Still reproduces**: go back to Step 4.
- **Can't verify**: carried over from Step 3. Say so; don't upgrade it.

**Feature:** run the `verify-feature` skill, passing this worktree and Step
3's requirements file. It decides which platforms need testing, writes the
seed data and testing instructions, and performs them on the device(s).
Result:

- **✅ Verified**: continue.
- **❌ Failures**: go back to Step 4.
- **⚠️ Partly verified**: continue, and flag the unverified steps in the PR
  and the final report.

Clean up per `reproduce-bug` Step 7 (stop `flutter run`, the pro-iq
emulators, and devices this run booted). Don't remove this worktree yet.

## Step 7 — Commit, push, PR

Pre-authorized by invoking this skill, for the `issue-<n>` branch only:
commit, push, and `gh pr create`, plus pushing evidence images to the
`pr-media` branch. Never push the default branch, never
force-push, never pass `--no-verify`, and never update the monorepo root's
submodule pointer. Never merge here: merging happens only in Step 9, when
the user says to.

1. Delete any `pubspec_overrides.yaml` from Step 2, and make sure only
   intended files are staged (`git status` in the worktree).
2. If lib changed, commit and open the lib PR first, so the app PR can link
   to it. The app PR then notes that it depends on that PR merging first.
3. Commit with a message that says what changed and why. End it with the
   attribution line from the session's instructions.
4. `git push -u origin issue-<n>`, then:
   ```bash
   gh pr create --repo <owner>/<repo> --base "$DEFAULT" --head issue-<n> \
     --title "<imperative summary>" --body-file <scratchpad>/pr-<n>.md
   ```
   Add `--label ios` / `--label android` if the change is specific to one
   platform and the label exists in the repo (`gh label list`).

PR body:

```markdown
Closes #<n>

## Summary
<what changed and why, a few bullets>

## Reproduction            ← bugs
<status line from reproduce-bug; Environment, Seed data, Steps, Expected/Actual>

## Root cause              ← bugs
<the mechanism, not a restatement of the symptom>

## Fix verification        ← bugs
<Verified fixed on <device, OS> by replaying the steps above / ⚠️ Can't verify: why>

## Testing instructions    ← features
<status line from verify-feature; Environment, Platforms, Seed data, Steps,
and Gaps if any>
**Verified on:** <device, OS> (<each platform verified>)

## Test plan
- [x] Unit/widget tests added: <files>
- [x] adair-code-audit pre-commit checklist
- [ ] <anything unverified, flagged>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

The Reproduction / Fix verification / Testing instructions sections carry
the full reports from `reproduce-bug` and `verify-feature`, with their
images inline. Publish the fix-verification images the same way
(`reproduce-bug`'s `scripts/publish-media.sh`, folder `issue-<n>`), and
put a before/after side-by-side image at the top of Fix verification.
Pushing to the `pr-media` branch is pre-authorized along with the issue
branch.

After the PR is open, bind it with the PR tools (`get_status`, then
`bind_pr` if needed) and read its CI per the session's instructions. Don't
poll it yourself.

## Step 8 — Clean up and report

Remove the worktree(s) after checking `git status` is clean (`git -C
<repo-dir> worktree remove ../<repo-name>-issue-<n>`). The branch stays on
the remote. If review asks for changes later, recreate the worktree with
`git -C <repo-dir> worktree add ../<repo-name>-issue-<n> issue-<n>`.

Report in chat:

- PR URL (and lib PR URL).
- Bug: reproduction status → fix verification status, with devices.
- Feature: the platform call and why, and what was verified on which
  device.
- Every **⚠️** flag, and anything `adair-code-audit` left open.

Then delete every local file this run wrote (screenshots, reports,
requirements, PR body). Everything that matters is in the PR.

## Step 9 — Merge (only when the user says to)

Run this when the user says to merge a verified ticket or PR, in this
session or a later one (e.g. "merge it" after `reproduce-bug` or
`verify-feature` posted its report). That instruction authorizes
everything below for that PR only.

1. **Check it's ready.** `gh pr view <n> --repo <owner>/<repo> --json
   state,mergeable,mergeStateStatus,statusCheckRollup,headRefName,headRefOid`.
   Stop and ask if it's not open and `MERGEABLE`, if a check failed, or if
   its verification is ❌ (still reproduces, or failures). ⚠️ flags don't
   block, but name them in the report.
2. **Lib first.** If an app PR depends on a lib PR, merge the lib PR first
   (steps 3–4), then the app PR.
3. **Squash merge and delete the branch:**
   ```bash
   gh pr merge <n> --repo <owner>/<repo> --squash --delete-branch
   ```
   Never the default branch or `pr-media`. Confirm with `gh pr view <n>
   --json state,mergeCommit` and `git ls-remote --heads origin <branch>`
   (empty). If `--delete-branch` couldn't delete the remote branch, delete
   it with `git push origin --delete <branch>`.
4. **Pull the local repos.** For each repo the merged PR(s) touched, in
   the main checkout (`cd` into each repo in the same command, never
   relying on an earlier `cd`):
   ```bash
   cd <repo-dir> && git checkout <default> && git pull --ff-only
   ```
   Only switch branches if the working tree is clean; otherwise pull
   nothing there and say so. If the pull isn't a fast-forward, stop and
   report it. Never stash. Then delete the local branch if one exists and
   points at the PR's `headRefOid` (`git branch -D <branch>`, since a
   squash merge doesn't show as merged). If it points anywhere else, leave
   it and say so. Remove any leftover worktree for the branch (Step 8).
   Don't update the monorepo root's submodule pointer.
5. **Check off the item in the "Priority Order" doc, if one exists.** It's
   a Markdown note in the user's Obsidian vault on iCloud Drive, e.g.
   `Notes/Dev/Anglers' Log/Claude Code/PR Priority Checklist/Priority
   Order.md`. Find every copy under the vault's `Dev` folder:
   ```bash
   find "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Notes/Dev" \
     -name "Priority Order.md"
   ```
   Look for the PR's URL in each one. If none has it, skip this step and
   say so in one line. If the PR's line is a `- [ ]` task, change it to
   `- [x]` and add sub-bullets in the note's existing style: `✅
   **Verified <date>**` (where, the result in a sentence or two, and a
   link to the report comment), then `✅ **Merged <date>** (<repo>
   \`<short sha>\`)`. Skip the Verified line if one is already there.
   Change nothing else in the note. If several lines match, ask which one.
6. **Report:** the merge commit, the branch deleted, each repo pulled (or
   why not), and whether the doc item was ticked.
