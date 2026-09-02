---
name: crashlytics-triage
description: >
  Fetches Firebase Crashlytics crash issues via the Firebase MCP server —
  across all Firebase projects in this monorepo — and either (Fix mode)
  analyzes stack traces, root-causes the bug, implements a fix following this
  repo's Flutter conventions, and opens a GitHub PR, or (Summary mode) just
  fetches and summarizes issues into a table with no code changes. Use Fix
  mode when the user says things like "triage crashes", "check Crashlytics",
  "fix the top crashes", "what's crashing in prod", or references a specific
  Crashlytics issue ID/URL. Use Summary mode when the user says things like
  "summarize Crashlytics issues", "give me a crash report", "list all
  Crashlytics issues", or otherwise asks to see/review crashes without asking
  to fix anything.
---

# Crashlytics Triage & Auto-Fix Skill

Two modes, both starting from the same Firebase MCP fetch:

- **Fix mode** (default): fetch → analyze → root-cause → fix → test → PR.
  See **Fix Mode** below (Steps 0–8).
- **Summary mode**: fetch → summarize into a table. No code changes, no PRs,
  no Crashlytics mutations. See **Summary Mode** below.

## Choosing a mode

- Request is to fix, triage, resolve, or references a specific issue to
  work on → **Fix mode**.
- Request is to list, summarize, report on, or review issues, with no
  mention of fixing → **Summary mode**.
- Ambiguous ("check Crashlytics" with no further detail) → ask the user
  which they want before proceeding.

---

## Firebase projects covered

| Firebase project ID | Repo dir | GitHub remote |
|---|---|---|
| `pro-iq` | `/Users/cohen/Documents/flutter-projects/pro-iq` | `Pro-IQ-Inc/pro-iq` (SSH) |
| `anglers-log` | `/Users/cohen/Documents/flutter-projects/anglers-log` | `cohenadair/anglers-log` |
| `activity-log-ed0d0` | `/Users/cohen/Documents/flutter-projects/activity-log/mobile` | `cohenadair/activity-log` |

`activity-log` is structured differently from the other two: the repo root
holds both `mobile/` (the Flutter app, config in `mobile/firebase.json`) and
`web/` (a separate web app, config in `web/.firebaserc`). Crashlytics only
applies to the mobile app, so fixes land in `mobile/`, but commits/PRs are
still made against the `activity-log` repo (not a separate repo per platform).

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
  via `--tools` to an explicit allow-list: 4 `firebase_*` env/project tools
  plus 8 `crashlytics_*` tools). If the `crashlytics_*` / `firebase_*` tools
  aren't showing up via `ToolSearch`, the session likely needs a restart to
  pick up `.mcp.json` — tell the user.
- Auth rides on `firebase login` (already logged in as the maintainer's
  Google account at the time this skill was written — reconfirm with
  `firebase_get_environment` if calls fail with an auth error).
- Tool names below have been exercised live (first full run: 2026-08-16,
  anglers-log). Two confirmed corrections to the MCP docs' own descriptions:
  - `crashlytics_get_report`'s description says to read the Crashlytics
    Reports Guide via a `firebase_read_resources` tool — that tool doesn't
    exist in this harness. Use `ReadMcpResourceTool` instead, with
    `server: "firebase"` and `uri: "firebase://guides/crashlytics/reports"`.
  - `intervalStartTime`/`intervalEndTime` filters reject a start time exactly
    90 days back (`"must be less than 90 days in the past"`). Use ~85 days
    back, not a full 90, to avoid the boundary error.

---

## Summary Mode

Read-only: fetches and summarizes issues, then renders them as a self-contained
HTML page. Never writes a Crashlytics note, never closes/updates an issue,
never touches git or GitHub. The output is meant to be handed back to this
skill in **Fix mode** — the user picks issues by Reference ID.

### SM-1 — Scope

Ask the user only for what isn't already implied by their request:

1. **Which project(s)?** Defaults to **all three** (see the projects table
   above). If the user names one, scope to that one only.
2. **Time window?** Defaults to the last ~85 days (the widest range the
   Crashlytics API allows — see the 90-day boundary note in Prerequisites).
3. **Issue state?** Defaults to **open/unresolved** issues only, since those
   are the ones worth acting on. Include closed/resolved issues only if the
   user asks (e.g. "include resolved ones too") — the `state` field is
   already on every row returned in SM-3, so this is a filter on data
   already in hand, not an extra call.

Fatal and non-fatal issues are always both included — that distinction is a
column in the output, not a filter.

### SM-2 — Set active project and enumerate apps

For each project in scope:

1. `firebase_update_environment` with `active_project` (and `project_dir` the
   first time you touch a given repo dir). **Verify it actually took** with a
   follow-up `firebase_get_environment` call before proceeding — confirmed
   live (2026-08-19) that setting `active_project` and `project_dir` in the
   same call can silently leave the *previous* project active. If
   `firebase_get_environment` still shows the old project, call
   `firebase_update_environment` again with just `active_project` (no
   `project_dir`) and re-verify. Don't call `firebase_list_apps` until the
   active project is confirmed correct — otherwise you silently fetch the
   wrong project's apps.
2. `firebase_list_apps` (`platform: "all"`) to get every `appId` in the
   project. Skip `WEB` apps (no Crashlytics). Every call below is
   per-`appId` — a project with both an Android and iOS app produces two
   separate sections (platforms aren't comparable — see the multi-platform
   note in Fix Mode Step 2).

### SM-3 — Fetch issues per app

For each `appId`:

