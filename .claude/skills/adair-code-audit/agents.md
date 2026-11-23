# adair-code-audit — agent checklists

Part of the `adair-code-audit` skill ([SKILL.md](SKILL.md)), Step 2. Give
each agent its section below in full, plus the scope sentence from Step 2
and any additions from the affected submodules' project-level files.

## Agent 1 — Bugs & Crashes

Universal Flutter checks:

- **Uncaught force casts** — `value as SomeType` without a surrounding try/catch can
  throw `CastError`. Prefer an `is` check or wrap with try/catch + logging.
- **Empty or logging-free catch blocks** — every `catch` must at minimum log the
  exception. Silent swallowing hides real failures.
- **`setState` or `context` after async gap without `!mounted` guard** — any use of
  `setState`, `Navigator`, or `context` following an `await` must be preceded by
  `if (!mounted) return;`.
- **Unhandled stream errors** — `.listen()` calls without `onError`. Note: if the stream
  already calls `.handleError()` upstream, the absence of `onError` on `.listen()` may be
  intentional — check before flagging.
- **Futures not awaited** — calls to async methods whose return value is discarded
  (`unawaited` futures) can silently fail.
- **Removed guards and validation checks** — when the diff deletes a guard, early
  return, or sign-in/role check, work out which inputs it used to reject (e.g. a
  user with no roles) and follow them through the new code path. Also grep
  `test/` for tests that still assert the old behavior or a removed string.
- **Caller stops logging because the callee "logs everything"** — when the
  diff removes a caller's `_log.e` because the callee now logs before
  rethrowing, check every throwing path in the callee: code before its
  `try`, synchronous throws from calls that start async work (e.g. a
  `putFile` before the `try` that awaits it), and any "already logged"
  skip conditions (e.g. a step label) that also cover later code.
- **Leftover debug overrides** — a getter or flag hardcoded to a constant in the
  diff (e.g. `bool get isPro => true;` replacing a real state check), often in a
  file unrelated to the rest of the change. Always critical: it ships to every
  app that depends on the file.
- **Page teardown of app-lifetime singleton state** — a page's `dispose()` that
  closes a manager's `StreamController`s or cancels listeners the manager only
  creates once in `init()`. After sign-out → sign-in (same app launch), the
  page is rebuilt but the manager isn't re-initialized, so the feature silently
  stops working. Trace what `init()` creates against what `dispose()` tears
  down.
- **State that was previously recomputed per-build now cached in a field** — when a
  refactor (e.g. a platform-branching cleanup) moves a value that used to be read fresh
  from a live object on every build (e.g. `controller.value.aspectRatio` inside
  `build()`) into a field that's only assigned once (e.g. on initial load), check every
  other place the underlying live value can change (advancing to the next item in a
  list/queue, seeking, switching tabs) and confirm the field is updated there too.
  Diff the before/after data flow, not just the before/after widget tree.

If the project uses **Firestore + protobuf**, also check:

- **Missing `clearId()` (or equivalent) before writes** — ID fields derived from document
  IDs must be cleared before serializing to Firestore. Look for the project's pattern
  (e.g., `..clearId()` before `.toProto3Json()`) and flag write paths that skip it.
- **Proto/value-type null checks** — fields that default to a zero-value (empty string,
  0, false) must be guarded with `.isEmpty` / `== 0` etc., not null checks.
- **Proto presence-check pattern by field type** — `string` fields must use
  `.isEmpty`/`.isNotEmpty`; every other field type (numeric, message, enum, etc.) must
  use the generated `has*()` method. Flag a `string` field checked via `has*()`, or a
  non-string field checked via a manual default-value comparison. If the same field is
  checked both ways at different call sites in the diff, that's a stronger signal.
- **Eagerly-started side-effecting futures not tracked for cleanup on failure** — when
  code kicks off an async side effect (e.g. an upload) that writes to external storage
  before or during a `try` block, check whether that side effect's target path is
  recorded somewhere a failure-cleanup mechanism (e.g. an "orphan cleanup" pending-doc
  pattern) can find it — even if the side effect itself swallows its own errors and
  never throws. A future that "never throws" can still leak state if nothing tracks
  what it wrote.

Check that `FutureBuilder` and `StreamBuilder` are never used directly — they must be
replaced with `AsyncBuilder.future` / `AsyncBuilder.stream` (from
`package:adair_flutter_lib/widgets/async_builder.dart`). The `errorReason` parameter
is required on every `AsyncBuilder` instance.

## Agent 2 — Coding Convention Violations

