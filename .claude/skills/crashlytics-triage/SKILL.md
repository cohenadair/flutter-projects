---
name: crashlytics-triage
description: >
  Fetches Firebase Crashlytics issues (fatal, non-fatal, Android ANRs) for
  every Firebase project in this monorepo via the Firebase MCP server, in
  three modes. Fix mode root-causes issues from their stack traces, fixes
  them in a worktree following flutter-conventions, opens a GitHub PR, and
  closes the issue. Summary mode renders the open issues as an HTML report
  with no changes. Update Me mode reports only what's new or still
  occurring since the last run. Use Fix mode for "fix the top crashes",
  "triage crashes", "fix this Crashlytics issue", or an issue ID/URL; Summary
  mode for "summarize Crashlytics issues", "crash report", "list all
  Crashlytics issues"; Update Me mode for "update me on Crashlytics", "any
  new crashes", "what's new since last time". For a bare "check
  Crashlytics" or "what's crashing in prod", ask which mode.
---

# Crashlytics Triage & Auto-Fix Skill

Three modes, all starting from the same Firebase MCP fetch. This file holds
what every mode shares; each mode's steps are in its own file:

- **Fix mode**: fetch → analyze → root-cause → fix → test → PR. Steps 0–8
  in [fix.md](fix.md).
- **Summary mode**: fetch → summarize into an HTML report. No code changes,
  no PRs, no Crashlytics mutations. SM-1–SM-8 in [summary.md](summary.md).
- **Update Me mode**: fetch → diff against issues seen on the last run →
  report only what's new. No code changes, no PRs, no Crashlytics mutations;
  the only state it writes is its own local checkpoint file. UM-1–UM-8 in
  [update-me.md](update-me.md).

Read the mode's file before starting it. Summary and Update Me reuse each
other's steps (Update Me uses SM-2–SM-5 and SM-7), so read `summary.md` for
an Update Me run too.

## Choosing a mode

- Request is to fix, triage, or resolve, or names a specific issue to work
  on → **Fix mode**.
