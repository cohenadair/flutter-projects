# Troubleshooting reference

Every non-obvious problem hit while working in this monorepo, what caused
it, and what fixed it. Written for Claude; readable by anyone.

## Using it

- **Before debugging** a build, tool, test, device, or API error, search
  here for the exact error text:
  `grep -rn "<distinctive part of the error>" .claude/troubleshooting/`
  Also search for the tool or file name if the error text is generic.
- **After resolving** anything that took more than one attempt, or whose
  fix wasn't obvious from the error, add an entry (or update the one that
  was wrong). Commit it with the fix, or on its own.
- If an entry's fix no longer works, don't delete it: add what changed under
  **Didn't work** with the date, then the new fix.

## Files

| File | Covers |
|---|---|
| [ios-xcode-spm.md](ios-xcode-spm.md) | iOS/macOS builds, Xcode, Swift Package Manager, simulators |
| [android.md](android.md) | Android builds, Gradle/AGP/Kotlin, the emulator |
| [flutter-dart.md](flutter-dart.md) | Flutter framework, Dart compiler, l10n, tests and mocks |
| [firebase.md](firebase.md) | Firebase CLI and MCP servers, Crashlytics, Firestore, emulators |
| [release-and-stores.md](release-and-stores.md) | Release builds, App Store Connect, Google Play, attribution |
| [meta-ads.md](meta-ads.md) | Meta Ads MCP tools and Ads Manager |
| [tooling.md](tooling.md) | git, worktrees, shell, Next.js, other dev tooling |

Error tables that a skill acts on stay in that skill, and are not copied
here:
- `build-and-upload-release` → Step 9, **Known fixable categories** and
  **Not auto-fixable**
- `store-release` → Step 7, **Handle errors**

## Entry format

```markdown
### <short symptom, as you'd search for it>

- **Symptom:** the exact error text or observed behavior.
- **Seen:** <project(s)>, <YYYY-MM-DD>.
- **Cause:** the mechanism, not a restatement of the symptom.
- **Fix:** what resolved it (commands, file:line, settings).
- **Didn't work:** (optional) what was tried and why it failed.
- **Related:** (optional) skill, memory, PR, or other entry.
```

Newest entries go at the top of each file's section. Keep the exact error
text verbatim so grep finds it. Never include secrets, keys, or personal
data.
