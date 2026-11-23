# Update Me mode

Read-only against Crashlytics: fetches open issues, diffs them against a
small local checkpoint file from the last run, and reports only issues that
are new since then, plus any previously *ignored* issue (reported earlier
but left open, muted, or closed without a code fix) that is still
occurring. Never writes a Crashlytics note, never closes/updates an
issue, never touches git or GitHub. The only thing this mode writes is its
own checkpoint file (UM-2 below) — everything else reuses Summary Mode's
fetch/classify machinery ([summary.md](summary.md)) so the two modes can't drift apart on how "an
issue" is fetched or classified.

## UM-1 — Scope

Ask the user only for what isn't already implied by their request:

1. **Which project(s)?** Defaults to **all four** (see the projects table
   in [SKILL.md](SKILL.md)). If the user names one, scope to that one only.

No time-window or issue-state question here (unlike SM-1) — the checkpoint
file itself defines "since when," and only open issues are ever meaningful
to report as new.

## UM-2 — Load the checkpoint file

State lives at `~/.claude/crashlytics-triage/update-me-state.json`,
**outside every project repo** — it's this skill's own bookkeeping, not
something that belongs in git history or could get swept up in a commit.
Create the parent directory and an empty `{}` file if it doesn't exist yet.

Shape:

```json
{
  "<Firebase project ID>": {
    "<appId>": {
      "lastCheckTime": "<ISO 8601 timestamp>",
      "knownIssueIds": ["<issueId>", "..."],
      "ignoredIssues": {
        "<issueId>": {
          "status": "left-open | muted | closed",
          "since": "<ISO 8601 timestamp>",
          "note": "<short reason, e.g. the user's words>"
        }
      }
    }
  }
}
```

`ignoredIssues` tracks every issue that was surfaced to the user but **not
fixed** — so it doesn't get silently suppressed forever just because its ID
is in `knownIssueIds` (or drops out of it because it's no longer `OPEN`).
An absent `ignoredIssues` key means empty (older checkpoints predate it).
Statuses:

- `left-open` — reported as new, user didn't act on it (the default for
  every newly reported issue — see UM-8).
- `muted` — user had it muted. Muted issues never appear in UM-4's
  `OPEN`-only set, so without this entry they'd vanish from every future
  report even while still crashing.
