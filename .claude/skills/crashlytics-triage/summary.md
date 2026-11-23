# Summary mode

Read-only: fetches and summarizes issues, then renders them as a self-contained
HTML page. Never writes a Crashlytics note, never closes/updates an issue,
never touches git or GitHub. The output is meant to be handed back to this
skill in **Fix mode** — the user picks issues by Reference ID.

## SM-1 — Scope

Ask the user only for what isn't already implied by their request:

1. **Which project(s)?** Defaults to **all four** (see the projects table
   in [SKILL.md](SKILL.md)). If the user names one, scope to that one only.
2. **Time window?** Defaults to the last ~85 days (the widest range the
   Crashlytics API allows — see Prerequisites in SKILL.md).
3. **Issue state?** Defaults to **open/unresolved** issues only, since those
   are the ones worth acting on. Include closed/resolved issues only if the
   user asks (e.g. "include resolved ones too") — the `state` field is
   already on every row returned in SM-3, so this is a filter on data
   already in hand, not an extra call.

Fatal and non-fatal issues are always both included — that distinction is a
column in the output, not a filter.

## SM-2 — Enumerate apps

For each project in scope, take its `appId`s from the **Firebase projects
covered** table in SKILL.md — no active-project switch (see **Never change
the Firebase CLI's active project** there). Every call below is per-`appId` — a project with
both an Android and iOS app produces two separate sections (platforms aren't
comparable — see the multi-platform note in [fix.md](fix.md) → Step 2).

## SM-3 — Fetch issues per app

For each `appId`:

1. Call `crashlytics_get_report` once per error type —
   `filter.issueErrorTypes: ["FATAL"]`, `["NON_FATAL"]`, and, for Android
   `appId`s only, `["ANR"]` — each with `report: "topIssues"`, the SM-1
   time window, and a generous `pageSize` (start at 100). Separate calls,
   not one combined filter, so each issue can be tagged Fatal/Non-fatal/ANR
   by which call surfaced it. ANRs (app freezes) are Android-only; the iOS
   apps never report any, so skip that call for them. Tracked since
   2026-11-19 at the user's request; before that, ANRs were left out of
   every mode.
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

## SM-4 — Fetch the last event per issue

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

## SM-5 — Classify and infer origin

For every issue, using its `blameFrame` and full stack trace from SM-4:

1. **Stack trace classification** — path-based on `blameFrame.file`, *not*
   `blameFrame.owner` (confirmed live: `owner` is `DEVELOPER` for both true
   app code *and* third-party pub packages like `protobuf` or
   `cloud_firestore_platform_interface` — it only distinguishes an
   attributable Dart/JVM/ObjC frame from a native one, it does not mean
   "the app's own code"). Apply the same three buckets as fix.md → Step 4:
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
   This is the same reasoning fix.md → Step 4 does before proposing a fix —
   here it's surfaced to the user instead of acted on.

## SM-5b — Fix-status cross-reference

Run **Fix-status cross-reference** in [SKILL.md](SKILL.md) for every issue from
SM-3. Its result fills SM-7's Fix status column.

## SM-6 — Cross-platform duplicate detection

For each project with issues on both Android and iOS, flag any pair that's
likely the same underlying bug surfacing on both platforms (common for
anglers-log/activity-log/tapd, whose Dart code is shared across platforms).

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

## SM-7 — Render as a single-file HTML page

Write one self-contained `.html` file (no external requests, inline CSS/JS)
to `~/Downloads/crashlytics-summary-<YYYYMMDD-HHMM>.html` and deliver it to
the user (`SendUserFile`) — don't just paste markdown tables into chat, the
volume (often 30–50+ open issues across four projects) is unreadable that
way.

**Always declare `<meta charset="UTF-8">` as the first tag in `<head>`.**
A file delivered with `SendUserFile` gets no injected charset, and without
the tag em dashes and `·` render as mojibake (`â€”`; see
`.claude/troubleshooting/tooling.md`). Add the tag before any other
content, and before delivering, check `file <path>` says "UTF-8 text" and
`grep -c "â€" <path>` is 0.

Structure:

- One section per project, then per platform within it (same grouping as
  SM-2/SM-3), each with its own table, in the order the projects table in SKILL.md
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
- Table columns: Reference ID, Type (Fatal/Non-fatal/ANR badge), Occurrences,
  Last Occurred, Affected Users, App Version Range, Stack Trace
  (App code/Third-party/Unknown-native badge), Cross-Platform (SM-6 — a
  badge naming the matched platform + issue ID as a tooltip, or an em-dash
  if no match), Likely Origin (the SM-5 sentence), Fix status (from
  **Fix-status cross-reference** — the status text with the PR/commit
  linked, or an em-dash).
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
  30–50 issues across four projects is a lot to page through, so letting
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
  for expand/collapse (the row-expand bullet above); without `stopPropagation` a copy click
  also toggles the row open/closed. Confirmed live (2026-08-19): clicking
  the actual button (not just near it) leaves the row's expanded state
  untouched, and the OS clipboard visibly updates.
- Keep the visual style consistent with this codebase's dark-UI conventions
  (see this run's output for a working reference: dark background, colored
  badges for Fatal/Non-fatal/ANR and the three origin buckets, monospace for IDs
  and stack traces).
- After writing the file, open it in the browser preview tool and click a
  row to confirm the expand/collapse interaction actually works, and click a
  copy button specifically (via its element ref, not just an approximate
  coordinate) to confirm it copies without toggling the row — a static
  screenshot doesn't prove either interaction actually works.
- Close the chat reply with a one-line reminder: give me the Reference
  ID(s) (and project, if ambiguous) from the page and say "fix" to hand them
  to Fix mode.

## SM-8 — Stale/duplicate candidates (only when asked, and only with confirmation)

Triggered by a follow-up like "which of these are stale" or "summarize
what's stale" — not part of the default SM-1–SM-7 flow.

- **This is not pre-authorized**, unlike fix.md's outdated-issue path
  (Step 4) or fix.md Step 8's close-on-PR-open — Summary Mode never mutates
  Crashlytics without the user explicitly saying so for that batch of
  issues. Propose candidates, then wait for a yes before calling
  `crashlytics_create_note` / `crashlytics_update_issue` on any of them.
- **Verify, don't guess from version age.** An old `lastSeenVersion` is a
  reason to *look*, not a reason to conclude staleness. For every
  App-code-classified candidate, actually read the current file at the
  blamed path (`blameFrame.file` from SM-4) and check whether the blamed
  class/method still exists and the described crash is still plausible
  there — same check as fix.md → Step 4's stale-issue rule. Confirmed live
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
- **Resolution, once confirmed** — same mechanics as fix.md's outdated-issue
  path (`crashlytics_create_note` then `crashlytics_update_issue` with
  `state: "CLOSED"`), against the confirmed issue's own `appId`:
  - **Stale**: note text `"Code is outdated."`, matching fix.md → Step 4
    exactly.
  - **Duplicate**: note text naming the canonical issue ID it duplicates,
    e.g. `"Duplicate of issue <canonical-id> (<short reason>). Closing as a
    duplicate variant."` — don't just say "duplicate", name what it's a
    duplicate *of* so the note is still useful read cold later.
- Record each closed issue in the checkpoint's `ignoredIssues` as `closed`
  (see **Checkpoint bookkeeping after acting on issues** in SKILL.md).
- After closing, **regenerate SM-7's HTML** with the closed issues removed
  from their table (don't leave stale rows in an "open issues" report) and
  a short note near the top of the page listing what was closed this
  session and why, then redeliver via `SendUserFile`. Don't silently
  reuse the old file — the whole point of a fresh render is that it
  reflects current state.
