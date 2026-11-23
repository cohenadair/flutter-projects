# Tooling: git, shell, Next.js

## git

### `gh release create` fails: `"workflow" scope may be required`

- **Symptom:** `! Failed to create release, "workflow" scope may be
  required. To request it, run: gh auth refresh -h github.com -s workflow`,
  and it keeps failing after the refresh (the token already lists
  `workflow`).
- **Seen:** pro-iq `v0.4.0`, 2026-10.
- **Cause:** the wrong repo owner: `--repo cohenadair/pro-iq` doesn't
  exist (`gh api repos/cohenadair/pro-iq` → 404). pro-iq is
  `Pro-IQ-Inc/pro-iq`. GitHub's error doesn't say "not found".
- **Fix:** take the owner from `git -C <repo> remote -v`.
- **Didn't work:** `gh auth refresh -s workflow`.
- **Related:** `github-releases` (repo owner note).

### `gh` fails with `HTTP 503: No server is currently available`

- **Cause:** a transient GitHub outage; an immediate retry usually fails
  too.
- **Fix:** wait a minute or two and retry once. Check whether the release
  or tag was created anyway (`gh release view`) before retrying a create.

### A git command ran against the wrong repo's remote

- **Seen:** adair-flutter-lib / activity-log, during a `github-releases`
  tag cleanup. A `git push origin :refs/tags/...` meant for activity-log ran
  in adair-flutter-lib (no `cd` before it) and deleted an unrelated,
  unrecoverable `v2.0.0` tag.
- **Cause:** relying on one leading `cd` for several repo-specific commands
  in one Bash call.
- **Fix:** `cd <repo> &&` before *every* repo-specific command, and put
  destructive multi-repo operations in separate Bash calls.
- **Related:** memory `feedback_git_multirepo_bash_cd.md`.

### `git worktree remove` refuses: "working trees containing submodules cannot be moved or removed"

- **Fix:** after checking the worktree for changes worth keeping (and
  commits not on `main`: `git rev-list --count main..<branch>`), use
  `git worktree remove --force <path>`, then `git worktree prune`.

## Shell (zsh)

### `(eval):1: = not found` / `===== not found`

- **Cause:** in zsh, an unquoted word that starts with `=` (e.g.
  `echo =====` as a separator) is expanded as `=command` (the path of a
  command named after the rest of the word).
- **Fix:** quote it: `echo "====="`, or use `echo ---`.

### `(eval):1: bad substitution`

- **Cause:** bash-only syntax such as indirect expansion `${!var}` doesn't
  work in zsh, which this shell is.
- **Fix:** use `${(P)var}` in zsh, or run the snippet with `bash -c '…'`.

### `xargs: command line cannot be assembled, too long`

- **Cause:** macOS `xargs -I{}` limits the replacement command line to 255
  bytes.
- **Fix:** use a `while read -r f; do …; done` loop instead of `xargs -I`.

### Loop over a space-separated variable runs once with the whole string

- **Symptom:** `for f in $LIST` or `set -- $r` treats the value as a single
  word; tools report a "file" whose name is the whole list.
- **Cause:** zsh doesn't word-split unquoted parameters.
- **Fix:** use an array (`S=(); S+=(...); "${S[@]}"`) or a literal list
  (`for repo in a/b c/d; do`).

## Next.js

### Dev server 404s on `_next/static/chunks/*` after a build

- **Seen:** `screenshots/studio`.
- **Cause:** `next build` overwrote the running `next dev` server's
  manifests in the shared `.next/`.
- **Fix:** the user restarts the dev server. To check a change compiles,
  use `npx tsc --noEmit` instead; check for a running `next dev`
  (`ps aux | grep "next dev"`) before any `next build`.
- **Related:** memory `feedback_no_next_build_alongside_dev_server.md`.
