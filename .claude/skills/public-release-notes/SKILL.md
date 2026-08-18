---
name: public-release-notes
description: >
  Writes the customer-facing "What's New" copy for a Flutter sub-project's
  next App Store / Google Play submission, and adds matching entries to the
  app's in-app change log page (if it has one) so the two stay in sync. Use
  when the user says things like "what's new list", "release notes for the
  app store", "app store description for this release", "update the change
  log page", "changelog for the next version", or asks to prepare
  submission copy for anglers-log, pro-iq, or another sub-project. This is
  about customer-facing copy — distinct from `github-releases` (tags/GitHub
  release bodies with commit hashes) and `github-release-testing-checklist`
  (internal QA checklists); don't reach for those when the user wants
  wording a customer will actually read.
---

# Public Release Notes Skill

Turns the commit range since a sub-project's last tagged release into (1)
copyable "What's New" text for App Store Connect / Play Console, and (2)
matching rows in the app's in-app change log page, if the project has one.
Built from a real anglers-log v2.7.19 run — see that project's
`mobile/lib/pages/onboarding/change_log_page.dart` and
`mobile/lib/l10n/localizations_en.arb` for a worked example of the pattern
described below.

---

## Terminology

| Term | Meaning |
|---|---|
| **sub-project** | The Flutter app being released (e.g. `anglers-log`, `pro-iq`) |
| **sub-project dir** | Local path, e.g. `/Users/cohen/Documents/flutter-projects/anglers-log` |
| **`{version}`** | The upcoming release version, e.g. `2.7.19` |
| **change log page** | The in-app screen listing past release notes, if the sub-project has one — project-specific, located in Step 4 |

---

## Project reference table

The languages a sub-project ships copy in, and whether it has an in-app
change log page — used throughout this skill so you don't have to
rediscover either fact each run. Keep this updated as projects gain
languages or grow/drop a change log page.

| Sub-project | Languages | Change log page |
|---|---|---|
| Anglers' Log | English, Spanish | Yes |
| Activity Log | English | No |
| Pro IQ | English | No |

If the sub-project isn't in this table, ask the user which languages it
ships copy in and whether it has an in-app change log page (or discover
the latter yourself via the grep in Step 4), then add a row here so future
runs don't have to ask again.

**Don't try to find or update a change log page for a "No" project** —
Activity Log, for instance, has none. Skip straight to Step 6 for those.

---

## Step 1 — Determine sub-project and version range

1. Ask which sub-project if not already clear from context.
2. Find the last tagged release:
   ```bash
   cd <sub-project dir>
   git fetch origin --tags -q
   git tag --sort=-version:refname | grep '^v' | head -1
   ```
3. Check the current (unreleased) version in `pubspec.yaml` — this is
   normally the `{version}` the notes are being written for.
4. **A tag existing doesn't guarantee it got release notes.** If the
   **project reference table** above says this sub-project has a change
   log page, check whether its newest entry actually matches the last tag.
   A version can get tagged and shipped without ever picking up a
   changelog row — anglers-log's `v2.7.18` did exactly this. If you find a
   gap, mention it to the user; they may want that version backfilled with
   a single terse row (see the note at the end of Step 5) alongside the
   current release's notes.

---

## Step 2 — Read every commit since the last tag, not just its subject line

```bash
git log v{prev-version}..HEAD --oneline
```

A commit subject is a hint, not the truth. For each commit:

```bash
git show --stat <sha>
git show <sha> -- <the files that actually changed>
```

You're looking for what a user would actually notice — the subject line
"Updates for lib's permission utils changes" tells you nothing about
whether that's user-visible; the diff does. This step is what separates a
useful What's New list from a changelog nobody trusts.

---

## Step 3 — Filter to user-facing changes

**Include:** bug fixes a user would notice (crashes, incorrect behavior,
visual glitches), new features, meaningful UX improvements.

**Exclude:** internal refactors, dependency/library migrations with no
behavior change, code cleanup, changes made purely to match an internal
library's updated API, CI/build config changes, and cosmetic tweaks too
minor to be worth a customer's attention (use judgment — a text-color fix
on a rarely-seen screen usually isn't worth a line; a fixed crash always
is).

**Keep the copy platform-neutral.** Even when a fix is iOS- or
Android-specific under the hood, don't say so in the notes — "Fixed a
crash when picking photos," not "Fixed a crash when picking photos on
iOS." Customers on the other platform don't need to know, and it reads as
more polished. This applies to the copyable text and any in-app changelog
entries alike; if the user later asks to strip a platform reference,
apply the edit in both places so they don't drift apart.

---

## Step 4 — Find the change log page, and match its existing voice