1. Call `crashlytics_get_report` twice — once with
   `filter.issueErrorTypes: ["FATAL"]`, once with `["NON_FATAL"]` — both with
   `report: "topIssues"`, the SM-1 time window, and a generous `pageSize`
   (start at 100). Two separate calls, not one combined filter, so each
   issue can be tagged Fatal/Non-fatal by which call surfaced it.
2. **No confirmed pagination.** If a call returns exactly `pageSize` rows,
   the list is likely truncated — say so in the final output rather than
   silently presenting a partial list as complete, and retry once with a
   larger `pageSize` if that seems likely to matter (e.g. a high-traffic
   app).
3. **This response already carries most of what you need** — confirmed live
   (2026-08-19), don't re-fetch it per issue:
   - `issue.id`, `issue.title`, `issue.subtitle`, `issue.errorType`
   - `issue.state` (filter to `OPEN` here per SM-1, no separate
     `crashlytics_get_issue` call needed)
   - `issue.firstSeenVersion` / `issue.lastSeenVersion` — **this is the App
     Version Range column directly.** No separate `topVersions` report call
     needed.
   - `issue.sampleEvent` — the resource name to fetch in SM-4 for the last
     occurrence timestamp and stack trace.
   - `metrics[0].eventsCount` / `metrics[0].impactedUsersCount` —
     Occurrences and Affected Users columns directly.
   - `issue.uri` — deep link to the Firebase console for that issue; use it
     in the HTML output (SM-6).
4. If SM-1 scoped to open issues only (the default), drop any issue whose
   `issue.state` isn't `OPEN` right here — no extra call required.

### SM-4 — Fetch the last event per issue

For every issue surfaced in SM-3, fetch the full event behind its
`sampleEvent` name via `crashlytics_batch_get_events`. Confirmed live
(2026-08-19): `sampleEvent` is consistently the *most recent* event for the
issue (its `eventTime` matches what `crashlytics_list_events` with
`pageSize: 1` returns) — so this single fetch gives you Last Occurred +
the full stack trace in one shot, no separate `list_events` call needed.

- **Batch by `appId`, not one call per issue.** `crashlytics_batch_get_events`
  accepts an array of event names — pass every `sampleEvent` name for a
  given `appId` in one call.
- **Response size caps out fast.** A batch of ~20+ mobile events (each
  carries device/memory/logs/threads/exceptions) exceeds the tool's inline
  output limit and gets redirected to a saved file
  (`.../tool-results/mcp-firebase-crashlytics_batch_get_events-*.txt`) with a
  message to read it in chunks. Don't try to read that file with the `Read`
  tool section-by-section — instead parse it with a script (`Bash` +
  `python3`): the format is YAML-ish block-scalar text, one record per
  `- name: |` line. Extract per record: `issue.id` (inside the nested
  `issue:` block), `eventTime`, `blameFrame.file` / `blameFrame.owner` /
  `blameFrame.symbol`, and `exceptions` (fall back to `threads` for native
  crashes with no Dart exception). A generic block-scalar parser (read lines
  after `key: |`/`key: |-`/`key: >-` until the next line at the same or
  lower indent) handles this reliably — see this run's approach: split on
  `\n(?=- name: \|)`, then within each record locate top-level `  key:
  value` lines and consume indented continuation lines as the block body.
- If a project/app has few enough issues that the combined response stays
  under the limit (roughly ~10–15 mobile events), it comes back inline and
  no file-parsing step is needed — just extract the same fields directly.

### SM-5 — Classify and infer origin

For every issue, using its `blameFrame` and full stack trace from SM-4:

1. **Stack trace classification** — path-based on `blameFrame.file`, *not*
   `blameFrame.owner` (confirmed live: `owner` is `DEVELOPER` for both true
   app code *and* third-party pub packages like `protobuf` or
   `cloud_firestore_platform_interface` — it only distinguishes an
   attributable Dart/JVM/ObjC frame from a native one, it does not mean
   "the app's own code"). Apply the same three buckets as Fix Mode Step 4:
   - `blameFrame.file` is `package:<app-package>/...` or
     `package:adair_flutter_lib/...` → **App code**
   - `blameFrame.file` is `package:<anything-else>/...` (including
     `package:flutter/...` — the Flutter SDK itself is not app code) →
     **Third-party**, and name the package in the cell, e.g. "Third-party
     (mapbox_maps_flutter)"
   - `blameFrame.file` is empty, `SourceFile` (obfuscated Android), or an
     unresolvable native symbol (`blameFrame.owner` is `SYSTEM`/`PLATFORM`,
     or `THIRD_PARTY` with no Dart file) → **Unknown/native**
2. **Likely origin (one sentence)** — read the issue's title, subtitle, full
   stack trace, and `blameFrame` together and write one sentence explaining
   *where in the app's flow* this happens and *why*, not just a restatement
   of the exception message. Name the actual class/method and the plausible
   trigger (a UI action, a lifecycle timing issue, a data-shape mismatch,
   an OS/device condition). Distinguish "this is a real app bug" from "this
   is an environment/OS/library quirk the app should defensively handle."
   This is the same reasoning Fix Mode Step 4 does before proposing a fix —
   here it's surfaced to the user instead of acted on.

### SM-6 — Cross-platform duplicate detection

For each project with issues on both Android and iOS, flag any pair that's
likely the same underlying bug surfacing on both platforms (common for
anglers-log/activity-log, whose Dart code is shared across platforms).

- **Don't match on `blameFrame`/title alone.** Several blamed frames are
  generic wrapper call sites hit by many unrelated errors —
  `package:adair_flutter_lib/utils/log.dart - Log._log` (every `Log.e()`
  call in the app blames this same line) and
  `package:flutter/src/services/message_codecs.dart -
  StandardMethodCodec.decodeEnvelope` (every platform-channel error blames
  this) are the two confirmed live (2026-08-19) to produce false positives
  if matched by title alone.
