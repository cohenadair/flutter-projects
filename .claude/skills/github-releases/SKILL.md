---
name: github-releases
description: >
  Creates coordinated GitHub releases for a Flutter sub-project and its
  associated adair-flutter-lib release. Use when the user says things like
  "create a release", "publish vX.Y.Z", or "cut a new release".
---

# GitHub Releases Skill

This skill creates a pair of GitHub releases: one on the sub-project repo and
one on `adair-flutter-lib`, both tagged at their respective HEADs.

---

## Terminology

| Term | Meaning |
|---|---|
| **sub-project** | The Flutter app being released (e.g. `anglers-log`, `pro-iq`) |
| **`{version}`** | The new version number, e.g. `2.7.13` |
| **sub-project dir** | Local path, e.g. `/Users/cohen/Documents/flutter-projects/anglers-log` |
| **lib dir** | `/Users/cohen/Documents/flutter-projects/adair-flutter-lib` |

---

## Step 1 — Confirm the version number

Ask the user for `{version}` if not already provided. Check the sub-project's
`pubspec.yaml` to verify the version matches the build that was committed.

---

## Step 2 — Determine tag names

| Repo | Tag format | Example |
|---|---|---|
| sub-project | `v{version}` | `v2.7.13` |
| adair-flutter-lib | `{project-slug}-v{version}` | `anglers-log-v2.7.13` |

The `{project-slug}` is the kebab-case project name (e.g. `anglers-log`,
`pro-iq`).

---

## Step 3 — Collect commits since last release

Find the previous release tags for each repo:

```bash
# sub-project — find the most recent vX.Y.Z tag
cd <sub-project dir>
git tag --sort=-version:refname | grep '^v' | head -1

# adair-flutter-lib — find the most recent {project-slug}-vX.Y.Z tag
cd <lib dir>
git tag --sort=-version:refname | grep '^{project-slug}-v' | head -1
```

Collect the commit log for each repo since its previous tag:

```bash
# sub-project commits (oldest → newest for the release body)
git -C <sub-project dir> log v{prev-version}..HEAD --oneline --reverse

# lib commits
git -C <lib dir> log {project-slug}-v{prev-version}..HEAD --oneline --reverse
```

> **Tip:** `--oneline` gives `<short-hash> <message>`, which is the exact
> format used in release bodies. `--reverse` puts oldest commits first,
> matching the convention established by prior releases.

---

## Step 4 — Get the Flutter version

```bash
flutter --version | head -1
# e.g. Flutter 3.41.6 • channel stable • ...
```

Extract just the version string: `Flutter X.Y.Z`.

---

## Step 5 — Write release notes to temp files

Write each release body to a temp file to avoid shell-escaping issues, then
pass it via `--notes-file`.

### adair-flutter-lib notes (`/tmp/lib-release-notes.md`)

```
Flutter {X.Y.Z}

# Changes
* {short-hash} {commit message}
* {short-hash} {commit message}
...
```

### sub-project notes (`/tmp/project-release-notes.md`)

```
# Flutter Version 
`{X.Y.Z}`

# {Project Display Name} Changes
* {short-hash} {commit message}
* {short-hash} {commit message}
...

# Adair Flutter Lib Changes
* cohenadair/adair-flutter-lib@{short-hash} {commit message}
* cohenadair/adair-flutter-lib@{short-hash} {commit message}
...
```

The `{Project Display Name}` is the human-readable name (e.g. `Anglers' Log`,
`Pro-IQ`).

---

## Step 6 — Create the adair-flutter-lib release first

Always create the lib release before the sub-project release, so the lib tag
exists when the sub-project release body references it.

```bash
gh release create {project-slug}-v{version} \
  --repo cohenadair/adair-flutter-lib \
  --title "{Project Display Name} v{version}" \
  --notes-file /tmp/lib-release-notes.md
```

`gh release create` automatically creates the tag at HEAD if it does not
already exist.

---

## Step 7 — Create the sub-project release

```bash
gh release create v{version} \
  --repo cohenadair/{project-slug} \
  --title "v{version}" \
  --notes-file /tmp/project-release-notes.md
```

---

## Step 8 — Verify

Confirm both releases are live by checking the URLs printed by `gh release
create`, or by running:

```bash
gh release view {project-slug}-v{version} --repo cohenadair/adair-flutter-lib
gh release view v{version} --repo cohenadair/{project-slug}
```

---

## Release body reference (Anglers' Log example)

**adair-flutter-lib** (`Anglers' Log v2.7.13`):
```
# Flutter Version
`3.41.6`

# Changes
* 01f3427 cohenadair/anglers-log#1099: Remove unnecessary Android paths in requestPhotosPermission
* 0b1763a Add new run_tests.sh script
...
```

**anglers-log** (`v2.7.13`):
```
# Flutter Version
`3.41.6`

# Anglers' Log Changes
* 988316b7 Update changelog and build version
* d7e0039b #1099: Use Android file picker instead of custom picker
...

# Adair Flutter Lib Changes
* cohenadair/adair-flutter-lib@01f3427 cohenadair/anglers-log#1099: Remove unnecessary Android paths in requestPhotosPermission
* cohenadair/adair-flutter-lib@0b1763a Add new run_tests.sh script
...
```