Check the **project reference table** first. If it says "No" for this
sub-project, there's nothing to find — skip Step 5 entirely and go
straight to Step 6.

If the table says "Yes" (or the project is new and you're finding out for
the first time), locate the actual file — its path is project-specific,
so discover it fresh rather than assuming anglers-log's location:

```bash
grep -ril "changelog\|change log\|what's new\|whats_new" <sub-project dir>/**/lib
```

If the table said "Yes" but nothing turns up, the table is stale — tell
the user and update the row. If you're checking a project not yet in the
table and nothing turns up, record "No" for it, produce the What's New
text from Step 6 only, and stop there — don't invent a page.

If a page exists, **read its recent entries before writing new ones** and
match their voice. Observed anglers-log conventions (yours may differ —
read the actual file):

- "Fixed an issue where X." / "Fixed a crash when/in X." / "Improved X." /
  feature statements like "X can now be Y."
- One short sentence per bullet. Plain language. No jargon, no ticket or
  PR numbers.

---

## Step 5 — Update the change log page (project-specific pattern)

The mechanics differ per project — adapt to what you actually find rather
than forcing the anglers-log shape below onto a different codebase. That
said, the anglers-log pattern is a fully worked example and a reasonable
default if the target project's page is structurally similar (an
ARB-localization-driven Flutter widget):

- Each version is its own `_buildX_Y_Z(BuildContext context)` method
  returning an `ExpansionListItem`. Only the **newest** version's entry has
  `isExpanded: true` — every other entry must be `false`. When you add a
  new newest version, flip the previously-newest entry back to `false`.
- The new version's call goes at the **top** of the children list in
  `build()`, and its `_build*` method is placed first among the `_build*`
  methods (reverse chronological order, newest first, in both places).
- Each bullet is `BulletListItem(Strings.of(context).changeLog_{digits}_{n})`,
  where `{digits}` drops the dots from the version (`2.7.19` → `2719`) and
  `{n}` is a 1-based index within that version.
- Add the string keys to **every locale ARB file** the project maintains
  (e.g. `localizations_en.arb` and `localizations_es.arb` for anglers-log —
  check what's actually there). Translate non-English entries directly and
  naturally, matching the domain's tone — never placeholder text. New keys
  don't need to be inserted in strict version order in the ARB file; put
  them next to the most recently-added version's keys. No `@`-metadata
  block is needed for plain strings with no placeholders.
- After editing any `.arb` file, regenerate with `flutter gen-l10n` from
  the sub-project's Flutter root. This touches generated files under
  `lib/l10n/gen/` — expected, never hand-edit those.

**Backfilling a missed version:** if Step 1 turned up a tagged-but-empty
version, it's fine to add its row too (in correct chronological position,
collapsed — `isExpanded: false`), even with just one short bullet the user
supplies or you infer from that version's own commit range.

---

## Step 6 — Output the copyable What's New text

Give this directly in the chat response as plain text, not only as a repo
diff — it's meant to be pasted straight into App Store Connect / Play
Console. Use `-` dashes, not bullet glyphs. Produce one block per language
listed for this sub-project in the **project reference table**, matching
wording 1:1 with whatever you just added to the change log page (or, for
"No" projects, the same filtering and voice you'd otherwise have applied)
— same filtering, same platform-neutral phrasing, same voice.

```
- Fixed a crash on startup for some users with automatic cloud backup enabled
- Fixed a crash when picking photos
- Fixed a crash in the onboarding flow
- Improved error handling when camera access is denied while adding a photo
```

**English spelling: check for a US/Canadian split.** anglers-log's base
`localizations_en.arb` is Canadian English (e.g. "colour," "cancelled"),
with a separate `localizations_en_US.arb` overriding only the words that
differ for US spelling — see this repo's Flutter conventions on
`_en_US.arb`. Apply the same logic here: after drafting the English
block, check whether any word in it has a different US spelling
("colour"/"color", "cancelled"/"canceled", "behaviour"/"behavior," etc.).
If none of the release's wording touches a word like that, one "English"
block is enough. If it does, produce two labeled blocks — "English (US)"
and "English (Canada)" — differing only in those specific words, the same
way the ARB override only carries the words that actually diverge.

If the user later asks for a wording change (e.g. "remove platform
references," "shorten this one"), apply it to **both** the copyable text
and the ARB entries in the same pass — these two outputs represent the
same release notes and should never be allowed to drift apart.

---

## Step 7 — Don't commit unless asked

This skill edits source files (ARB, generated l10n, the change log page)
but produces no `gh` or publishing side effects on its own — the copyable
text lives in the chat response, not in a GitHub release. Leave the
working tree as edited but uncommitted, per the repo's normal git
discipline, unless the user explicitly asks you to commit.
