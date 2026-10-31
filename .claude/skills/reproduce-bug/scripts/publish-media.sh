#!/usr/bin/env bash
# Pushes evidence images to the repo's orphan `pr-media` branch, under
# <folder>/, and prints a Markdown-ready URL for each one.
#
#   publish-media.sh <repo-dir> <owner/repo> <folder> <file>...
#
# <folder> is `pr-<n>` for a PR, or `issue-<n>` for an issue. The branch
# shares no history with the code, so merges never touch it. Files are added
# on top of what's already there; nothing is checked out, so the local
# working tree and index are left alone. URLs are pinned to the new commit,
# so later pushes can't break them. They work in private repos for anyone
# who can see the repo.
set -euo pipefail

repo_dir=$1
slug=$2
folder=$3
shift 3

files=()
for f in "$@"; do
  files+=("$(cd "$(dirname "$f")" && pwd)/$(basename "$f")")
done
set -- "${files[@]}"

cd "$repo_dir"

parent=""
if git fetch --quiet origin pr-media 2>/dev/null; then
  parent=$(git rev-parse FETCH_HEAD)
fi

index=$(mktemp)
trap 'rm -f "$index"' EXIT
export GIT_INDEX_FILE=$index
rm -f "$index"
if [ -n "$parent" ]; then
  git read-tree "$parent"
fi

for f in "$@"; do
  blob=$(git hash-object -w "$f")
  git update-index --add --cacheinfo "100644,$blob,$folder/$(basename "$f")"
done

tree=$(git write-tree)
commit=$(git commit-tree "$tree" ${parent:+-p "$parent"} \
  -m "Media for $folder")
git push --quiet origin "$commit:refs/heads/pr-media"

for f in "$@"; do
  echo "https://github.com/$slug/blob/$commit/$folder/$(basename "$f")?raw=true"
done