- **Match on title (same blamed symbol) AND subtitle similarity.** Normalize
  each subtitle (lowercase, strip hex addresses and bare numbers, collapse
  whitespace) and compare with a similarity ratio
  (`difflib.SequenceMatcher.ratio()` in a Python one-off, or equivalent) —
  treat pairs above ~0.6 as a match. This correctly rejects the two false
  positives above (their subtitles describe unrelated errors) while still
  catching a genuine same-cause pair if one ever appears.
- Confirmed live: across all issues open at the time, zero genuine
  cross-platform matches existed — both `Log._log` and `decodeEnvelope`
  title collisions were false positives once subtitles were compared. Don't
  assume the feature is broken if it finds nothing; it correctly found
  nothing that run.
- Store the match (other platform's issue ID) per issue for SM-7's table.

### SM-7 — Render as a single-file HTML page

Write one self-contained `.html` file (no external requests, inline CSS/JS)
to `~/Downloads/crashlytics-summary-<YYYYMMDD-HHMM>.html` and deliver it to
the user (`SendUserFile`) — don't just paste markdown tables into chat, the
volume (often 30–50+ open issues across three projects) is unreadable that
way.

**Always declare `<meta charset="UTF-8">` as the first tag in `<head>`.**
This file is delivered as a raw file via `SendUserFile`, not published through
the Artifact tool — so it does not get an automatically-injected charset meta
the way an Artifact publish would. Confirmed live (2026-09-02): without an
explicit charset tag, opening the file directly caused every em dash, en
dash, and middle dot (all used throughout this page's copy — em dashes in
prose, `·` in the header eyebrow, etc.) to render as mojibake (`â€”` and
similar) because the viewer guessed Windows-1252 instead of UTF-8. The file
on disk was valid UTF-8 the whole time; only the missing declaration was
wrong. Add the meta tag before writing any other content into the file, and
verify with `file <path>` (expect "UTF-8 text") plus a quick `grep -c "â€"
<path>` (expect 0) before delivering.

Structure:

- One section per project, then per platform within it (same grouping as
  SM-2/SM-3), each with its own table, in the order the projects table above
  lists them.
- **Every non-web app enumerated in SM-2 gets its own section, with no
  exceptions for having nothing to show.** Do not fold zero-issue apps into a
  separate summary list or footnote, and do not silently omit them — confirmed
  live (2026-09-02) that doing so (a "no open issues" appendix at the bottom
  of the page) reads as apps missing from the report entirely, since the
  section list at a glance no longer matches SM-2's app enumeration. Render
  the section and its table exactly as for any other app; the table itself
  is what's empty. Give the empty table a single centered row spanning all
  columns with a short message instead of headers-with-nothing-under-them:
  - Zero *open* issues were found in the SM-1 window (the normal case): "No
    open issues in this window."
  - `crashlytics_get_report` returned a 404 for this `appId` (confirmed live
    for a white-label variant app sharing a project with another brand, e.g.
    a second brand's Android/iOS app registered in Firebase but never
    integrated with the Crashlytics SDK): "No Crashlytics data for this app
    — Crashlytics may not be integrated yet." Don't conflate this with the
    zero-issues case; they mean different things to the user.
  - These empty sections still get their own `N open` count pill (`0 open`)
    and are still independently collapsible — default them to **collapsed**
    on load (unlike sections with issues, which start expanded per the
    section-collapse bullet below) so a run with several quiet apps doesn't
    bury the ones that actually need attention, while still being visibly
    present and one click away.
- Table columns: Reference ID, Type (Fatal/Non-fatal badge), Occurrences,
  Last Occurred, Affected Users, App Version Range, Stack Trace
  (App code/Third-party/Unknown-native badge), Cross-Platform (SM-6 — a
  badge naming the matched platform + issue ID as a tooltip, or an em-dash
  if no match), Likely Origin (the SM-5 sentence).
- **Last Occurred display format has no timezone suffix** — render as e.g.
  `Aug 05, 2026 13:00`, not `Aug 05, 2026 13:00 UTC`. The values are still
  UTC (Crashlytics' `eventTime` is UTC and this skill doesn't convert it),
  just don't label every cell with it — say once near the top of the page
  that times are UTC if it's not otherwise obvious, rather than repeating
  the suffix 40+ times. Same for the "generated" timestamp in the page
  header. The `data-sort` attribute (SM-7's sortable-column bullet below)
  still carries the full ISO 8601 UTC string regardless of what's displayed
  — only the human-readable text drops the suffix.
- **Default sort is Last Occurred, most recent first** — not by occurrence
  count — but every column header is clickable to re-sort (see the dedicated
  bullet below).
- **Every section header (project + platform) is collapsible**, independent
  of row-level expand/collapse: clicking it toggles the whole table below.
  Use a `<button>` header (not a bare `<div>`) with `aria-expanded` reflecting
  state, so it's keyboard-accessible. Sections start expanded by default —
  30–50 issues across three projects is a lot to page through, so letting
  the user collapse projects/platforms they don't care about this run is
  the point, not making them collapse everything first.
- **Every row is independently expandable/collapsible** (click to toggle, no
  page reload): expanding reveals the full issue title, subtitle, a link to
  the Firebase console (`issue.uri` from SM-3), and the full stack trace
  (`exceptions`/`threads` from SM-4) in a `<pre>` block. This must keep
  working after adding section-level collapse — confirmed live (2026-08-19)
  the two toggles (section `<button>` vs row `<tr>`) don't interfere since
  they're bound to different elements with no shared click target.
- **Every column header is sortable**, independently per table (each
  project/platform table sorts on its own data, not globally). Click once to
  sort ascending, click the same header again to reverse to descending;
  clicking a different header resets to ascending on that column. Show a
  small ▲/▼ indicator on the active sort column only, and pre-mark the Last
  Occurred header as the active (descending) sort on page load to match the
  default order rows are rendered in — don't leave the indicator blank when
  a sort is already in effect.
  - Give each `<th>` a `data-col` (its cell index) and `data-type`
    (`text`/`num`/`date`) attribute the sort handler reads, and give the
    corresponding `<td>` in every row a `data-sort` attribute with the raw
    sortable value — Occurrences/Users need the bare number (not the
    formatted string), Last Occurred needs the raw ISO timestamp (not the
    human-formatted "Aug 05, 2026 13:00" string, which won't sort
    chronologically as text). Text columns (Reference ID, Type, Version
    Range, Stack Trace, Cross-Platform, Likely Origin) can sort on
    `textContent` directly.
  - **Sorting must move each issue row's detail row with it.** The expand
    detail is a separate `<tr class="detail-row">` immediately following its
    `<tr class="issue-row">` in the DOM, not nested inside it — a naive sort
    that only reorders `.issue-row` elements orphans every detail row from
    its issue, showing the wrong stack trace under the wrong row. After
    sorting, re-append each issue row's paired detail row (found via the
    issue row's `data-target` → the detail row's matching `id`) right after
    it. Confirmed live (2026-08-19): sorting by Occurrences, expanding a row
    post-sort, and confirming the stack trace shown matches that row's
    Reference ID (not a stale pairing) — this is the failure mode to check
    for, a static screenshot of the sorted table alone doesn't catch it.
  - Sorting is a pure DOM reorder (no page reload, no data refetch) and must
    not disturb section collapse state or any row's already-expanded detail.
- **Don't force a horizontal scrollbar the container doesn't need.** Give the
  `<table>` `table-layout: fixed` plus an explicit `<colgroup>` of
  percentage-width `<col>`s summing to 100% (roughly: Reference ID 11%, Type
  8%, Occurrences 8%, Last Occurred 11%, Affected Users 9%, Version Range
  10%, Stack Trace 9%, Cross-Platform 10%, Likely Origin 24%) instead of a
  fixed pixel `min-width` on the table or `white-space: nowrap` on `thead
  th`. Confirmed live (2026-09-02): a `min-width: 980px` plus nowrap headers
  forced a scrollbar even inside a ~1130px-wide content column, because
  auto table layout sizes columns to their widest unwrapped content
  (particularly the Likely Origin prose) regardless of how much container
  width is actually available. With `table-layout: fixed` + percentage
  columns the table always exactly fills its container and never needs to
  scroll when there's room — long text (Likely Origin, the full-length
  title/subtitle in the id cell) just wraps within its column instead
  (`overflow-wrap: break-word` on `td`). Keep `.table-scroll`'s
  `overflow-x: auto` as a fallback only, for a viewport too narrow to fit
  even the minimum readable column widths — it should not be what's
  triggering on an ordinary desktop window.