- Request is centered on *new since last time* ("update me", "anything
  new", "what's changed") → **Update Me mode**.
- Request is to list, summarize, report on, or review issues in general
  (not phrased as a delta), with no mention of fixing → **Summary mode**.
- Ambiguous ("check Crashlytics", "what's crashing in prod", with no further
  detail) → ask the user which mode they want before proceeding.

Before debugging any tool error, search `.claude/troubleshooting/firebase.md`
for the error text.

---

## Firebase projects covered

| Firebase project ID | Repo dir | GitHub remote | Crashlytics `appId`s |
|---|---|---|---|
| `pro-iq` | `/Users/cohen/Documents/flutter-projects/pro-iq` | `Pro-IQ-Inc/pro-iq` (SSH) | Pro IQ tenant: Android `1:471654200598:android:d78feedb6a6d675f038c37`, iOS/macOS `1:471654200598:ios:860649be7b6fc80b038c37`. Hill Method tenant: Android `1:471654200598:android:3b4e94aa5384f758038c37`, iOS/macOS `1:471654200598:ios:6b2b227bc8198fbc038c37` |
| `anglers-log` | `/Users/cohen/Documents/flutter-projects/anglers-log` | `cohenadair/anglers-log` | Android `1:1018039459325:android:f4b10d819dbf3934`, iOS `1:1018039459325:ios:b91fa700d0742896244d94` |
| `activity-log-ed0d0` | `/Users/cohen/Documents/flutter-projects/activity-log/mobile` | `cohenadair/activity-log` | Android `1:369664271784:android:63e4cb098ece2abe`, iOS `1:369664271784:ios:63e4cb098ece2abe` |
| `tapd-game` | `/Users/cohen/Documents/flutter-projects/tapd/mobile` | `cohenadair/tapd` | Android `1:57081871029:android:6fe4cf3079718070499cfc`, iOS `1:57081871029:ios:33fc9ffc13bd140f499cfc` |

### Never change the Firebase CLI's active project

Every `crashlytics_*` tool takes an explicit `appId`, so this skill never
needs an active project. **Do not call `firebase_update_environment`** (it's
not in `.mcp.json`'s `--tools` allow-list, but the Firebase plugin's server
exposes it as `mcp__plugin_firebase_firebase__firebase_update_environment`
— don't call that one either) and do not run `firebase use`. Setting `active_project` writes a per-directory override
into `~/.config/configstore/firebase-tools.json` that persists after the
session and silently outranks each repo's `.firebaserc` — past runs left
`pro-iq/` pointing at `anglers-log`, which made a later `firebase deploy`
from `pro-iq/` target the wrong project.

**Source of truth for `appId`s:** the table above mirrors the `appId:` lines
in each app's `lib/firebase_options.dart` (pro-iq: one file per tenant in
`pro-iq/lib/firebase_options/`, since `lib/firebase_options.dart` is a
gitignored copy of whichever tenant was built last;
anglers-log: `anglers-log/mobile/lib/`; activity-log:
`activity-log/mobile/lib/`; tapd: `tapd/mobile/lib/`). If a Crashlytics call 404s for a listed
`appId`, or an app may have been added since, re-read those files and update
this table. Skip web app IDs (no Crashlytics). pro-iq's macOS build shares
the iOS `appId`, so it's not a separate app.

`activity-log` and `tapd` are structured differently from the other two: the
repo root holds both `mobile/` (the Flutter app, config in
`mobile/firebase.json`) and `web/` (a separate web app). Crashlytics only
applies to the mobile app, so fixes land in `mobile/`, but commits/PRs are
still made against the `activity-log`/`tapd` repo (not a separate repo per
platform). tapd's Dart package is named `mobile`, so its app-code frames are
`package:mobile/...` (relevant to SM-5's App code bucket).

`adair-flutter-lib` has no Firebase project of its own, but crashes in any
app can originate from shared code there — check it when a stack frame points
into `package:adair_flutter_lib/...`. This also applies when the *fix* (not
just the blamed frame) belongs there: a third-party-package crash (Step 5)
routed through a shared `adair-flutter-lib` wrapper should be branched,
committed, and PR'd against the `adair-flutter-lib` repo, not the app repo
that reported it — determine this by finding where the call site actually
lives, not by which Firebase project the crash came from.

---

## Prerequisites

- The Firebase MCP server must be registered (`.mcp.json` at repo root, scoped
  via `--tools` to an explicit allow-list: 3 read-only `firebase_*` env/project tools
  plus 8 `crashlytics_*` tools). Its tools are `mcp__firebase__*`. If the
  `crashlytics_*` / `firebase_*` tools aren't showing up via `ToolSearch`, the
  session likely needs a restart to pick up `.mcp.json` — tell the user.
- **Two Firebase servers are loaded.** The Firebase Claude plugin adds a
  second, unscoped server (`mcp__plugin_firebase_firebase__*`). It has **no**
  `crashlytics_*` tools: it starts in `pro-iq/` and enables only the features
  that `pro-iq/firebase.json` declares (Firestore, Functions, Hosting,
  Storage). Always use the `mcp__firebase__crashlytics_*` tools from
  `.mcp.json` for this skill. When `ToolSearch`ing, search
  `+firebase crashlytics` so both servers' tool names are visible. Never use
  the plugin server's write tools (deploy, `firestore_*` writes, environment
  changes) from this skill.
- Auth rides on `firebase login` (already logged in as the maintainer's
  Google account at the time this skill was written — reconfirm with
  `firebase_get_environment` if calls fail with an auth error).
- Known MCP quirks (confirmed live): read the Crashlytics reports guide with
  `ReadMcpResourceTool` (`server: "firebase"`,
  `uri: "firebase://guides/crashlytics/reports"`), not
  `firebase_read_resources`; and start report intervals ~85 days back,
  never a full 90 ("must be less than 90 days in the past"). Details and
  other errors: `.claude/troubleshooting/firebase.md` → Crashlytics.

---

## Fix-status cross-reference (every mode, every invocation)

Before reporting or acting on any issue, check whether a fix for it already
exists but hasn't reached users — so the report never presents an
already-fixed issue as unaddressed, and Fix mode never re-fixes one. Read-only:
only `git fetch`, `git log`, `git diff`, and `gh pr list`/`gh pr view`.

Scope: every issue this run reports or considers — Summary mode's full open
set, Update Me's new + regressed + still-occurring-ignored issues, and Fix
mode's Step 2 candidates.

1. **Unreleased commits, per repo** (`pro-iq`, `anglers-log`,
   `activity-log`, `tapd`, and `adair-flutter-lib`): `git -C <repo> fetch -q --tags
   origin`, then `git log --oneline <last-tag>..origin/HEAD`. The last tag
   is `git describe --tags --abbrev=0 origin/HEAD` for the apps;
   `adair-flutter-lib` tags per app (`pro-iq-vX`, `anglers-log-vX`,
   `activity-log-vX`), so use the tag for the app that reported the issue.
   tapd has no `tapd-vX` lib tag yet (its app tags are plain `vX.Y.Z`); for a
   tapd issue blamed in `adair-flutter-lib`, compare against the lib commit
   closest to tapd's last tag date instead.
   **Check `version:` in the app's `pubspec.yaml` too** — a version bump
   after the last tag (confirmed live 2026-10-15: pro-iq had untagged 1.3.0
   commits that were already reporting in Crashlytics) means those commits
   are *built and possibly distributed*, not unreleased. An issue still
   occurring on that version was not fixed by those commits.
2. **Open PRs, per repo**: `gh pr list --repo <owner/repo> --state open
   --json number,title,headRefName,body`. In zsh, loop over repos with a
   literal list (`for repo in a/b c/d; do …`) — `set -- $r` word-splitting
   breaks under zsh.
3. **Match each issue**, strongest signal first:
   - **ID match**: the issue ID or its 8-char prefix in a PR's title, body,
     or `crashlytics-<short-id>` branch, or in a commit message (`git log
     --all -i --grep=<prefix>`). Fix-mode PRs embed the console link, so
     this catches most of them.
   - **Code match**: an unreleased commit or open PR that touches the
     blamed file/symbol — read the diff and only count it as a fix if it
     actually changes the failing path. Touching the file isn't enough.
   - **Keyword match**: the blamed symbol or exception text in PR bodies.
     Also search recently **merged** PRs (`--state all`); a match that
     merged before the last tag shipped already, which explains why it's
     still occurring rather than linking a pending fix.
4. **Classify** each issue's Fix status:
   - `Fixed — unreleased <sha>` (merged after the last tag; link the commit)
   - `Fix in open PR #N` (link the PR; note if it's only in
     `adair-flutter-lib`, since the app also needs its lib ref bumped)
   - `Related, not a fix — <link>` (touches the same area but doesn't
     address the failure; say why in a few words)
   - `Shipped in <version> — still occurring` (a merged fix that's already
     released, yet the issue recurs on that version or later)
   - `—` (nothing found)
5. **Flag closed-but-unshipped fixes.** If an issue is `SIGNAL_REGRESSED`
   or still occurring after being closed, and its only fix is an *open* PR,
   say so explicitly — the issue was closed before the fix shipped, which
   is why it regressed.

Use the result in each mode's output (SM-7's Fix status column, UM-7's
tables, Fix mode Step 2's shortlist in fix.md). Link PRs as
`[owner/repo#N](https://github.com/owner/repo/pull/N)` and commits as
`[repo@sha](https://github.com/owner/repo/commit/sha)`.

---

## Checkpoint bookkeeping after acting on issues

Whenever this skill — in *any* mode, including a follow-up turn after an
Update Me report — mutates an issue or the user explicitly decides on one,
update that app's `ignoredIssues` in the checkpoint file
(`~/.claude/crashlytics-triage/update-me-state.json`, shape in
[update-me.md](update-me.md) → UM-2; read-modify-write the whole file, as
in UM-8):

- **Muted** (user asked) → `status: "muted"`, `since` = now, `note` = the
  user's reason.
- **Closed without a code fix** (e.g. "fixed in a newer build", SM-8
  stale/duplicate, Fix Mode's outdated-issue path, or the
  no-app-fixable-resolution path) → `status: "closed"`, `since` = now,
  `note` = the closing note text.
- **Explicitly left as-is** → keep/create `status: "left-open"`.
- **Fixed via a Fix-mode PR** (Step 8 closed it) → **remove** the entry.

This is the only checkpoint write outside UM-8, and it never touches
`knownIssueIds` or `lastCheckTime`.

---

## After the run

Do the `skill-maintenance` Retro (per `CLAUDE.md`): fix anything this run
showed was missing, wrong, or stale in this skill or its mode files, and add
new tool errors to `.claude/troubleshooting/firebase.md`.
