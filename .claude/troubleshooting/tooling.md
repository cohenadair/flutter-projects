# Tooling: git, shell, Next.js

## git

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