- `closed` — user had it closed *without* a code fix (e.g. "fixed in a
  newer build", "outdated", duplicate). Crashlytics only regresses a closed
  issue when it recurs in a *newer* version, so recurrences on old builds
  stay closed and invisible without this entry.

Issues closed by a Fix-mode PR are **not** tracked here — remove their
entry (see **Checkpoint bookkeeping after acting on issues** in SKILL.md); a
recurrence regresses the issue to `OPEN` and UM-5 surfaces it as new.

Keyed by Firebase project ID, then `appId` (matches SM-2's per-app
enumeration — an Android and iOS app in the same project track
independently, same reasoning as the multi-platform note in fix.md → Step
2). If a project/appId key is absent, this is the **first-ever run** for
that app — see UM-5.

## UM-3 — Enumerate apps

Same as **SM-2** — take each project's `appId`s from the **Firebase projects
covered** table in SKILL.md. Never switch the active project.

## UM-4 — Fetch current open issues per app

Same as **SM-3** — `crashlytics_get_report` (`topIssues`, `FATAL`,
`NON_FATAL`, and `ANR` for Android apps, SM-1's ~85-day window, `pageSize` starting at 100), filtered to
`issue.state == OPEN`. The window doesn't need to align with
`lastCheckTime`; it only needs to cover every currently-open issue so the ID
diff in UM-5 is against a complete set — an issue first seen 40 days ago
that this app simply never surfaced before (new Firebase project added to
scope, a prior run that errored before reaching this app, etc.) should still
show as new to *this checkpoint*, even though it's not new to Crashlytics.

## UM-4b — Check ignored issues for recent activity

Only for appIds whose `ignoredIssues` is non-empty:

1. Call `crashlytics_get_report` (`topIssues`, `FATAL`, `NON_FATAL`, and
   `ANR` for Android apps, one call each, `pageSize` 100) with `intervalStartTime` = the app's
   `lastCheckTime` and `intervalEndTime` = now. **Don't** filter by
   `issue.state` here — muted and closed issues still appear in the report
   when they have events in the window, and those are exactly the ones this
   step exists to catch.
2. **Still occurring** = every `ignoredIssues` ID that appears in that
   result (i.e. has ≥1 event since the last check). Record its
   `eventsCount`/`impactedUsersCount` for the window, current
   `issue.state`, `lastSeenVersion`, and any `signals` (e.g.
   `SIGNAL_REGRESSED`).
3. Ignored IDs absent from the result were quiet since the last check —
   don't list them individually in the report, just count them.
4. If this fetch fails, report it inline (same as UM-7's failure rule) and
   leave that app's `ignoredIssues` untouched in UM-8.

No sample-event fetch is needed — these were already classified when first
reported. Reuse the classification from that report if it's still in the
conversation; otherwise one `crashlytics_batch_get_events` call per app for
just the still-occurring IDs is fine.

## UM-5 — Diff against the checkpoint

For each appId:

1. Compare the current open `issue.id` set (UM-4) against
   `knownIssueIds` from UM-2.
2. **New issues** = current IDs not in `knownIssueIds`. This includes an
   issue that was previously closed and has since reopened — it won't be in
   `knownIssueIds` if a prior run's UM-8 write only ever stored the
   *open* set (see UM-8), so a reopen correctly surfaces again rather than
   staying silently suppressed.
3. **First-ever run for this appId** (UM-2's key absent): every currently
   open issue counts as "new," but say so explicitly in the report (UM-7) —
   this is an initial baseline, not really 30 issues that appeared since
   yesterday. Don't let this read as a spike.

If an appId has zero new issues, it still gets a line in the report (UM-7)
— "no new issues" is a valid, useful answer, not something to omit silently
(same reasoning as Summary Mode's empty-section rule in SM-7).

## UM-6 — Classify new issues only

For issues found new in UM-5 (not the full open set — no need to re-fetch
event data for issues already known from a prior run), fetch sample events
and classify exactly per **SM-4** (blame frame, stack trace) and **SM-5**
(App code / Third-party / Unknown-native bucket, one-sentence likely
origin).

## UM-6b — Fix-status cross-reference

Run **Fix-status cross-reference** in [SKILL.md](SKILL.md) for the new issues,
any `SIGNAL_REGRESSED` issue, and the still-occurring ignored issues from
UM-4b. A regressed issue whose only fix is an open PR is called out in
UM-7 as closed before its fix shipped.

## UM-7 — Report

- **If the total new-issue count across all scoped apps is small** (rough
  guide: ≤10 — a delta since last check should usually be small): reply
  directly in chat. One short section per project/app (even the empty
  ones, per UM-5's rule), a compact markdown table per app with columns
  Reference ID, Type (Fatal/Non-fatal/ANR), Occurrences, Affected Users,
  Likely Origin, Fix status (UM-6b) — no need for the full SM-7 HTML machinery (sort/expand/
  collapse) for a handful of rows.
- **If the count is large** (a first-ever run per UM-5.3, or a long gap
  since the last check): render as an HTML page reusing **SM-7** verbatim
  (same file-naming convention, same structure, same delivery via
  `SendUserFile`), scoped to just the new issues instead of every open
  issue. Note at the top of the page that this is an Update Me run, and
  whether it's an initial baseline (UM-5.3) or an actual delta, with the
  `lastCheckTime` being compared against.
- **Still-occurring ignored issues (UM-4b)** get their own section,
  placed *before* the new-issues sections so they aren't buried: a compact
  table with Reference ID, project/app, Status (`left-open`/`muted`/
  `closed` + the stored `since` date and `note`), Events since last check,
  Users since last check, Current state, and Latest version. Call out
  explicitly when a `closed` issue is still occurring on a version *newer*
  than the one it was closed against, or a `muted` one is accelerating —
  those likely need revisiting. If none are still occurring, say so in one
  line (e.g. "6 ignored issues — none occurred since last check").
- Either way, close with the same one-line reminder as Summary Mode: give
  me the Reference ID(s) (and project, if ambiguous) and say "fix" to hand
  them to Fix mode.
- If a fetch failed for a given project/app (auth error, 404, etc.), report
  that failure inline rather than silently treating it as "no new issues,"
  and skip UM-8's checkpoint update for that specific app only — see UM-8.

## UM-8 — Update the checkpoint

Only after UM-7's report has been produced (successfully, for a given
appId):

1. Set `knownIssueIds` to the **full current open-issue-ID set from UM-4**
   for that appId (not `knownIssueIds ∪ new`) — closed issues drop out
   naturally, so a reopen is detected next time per UM-5.2.
2. Add every issue reported as **new** in this run to `ignoredIssues` with
   `status: "left-open"`, `since` = now, and a short `note` (the Likely
   Origin's gist is fine). Don't overwrite an existing entry for the same
   ID — keep its original `status`/`since`.
3. Prune `ignoredIssues` entries whose ID is absent from UM-4's **raw**
   85-day results (before the `OPEN` filter — muted/closed issues with
   events still appear there), i.e. no events in ~85 days; they've aged
   out. Don't prune just because an issue was quiet since the last check.
4. Set `lastCheckTime` to now (ISO 8601, UTC). Do this *after* UM-4b has
   used the old value.
5. Write the **whole file** back in one shot (read-modify-write the full
   JSON), not a per-app incremental patch — avoids a partially-written file
   if this step is interrupted mid-run across multiple apps.

**Skip the update for any appId whose UM-4 fetch failed this run** — leave
its existing entry untouched so the next run retries against the last
*successful* checkpoint instead of silently advancing past issues that were
never actually seen. Do not skip the update for an appId that fetched
successfully but had zero new issues — `lastCheckTime` should still advance
for it.