Checks the changed code against the `flutter-conventions` skill. Brief the
agent with the full text of `.claude/skills/flutter-conventions/SKILL.md`
and `tests.md`, plus `firestore-protos.md` when the submodule uses
Firestore, and the convention rules from each affected submodule's
project-level file. Don't summarize them; the agent needs the exact rules
and their exceptions.

The rules most often missed in review, to call out in the briefing:
- Double quotes (except `import`/`export`), curly braces on every `if`, and
  `== null` ordering in ternaries.
- Magic numbers, `final` fields that could be `static const`, boolean
  naming, and `_` for unused parameters.
- `build()` placement and `_build*` + early `SizedBox()` for conditional
  widgets.
- Dead imports.

## Agent 3 — Code Quality & Duplication

- **Identical private methods across files** — the same `_buildError()`, `_buildLoading()`,
  or similar helper appearing verbatim in multiple files is a candidate for a shared widget
  or mixin.
- **Repeated inline widget structures** — the same structural pattern (e.g.,
  `Row([Icon, SizedBox, Text])`) appearing in 3+ methods in the same file is a candidate
  for a private helper method.
- **`setState` inside `try`/`catch`** — the correct async pattern is a single `setState`
  call at the end of the method, after the try/catch block. An opening `setState` to set
  busy/loading state at the top is fine; one inside `try` or `catch` is not.
- **Error state not cleared at the start of a save** — async save methods that show
  inline errors should reset the error field (`_error = ""`) alongside the busy flag in
  the opening `setState`, so stale errors don't persist into the next attempt.
- **Architecture violations** (if the project uses a wrapper/manager pattern):
  - Business logic inside wrappers (wrappers should be thin, 1:1 SDK delegations to a
    single third-party library — they must not call other wrappers).
  - Generic-enough wrappers or managers living in a sub-project that should be moved to
    `adair-flutter-lib`.
  Note: managers may freely call other managers. Only wrappers are prohibited from
  cross-dependency.
- **Naming-issue TODOs** — TODO/FIXME comments that explicitly call out a misleading or
  wrong name (class, method, variable, file) are a finding. List them — they represent
  confirmed tech debt.
- **Dead or unreachable code** — unreferenced variables, methods, or classes, and
  branches that can never execute given the surrounding logic. For every changed/audited
  file, reason through each `if`/`else`, guard clause, and null check: is there an
  earlier guard that makes a later branch unreachable? Is there a null check on a value
  already asserted non-null? Report these explicitly rather than silently deleting code
  — the user may know a reason it's there.

## Agent 4 — Efficiency & Firebase Cost

Findings from this agent are lower-confidence than bugs — many are legitimate
tradeoffs, not defects. Flag them as suggestions, not required fixes, and let
the user decide during review (Step 4).

**Code efficiency**
- **Expensive work inside `build()`** — sorting, filtering, or mapping a list on every
  rebuild instead of memoizing/caching the result outside `build()`.
- **Missing `const` constructors** — widgets that could be `const` but aren't, causing
  avoidable rebuilds.
- **Heavy synchronous work on the UI thread** — CPU-bound work (parsing, image
  processing, large collection transforms) that should move to `compute()` or an
  isolate instead of blocking the frame.
- **Repeated redundant computation** — the same derived value recomputed in multiple
  nearby methods instead of computed once and reused.
- **Nested-loop lookups** — an `O(n*m)` search (looping a list inside a loop) where a
  `Map`/`Set` lookup would be `O(n)`.
- **Loading a full list into memory** where pagination or streaming would do (e.g. a
  `ListView` fed by a fully-materialized list instead of `ListView.builder` with lazy
  data).
- **App-lifetime polling** — a `Timer.periodic` (network probe, location or
  status poll) that runs for the whole session, including in the background,
  drains battery and keeps the cellular radio awake. Check who consumes the
  value; if it's only read occasionally (e.g. on failure), prefer measuring on
  demand or an event-driven source.

**Firebase cost efficiency** (only when the project/submodule uses Firebase — check
`pubspec.yaml` before running these checks; skip entirely otherwise)
- **Unbounded queries** — Firestore queries missing `.limit()`.
- **Over-fetching** — reading an entire collection where a targeted query or a
  single-doc `get()` would work.
- **N+1 query patterns** — looping single-document fetches instead of a batched or
  `whereIn` query.
- **Long-lived or leaked listeners** — `.snapshots()` subscriptions that outlive their
  need, or aren't cancelled in `dispose()`.
- **Listening to a whole collection** when only specific documents are actually used.
- **Redundant writes** — writes that set fields to their already-current value, or
  frequent small writes that could be batched into one.
- **Full Storage object downloads** where only metadata (size, content type) is needed.