- **Reference ID is plain text**, not a link — the user copies it verbatim
  back to this skill for Fix mode. Call out once, near the top of the page,
  that Reference IDs are scoped per-project/appId and are **not**
  guaranteed globally unique — the same issue ID can legitimately appear in
  two different projects if Crashlytics grouped an identical stack
  signature the same way in both (confirmed live: `activity-log` and
  `anglers-log` both produced an issue with ID
  `2d42509567320134aecbd6708ad5fa8b` for an unrelated `adair_flutter_lib`
  log call). When handing a Reference ID back to Fix mode in a case like
  this, the user needs to say which project too.
- **Copy-to-clipboard button beside every Reference ID** — a small icon
  button next to the `<code>` ID, using the `navigator.clipboard` API with a
  `document.execCommand('copy')` fallback (needed for non-secure/`file://`
  contexts where `navigator.clipboard` is unavailable). On click, briefly
  swap the icon to a checkmark (~1.2s) as copy confirmation. **Must call
  `event.stopPropagation()`** in the button's click handler — the button
  lives inside the row's `<td>` and the row itself has its own click handler
  for expand/collapse (SM-6 above); without `stopPropagation` a copy click
  also toggles the row open/closed. Confirmed live (2026-08-19): clicking
  the actual button (not just near it) leaves the row's expanded state
  untouched, and the OS clipboard visibly updates.
- Keep the visual style consistent with this codebase's dark-UI conventions
  (see this run's output for a working reference: dark background, colored
  badges for Fatal/Non-fatal and the three origin buckets, monospace for IDs
  and stack traces).
- After writing the file, open it in the browser preview tool and click a
  row to confirm the expand/collapse interaction actually works, and click a
  copy button specifically (via its element ref, not just an approximate
  coordinate) to confirm it copies without toggling the row — a static
  screenshot doesn't prove either interaction actually works.
- Close the chat reply with a one-line reminder: give me the Reference
  ID(s) (and project, if ambiguous) from the page and say "fix" to hand them
  to Fix mode.

### SM-8 — Stale/duplicate candidates (only when asked, and only with confirmation)

Triggered by a follow-up like "which of these are stale" or "summarize
what's stale" — not part of the default SM-1–SM-7 flow.

- **This is not pre-authorized**, unlike Fix Mode's outdated-issue path
  (Step 4) or Step 8's close-on-PR-open — Summary Mode never mutates
  Crashlytics without the user explicitly saying so for that batch of
  issues. Propose candidates, then wait for a yes before calling
  `crashlytics_create_note` / `crashlytics_update_issue` on any of them.
