#!/usr/bin/env bash
# Bumps the version/build number in a Flutter project's pubspec.yaml.
#
# Usage:
#   ./bump_pubspec_version.sh <project-dir> [--version=<X.Y.Z>]
#
# Build number: always auto-generated as YYYYMMDDNN (today's date plus a
# same-day sequence). If the current build number already starts with
# today's date, the trailing sequence is incremented; otherwise it resets to
# 01.
#
# Version name (X.Y.Z): left unchanged unless --version=<X.Y.Z> is given, or
# (when omitted) the caller is an interactive terminal, in which case this
# script prompts for a new version name directly (blank keeps the current
# one). A non-interactive caller that omits --version keeps the current
# version name with no prompt.

set -euo pipefail

VERSION_RE='^[0-9]+\.[0-9]+\.[0-9]+$'

usage() {
  echo "Usage: $(basename "$0") <project-dir> [--version=<X.Y.Z>]" >&2
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

PROJECT_DIR=""
NEW_VERSION_NAME=""

for arg in "$@"; do
  if [[ "$arg" == --version=* ]]; then
    NEW_VERSION_NAME="${arg#*=}"
  elif [[ -z "$PROJECT_DIR" ]]; then
    PROJECT_DIR="$arg"
  else
    echo "Error: unexpected argument '$arg'" >&2
    usage
  fi
done

if [[ -z "$PROJECT_DIR" ]]; then
  usage
fi

if [[ -n "$NEW_VERSION_NAME" && ! "$NEW_VERSION_NAME" =~ $VERSION_RE ]]; then
  echo "Error: --version must be in the format X.Y.Z" >&2
  exit 1
fi

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
PUBSPEC="$PROJECT_DIR/pubspec.yaml"

if [[ ! -f "$PUBSPEC" ]]; then
  echo "Error: pubspec.yaml not found in $PROJECT_DIR" >&2
  exit 1
fi

CURRENT_VERSION_LINE=$(grep '^version:' "$PUBSPEC" | head -1)
if [[ -z "$CURRENT_VERSION_LINE" ]]; then
  echo "Error: no 'version:' line found in $PUBSPEC" >&2
  exit 1
fi

CURRENT_VERSION=$(awk '{print $2}' <<< "$CURRENT_VERSION_LINE")
VERSION_NAME="${CURRENT_VERSION%%+*}"
CURRENT_BUILD="${CURRENT_VERSION#*+}"

if [[ ! "$VERSION_NAME" =~ $VERSION_RE ]]; then
  echo "Error: unable to parse version name from '$CURRENT_VERSION' (expected X.Y.Z+BUILD)" >&2
  exit 1
fi

# ── Build number: YYYYMMDDNN ─────────────────────────────────────────────────

TODAY="$(date +%Y%m%d)"
if [[ "$CURRENT_BUILD" == "$TODAY"?? && "${#CURRENT_BUILD}" -eq 10 ]]; then
  PREV_SEQ="${CURRENT_BUILD: -2}"
  NEW_SEQ=$(printf '%02d' $((10#$PREV_SEQ + 1)))
else
  NEW_SEQ="01"
fi
NEW_BUILD="${TODAY}${NEW_SEQ}"

# ── Version name: direct X.Y.Z, prompted for interactively if not given ──────

if [[ -z "$NEW_VERSION_NAME" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "New version name (currently $VERSION_NAME, blank to keep): " input
    if [[ -z "$input" ]]; then
      NEW_VERSION_NAME="$VERSION_NAME"
    elif [[ "$input" =~ $VERSION_RE ]]; then
      NEW_VERSION_NAME="$input"
    else
      echo "Error: version must be in the format X.Y.Z" >&2
      exit 1
    fi
  else
    NEW_VERSION_NAME="$VERSION_NAME"
  fi
fi

NEW_VERSION="${NEW_VERSION_NAME}+${NEW_BUILD}"

sed -i '' "s/^version:.*/version: ${NEW_VERSION}/" "$PUBSPEC"

echo "Version: ${CURRENT_VERSION} -> ${NEW_VERSION}"
