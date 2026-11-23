# Firebase

## CLI & MCP servers

### `firebase deploy` from `pro-iq/` targets the wrong project

- **Seen:** pro-iq (left pointing at `anglers-log`; date not recorded).
- **Cause:** calling `firebase_update_environment` (either MCP server) or
  `firebase use` writes a per-directory `active_project` override into
  `~/.config/configstore/firebase-tools.json`. It persists after the session
  and outranks each repo's `.firebaserc`.
- **Fix:** remove the override from that file. Never change the active
  project; every `crashlytics_*` tool takes an explicit `appId`.
- **Related:** `crashlytics-triage` → Never change the Firebase CLI's
  active project.

### Firestore MCP tools hit production, not the emulator

- **Cause:** the Firebase plugin's `mcp__plugin_firebase_firebase__firestore_*`
  tools talk to the production `pro-iq` project.
- **Fix:** seed only through the local emulator (REST API or emulator UI).
  The read-only tools are fine for looking up a production document's shape.
- **Related:** `reproduce-bug` Step 5.

### No `crashlytics_*` tools in ToolSearch

- **Cause:** two Firebase servers load. The plugin's server has no
  Crashlytics tools; the `.mcp.json` server (`mcp__firebase__*`) does, and
  needs a session restart to pick up `.mcp.json` changes.
- **Fix:** search `+firebase crashlytics`; if still missing, restart the
  session.

## Crashlytics

### `crashlytics_get_issue`: `HTTP Error: 404, Requested entity was not found`

- **Cause:** the issue belongs to the app's other platform; issue IDs are
  per `appId` (e.g. an Android issue looked up with the iOS `appId`).
- **Fix:** retry with the other platform's `appId` from the
  `crashlytics-triage` project table.

### `crashlytics_get_report`: `Timeout reached making request`

- **Cause:** a slow Crashlytics API response, usually for a large window.
- **Fix:** retry that one call once; the other calls in the batch are
  unaffected. If it times out again, shorten the window or lower
  `pageSize` and say so in the report.

### `crashlytics_get_report` interval error: "must be less than 90 days in the past"

- **Fix:** use a start time ~85 days back, not exactly 90.

### Reading the Crashlytics reports guide

- **Symptom:** `crashlytics_get_report`'s description points to a
  `firebase_read_resources` tool the `.mcp.json` server doesn't expose.
- **Fix:** `ReadMcpResourceTool` with `server: "firebase"` and
  `uri: "firebase://guides/crashlytics/reports"`.

### SKAN `SKANErrorDomain error 10` non-fatals

- **Symptom:** `SKAdNetwork.updatePostbackConversionValue` fails with
  `SKANErrorDomain error 10` (`SKANErrorUnknown`) on every launch of
  affected devices (Crashlytics `e65da98e…`).
- **Seen:** anglers-log and activity-log iOS, 2026-11-19. Only iOS 15.8,
  16.7, iPadOS 17.7, iOS 17.1.
- **Cause:** an old-OS quirk the app can't fix.
- **Fix:** adair-flutter-lib#24 logs code 10 with `_log.w` (matched through
  the native error's `details` `{domain, code}`). If it regresses, check
  the app's lib bump first.
- **Related:** memory `project_skan_error_10_testflight.md`.