- **Verify, don't guess from version age.** An old `lastSeenVersion` is a
  reason to *look*, not a reason to conclude staleness. For every
  App-code-classified candidate, actually read the current file at the
  blamed path (`blameFrame.file` from SM-4) and check whether the blamed
  class/method still exists and the described crash is still plausible
  there — same check as Fix Mode Step 4's stale-issue rule. Confirmed live
  (2026-08-19): several issues on old app versions turned out to have the
  *exact same bug still present*, just shifted to a different line number
  because unrelated code was added above it in the file — that is **not**
  stale. Only flag a candidate when the file is gone entirely, the
  class/method no longer exists anywhere in the repo (grep for the class
  name too, in case the file was renamed), or the described crash can no
  longer occur at that location. Third-party and Unknown/native issues
  aren't checkable this way (no app file to verify against) — don't
  guess at staleness for those.
- **Duplicate detection is a separate, related judgment call** — two open
  issues that are really the same underlying bug (e.g. Crashlytics grouped
  the same crash into two issue IDs/variants; SM-6's cross-platform
  matching can surface a Crashlytics grouping gap too). Propose these
  alongside stale candidates but label them distinctly, since the
  resolution note differs (see below).
- Present each candidate with the evidence (file path, what you found or
  didn't find, the other issue ID for duplicates) and wait for the user to
  confirm which ones to actually close before touching Crashlytics.
- **Resolution, once confirmed** — same mechanics as Fix Mode's outdated-issue
  path (`crashlytics_create_note` then `crashlytics_update_issue` with
  `state: "CLOSED"`), against the confirmed issue's own `appId`:
  - **Stale**: note text `"Code is outdated."`, matching Fix Mode Step 4
    exactly.
  - **Duplicate**: note text naming the canonical issue ID it duplicates,
    e.g. `"Duplicate of issue <canonical-id> (<short reason>). Closing as a
    duplicate variant."` — don't just say "duplicate", name what it's a
    duplicate *of* so the note is still useful read cold later.
- After closing, **regenerate SM-7's HTML** with the closed issues removed
  from their table (don't leave stale rows in an "open issues" report) and
  a short note near the top of the page listing what was closed this
  session and why, then redeliver via `SendUserFile`. Don't silently
  reuse the old file — the whole point of a fresh render is that it
  reflects current state.

---

## Fix Mode

## Step 0 — Scope the run

Ask the user only for what isn't already implied by their request:

1. **Which project(s)?** Defaults to **all three** — `pro-iq`, `anglers-log`,
   `activity-log-ed0d0` — run sequentially, not parallel (keeps output
   readable and avoids interleaved branch/PR work). If the user's prompt
   names a specific project (e.g. "check pro-iq crashes"), scope to that one
   project only — don't ask, just narrow the run.
2. **Which issue(s)?** A specific Crashlytics issue ID/URL they already have,
   or "find the top N open issues" (pick N, default 3).
3. **Autonomy level**: fix everything found, opening a PR and closing the
   issue for each automatically per Steps 7–8 (default), or stop after
   root-causing and let the user pick which ones to actually fix.

---

## Step 1 — Set the active Firebase project

Call `firebase_get_environment` to see current state, then
`firebase_update_environment` to point at the target project ID (`pro-iq`,
`anglers-log`, or `activity-log-ed0d0`). Repeat per project when running the
default all-projects scope.

---

## Step 2 — Identify issues to triage

- If the user gave a specific issue ID/URL, skip to Step 3.
- Otherwise call `crashlytics_get_report` to get aggregated crash data
  (event counts, impacted users, and — check the live schema — an app-version
  / release dimension). There is no confirmed "list all issues" tool — if
  `get_report` doesn't surface enough to pick candidates, ask the user to
  paste issue links from the Firebase console rather than guessing at an
  undocumented tool.
- **Ranking order (strict priority, always applied, not just the default):**
  1. **Crashes (fatal) before non-fatals.** Build the candidate list from
     fatal issues only; only consider non-fatals if the user explicitly asks
     for them, or after fatal candidates for every release are exhausted.
  2. **Newest release first.** Determine the most recent release version from
     the app-version dimension in the Crashlytics data itself (not the
     GitHub tag — Crashlytics should reflect what's actually reporting
     crashes in the field). If the report tool doesn't expose a version
     filter directly, pull sample events for candidate issues and check the
     version field on each to group them by release.
  3. **Most frequent first, within a release.** Rank by event count
     (impacted users as tiebreaker) among the fatal issues for that release.
  4. If the newest release doesn't have enough open crash issues to fill N,
     move to the next-most-recent release and continue, still crash-first.
- **Multi-platform projects** (a Firebase project with both an Android and an
  iOS app, e.g. `anglers-log`): apply the full ranking above independently
  per platform/appId — release recency and event counts aren't comparable
  across platforms. Default to top-N *per platform*, not N total, so the
  shortlist surfaces both. Presenting this as "top 3 Android + top 3 iOS = 6
  candidates" and asking the user to confirm scope (all of them / one
  platform / a subset) works well in practice.
- Present the shortlist (issue title, release, event count, impacted users)
  and confirm with the user before deep-diving — avoids burning time
  analyzing issues they don't care about.

---

## Step 3 — Fetch issue detail & stack traces

For each selected issue:

1. `crashlytics_get_issue` — title, state, first/last seen.
2. `crashlytics_list_notes` — check for prior triage notes so work isn't
   duplicated. If a note links to a GitHub issue, fetch its full history
   (`gh issue view <n> --repo <owner>/<repo> --json title,body,state,url,comments`)
   before root-causing — it may contain prior investigation findings (e.g.
   "already tried upgrading the plugin, still crashes on the newer version",
   reproduction steps a human already gathered, or a link to an upstream SDK
   issue) that should directly shape the approach rather than being
   rediscovered from scratch. While you have it open, apply the platform
   label from the **Platform label** section below if it's missing.
3. `crashlytics_list_events` then `crashlytics_batch_get_events` — pull
   sample events with full stack traces. Grab a few samples if the crash has
   multiple distinct triggering paths, not just one.

---

## Step 4 — Root-cause

- Map the top stack frame(s) in app code (skip framework/SDK frames) to the
  actual file in the repo dir from the table above. Dart frames map directly;
  native frames (Kotlin/Swift/Java) live under `android/` or `ios/` in the
  same repo.
- **Stale-issue check first.** If the file no longer exists at that path, or
  the line number lands outside the file / on unrelated code / on a line that
  couldn't plausibly throw what the stack trace describes, the issue predates
  the current codebase. Don't guess at a fix — go straight to the **outdated
  issue** path below and move to the next issue.
- Read the implicated code and enough surrounding context (caller, related
  managers/wrappers) to understand the real bug, not just the crash site.
- Per this repo's conventions: check whether the bug lives in a wrapper,
  manager, or widget, and whether shared logic in `adair-flutter-lib` is
  actually at fault even if the crash surfaced in `pro-iq`/`anglers-log`.
- **Classify where the crash actually originates** before deciding what kind
  of fix applies:
  - App code or `adair-flutter-lib` → continue to Step 6 (Fix) as normal.
  - A third-party pub package (stack frame under `package:<name>/...` that
    isn't `adair_flutter_lib` or the app's own package) → go to Step 5
    instead.
  - No app-owned or pub-package call site at all — e.g. a native engine
    bootstrap failure (`Could not find 'libflutter.so'`), an OS-level crash,
    or anything Crashlytics itself attributes to `owner: THIRD_PARTY` in
    obfuscated/native code with no Dart frame involved, especially if it
    spans unrelated devices/manufacturers (or shows up on emulators, where
    it may just reflect an ABI the release build doesn't ship) → there is no
    code fix available. Don't guess at one — go to the **no app-fixable
    resolution** path below.
- State the root-cause hypothesis and the planned fix to the user before
  writing code if the issue is ambiguous, spans multiple files, or touches
  Firestore/data-model concerns. For a clear, small, local bug, proceed
  directly and explain the reasoning in the PR description instead.

### Outdated issue (pre-authorized, automatic — no PR)

Skip the fix/PR flow entirely. Same pre-authorization basis as Steps 7–8
(2026-08-15): Crashlytics-only mutation, no code change, no branch.

1. `crashlytics_create_note` on the issue with the text `Code is outdated.`
2. `crashlytics_update_issue` to close/resolve it.
3. Report the issue ID in the running checklist as "closed — outdated" and
   move to the next issue.

### No app-fixable resolution (ask the user — not pre-authorized)

Reached when Step 4 classified the crash as having no app-owned or
pub-package call site to fix. Unlike the outdated-issue path, this is **not**
pre-authorized to auto-resolve: closing it as "outdated" would be factually
wrong (the code isn't stale, it's just not the cause), and silently leaving
it open contradicts the "fix everything automatically" autonomy level the
user may have chosen in Step 0. Explain the root-cause finding (what the
crash actually is, why no code change addresses it, and any device/version
pattern found) and ask the user how to resolve the Crashlytics issue itself:
mute it, leave it open with an explanatory note, close it with no note, or
leave it untouched. Apply whatever they pick, then move to the next issue —
there is no PR for this path.

---

## Step 5 — Third-party library crashes

Only reached when Step 4 classified the crash as originating in a pub
package, not app code or `adair-flutter-lib`.

1. Check the package's current constraint in the relevant `pubspec.yaml` and
   its resolved version in `pubspec.lock`.
2. Research whether the crash is already fixed in a newer version — check the
   package's CHANGELOG on pub.dev and, if available, its GitHub issues/commits
   for the specific exception/symptom from the stack trace.
3. **If a newer version fixes it**: check whether the existing constraint
   already permits it (`flutter pub outdated` shows the resolvable version
   even when the lockfile is stale) — often `flutter pub upgrade <package>`
   is enough with no `pubspec.yaml` edit at all. Then treat this as the fix
   and verify thoroughly before the PR:
   - Run the **full** `flutter test` suite, not just tests that obviously
     touch the package. A version bump can change generated interfaces
     (nullable return types, new optional parameters) in ways the changelog
     doesn't fully call out, breaking compilation or mocks elsewhere.
   - If compile errors point into `mocks.mocks.dart`, regenerate mocks
     (`gen_mocks.sh` / `dart run build_runner build`) — see the `flutter-test`
     skill/root `CLAUDE.md` for the exact command per repo. Never hand-edit
     the generated file.
   - If the package has an iOS component, run `pod install` in the `ios/`
     dir so `Podfile.lock` (typically gitignored — check with
     `git check-ignore` before assuming it needs to be committed) picks up
     the new native pod version; otherwise the fix won't actually apply to
     iOS builds.
4. **If it isn't fixed upstream**: add a reasonable defensive guard at the
   call site so the exception can't crash the app — e.g. wrap the call in
   `try`/`catch` following this repo's error-handling convention (log via
   `_log.e(e, reason: "...")`, never an empty `catch`), or add a null/bounds
   check if the crash is a predictable misuse pattern. Don't swallow the
   error silently — log it and fall back to sensible default behavior.
   - If the call site is a **wrapper** (per the wrappers-vs-managers
     convention in root `CLAUDE.md`), the guard usually reads best as a
     shared private helper the wrapper's other methods route through, not a
     one-off `try`/`catch` at a single call site — see whether the same
     underlying SDK constraint could plausibly hit other methods on that
     wrapper too. Per the "no tests for wrappers" testing convention, don't
     add a dedicated test file for the wrapper itself — Step 6's
     test-writing requirement is satisfied by confirming the existing
     call-site tests (which mock the wrapper) still pass unmodified, proving
     the public API surface didn't change.
   - If that wrapper lives in `adair-flutter-lib` rather than the reporting
     app, see the "Firebase projects covered" section above — the fix,
     branch, and PR belong in the `adair-flutter-lib` repo.
5. Either way, the PR description (Step 7) must include: the package name and
   versions (before/after if bumped), a link to the changelog/issue found (or
   a note that none was found), and — for the defensive-guard path — why a
   library-side fix wasn't available and what the guard does.

---

## Step 6 — Fix

### Set up an isolated worktree

Every issue's fix happens in its own temporary `git worktree`, never directly
on whatever branch happens to be checked out in the main repo clone. This
keeps sequential fixes within a run from bleeding into each other and
guarantees each PR's diff is exactly that issue's fix.

1. **Determine the default branch** (if not already known for this repo this
   run): `gh repo view <owner>/<repo> --json defaultBranchRef -q
   .defaultBranchRef.name`. Don't assume — it differs across repos in this
   monorepo (e.g. `anglers-log` uses `master`, `adair-flutter-lib` uses
   `main`). Reuse this value in Step 7 instead of looking it up again.
2. **Determine the base branch/ref for the worktree:**
   - **Default:** the repo's default branch at its current remote tip. Fetch
     first so the worktree starts from the true tip —
     `git -C <repo-dir> fetch origin <default-branch>` — then base off
     `origin/<default-branch>`.
   - **Exception — related fixes within the same run.** If an *earlier* issue
     fixed in this run (same repo) touched code that this issue's fix will
     also touch or directly depend on (same file, same
     widget/manager/wrapper, or one fix would conflict with or build on the
     other), base this worktree on that earlier issue's branch instead.
     Otherwise — different issue, different code — always branch fresh from
     `origin/<default-branch>`, even if both issues are in the same repo or
     same run. Note the stacking explicitly in this issue's PR description
     (Step 7): it depends on the earlier PR merging first, or will need
     retargeting once that happens.
3. **Create the worktree** in a sibling directory next to the repo (not
   inside it, so it's outside the repo's own `.gitignore`/tooling scans):
   ```bash
   git -C <repo-dir> worktree add ../<repo-name>-crashlytics-<short-id> \
     -b crashlytics-<short-id> <base>
   ```
   `<base>` is `origin/<default-branch>` or the earlier issue's branch name,
   per the exception above.
4. **Do all remaining work for this issue in that worktree directory** — the
   rest of Step 6's fix, Step 7's commit/push/`gh pr create`. Run test
   commands (`flutter test`, `dart format`, `gen_mocks.sh`, `pod install`)
   scoped to the worktree path, not the original repo dir.
5. **Remove the worktree once the PR is open** — see the cleanup step at the
   end of Step 7. This deletes only the local checkout; the branch itself
   stays on the remote (already pushed) and continues to back the open PR.
   Never pass `--force` to `worktree remove` over uncommitted changes — if
   removal is blocked, check what's uncommitted before forcing anything.

### Write the fix

- Follow this repo's Dart/Flutter conventions (see root `CLAUDE.md`) — invoke
  the `flutter-widget` skill for widget-shaped fixes.
- Add or extend a test that reproduces the crash scenario so it can't
  regress — see the `flutter-test` skill for conventions (flat `test()`
  list, one test per branch, `StubbedManagers`, etc.).
- **Verify the test is a faithful reproduction, not a false positive**,
  especially for widget tests exercising framework-internal state (Navigator
  stacks, timers, animations) rather than a simple app-code branch. Before
  finalizing: temporarily revert the fix using `Edit` (never `git stash` —
  this repo's standing guidance is to never use git stash for debugging
  isolation, since it disturbs the working tree/staging area) and confirm
  the new test fails with the *same* exception type/message/stack signature
  as the Crashlytics report — not a different, unrelated failure. Then
  reapply the fix and confirm it passes. A test that "passes" without ever
  having been run red proves nothing; one that fails for the wrong reason
  means the reproduction doesn't actually exercise the crashing path.
- Run the affected tests (and `dart format`) before proposing a PR — use the
  `run-flutter-tests` skill or a targeted `flutter test` run scoped to the
  changed files.
- List possible side effects of the fix (per the collaboration preference in
  `CLAUDE.md`) before moving to the PR step.

---

## Platform label (`ios` / `android`)

Every PR opened in Step 7, and any pre-existing GitHub issue linked from a
Crashlytics note (Step 3), must carry the label matching the crash's
platform.

1. **Determine the platform** from the `appId` you already fetched for the
   issue — the same string used to build the Crashlytics link in the final
   report. It's a colon-delimited string like
   `1:1018039459325:android:f4b10d819dbf3934` or `1:...:ios:...`; the
   `android`/`ios` segment is the platform. No extra API call needed.
2. **Ensure the label exists** in the target repo before using it — both
   `gh pr create --label` and `gh issue edit --add-label` fail if the label
   isn't already defined. Check once per repo (not per issue):
   ```bash
   gh label list --repo <owner>/<repo> --search ios
   gh label list --repo <owner>/<repo> --search android
   ```
   Create whichever is missing:
   ```bash
   gh label create ios --repo <owner>/<repo> --color 000000 --description "iOS-specific"
   gh label create android --repo <owner>/<repo> --color A4C639 --description "Android-specific"
   ```
3. **Apply it**:
   - PR (Step 7): pass `--label ios` or `--label android` to `gh pr create`.
   - Pre-existing linked issue (Step 3): if it doesn't already carry the
     platform label, add it with
     `gh issue edit <n> --repo <owner>/<repo> --add-label ios`/`android`.

---

## Step 7 — Open the GitHub PR (pre-authorized, scoped to this skill)

**Override, specific to `crashlytics-triage` fix branches only:** committing,
pushing to a non-`main`/`master` branch, and running `gh pr create` proceed
without asking for per-PR confirmation. The user pre-authorized this
explicitly (2026-08-15) because it's narrow: crash fixes only, never touching
`main`/`master` directly.

This override does **not** relax anything else. Regardless of skill, always:
- Never push to `main`/`master` — branch name must not be either.
- Never force-push.
- Never merge the PR — opening it is as far as this skill goes.
- Never skip hooks (`--no-verify`) or bypass signing.

Branch naming: **`crashlytics-<short-issue-id>`** (prefix is `crashlytics-`,
not `fix/crashlytics-`) — already created as part of the worktree in Step 6.
Commit and push from **within that issue's worktree directory**, not the
original repo dir (`Pro-IQ-Inc/pro-iq` is an SSH remote — confirm
`gh auth status` covers it before relying on `gh pr create` there). Pass
`--base <default-branch>` to `gh pr create` using the default branch name
already determined in Step 6 — don't look it up again, and don't guess.
Also pass `--label ios` or `--label android` per the **Platform label**
section above.

**Cleanup — once the PR is created:** remove this issue's worktree before
moving on:
```bash
git -C <repo-dir> worktree remove ../<repo-name>-crashlytics-<short-id>
```
The branch stays on the remote (already pushed) and continues to back the
open PR — only the local worktree checkout is removed. Do this before
continuing to Step 8; Step 8's Crashlytics calls don't need repo file access.

PR description must include, in addition to the usual Summary + Test plan:
- **Why the crash happens** — the actual root cause from Step 4/5 (e.g. "X
  is called before Y is initialized because Z"), not just a restatement of
  the exception/stack trace. This is separate from the reproduction steps
  below — one explains the trigger, the other explains the mechanism.
- **Reproduction steps for the crash**, derived from the stack trace and
  sample events (user action sequence, input state, or conditions that
  trigger it) — if the events don't give enough to reconstruct concrete
  steps, say so explicitly rather than inventing plausible-sounding ones.
- The Crashlytics issue reference.
- For third-party crashes (Step 5): package name/versions, the
  changelog/issue link found (or that none was found), and — for the
  defensive-guard path — why no library fix was available and what the guard
  does.

Once the PR is open, immediately continue to Step 8 — don't stop and wait
here.

---

## Step 8 — Close the loop (pre-authorized, automatic on PR open)

As soon as a PR from Step 7 is open, without asking:

1. `crashlytics_create_note` on the issue with a note containing the PR URL.
2. `crashlytics_update_issue` to close/resolve the issue.

This happens at **PR-open time**, not at merge time — the user wants the
Crashlytics issue closed as soon as the fix is up for review, not later. Same
pre-authorization basis as Step 7 (2026-08-15): narrow, specific to this
skill's own crash-fix issues, doesn't extend to any other Crashlytics issue
mutation outside this flow.

After both calls, report the issue ID + PR URL pair so the user has a record,
even though nothing here required their approval first.

---

## Running across projects

Default scope is **all three projects**, one at a time — repeat Steps 1–8 per
project sequentially. If the user's prompt named a single project (Step 0),
run Steps 1–8 for that one project only.

When fixing multiple issues in the same repo during a run, keep a running
note of which files each issue's branch touched (from its `git diff`) — Step
6's worktree-base exception needs this to decide whether the next issue's
fix is related enough to stack on an earlier branch, versus branching fresh
from the default branch as usual.

---

## Final report

Always end the run — single-project or all-projects — with a markdown table,
one row per Crashlytics issue touched (not per PR; the outdated-issue path
has no PR):

| Issue | Platform | Resolution | Crashlytics | PR |
|---|---|---|---|---|
| `<issue title, short>` | `ios` / `android` | Fixed — library upgraded to `x.y.z` / Fixed — defensive guard added / Fixed — app code / Closed — outdated / Muted (or left open / closed, per user choice) — no app-fixable resolution / Root-caused, not fixed (user opted out) | [Open](<console-url>) | [#123](<pr-url>) or `—` |

- **Platform**: from the same `appId` segment used for the Crashlytics link
  below — matches the label applied per the **Platform label** section. If
  the `gh label create` fallback in that section had to run (label didn't
  already exist in the repo), note that here too.
- **Crashlytics link**: `https://console.firebase.google.com/v1/appid/project/<projectId>/crashlytics/app/<appId>/issues/<issueId>`
  (confirmed format, 2026-08-16 — `appId` is the full Firebase app ID string
  like `1:1018039459325:android:f4b10d819dbf3934`, taken directly from the
  `appId` you already used to fetch the issue, not `platform:bundleId`).
- **PR link**: the URL `gh pr create` returns. Use `—` for outdated-issue and
  no-app-fixable-resolution rows, since those never reach Step 7.
- **Resolution** should be specific enough to skim: which of the Step 4/5/8
  outcomes applied, not just "fixed".
- If a fix might also resolve **other** Crashlytics issues referenced in the
  same linked GitHub issue thread but outside this run's scope, say so in the
  closing note (Step 8) and in the final report row — gives the user a
  pointer to verify later without expanding this run's scope now.
- Post this table once at the end of each project's run, then a single
  combined table at the very end when running the default all-projects
  scope, so the user gets both per-project detail and one final overview.
