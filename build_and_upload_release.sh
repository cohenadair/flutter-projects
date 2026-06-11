#!/usr/bin/env bash
# Builds a Flutter app for one or more platforms and uploads to App Store Connect.
#
# Usage (from within a project directory):
#   ../build_and_upload_release.sh <ios|macos> [ios|macos] ...
#
# Usage (from repo root):
#   ./build_and_upload_release.sh <ios|macos> [ios|macos] ... <project-dir>
#
# Required env vars:
#   APPLE_ID              — Apple ID email (App Store Connect login)
#   APP_SPECIFIC_PASSWORD — App-specific password from appleid.apple.com
#   TEAM_ID               — 10-character Apple Developer Team ID

set -uo pipefail

# ── Argument parsing ──────────────────────────────────────────────────────────

usage() {
  echo "Usage: $(basename "$0") <ios|macos> [ios|macos] ... [project-dir]"
  echo ""
  echo "  Platforms    One or more of: ios, macos"
  echo "  project-dir  Path to the Flutter project (default: current directory)"
  echo ""
  echo "Required env vars: APPLE_ID, APP_SPECIFIC_PASSWORD, TEAM_ID"
  exit 1
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
fi

PLATFORMS=()
PROJECT_DIR=""

for arg in "$@"; do
  if [[ "$arg" == "ios" || "$arg" == "macos" ]]; then
    PLATFORMS+=("$arg")
  else
    if [[ -n "$PROJECT_DIR" ]]; then
      echo "Error: unexpected argument '$arg'" >&2
      usage
    fi
    PROJECT_DIR="$arg"
  fi
done

if [[ ${#PLATFORMS[@]} -eq 0 ]]; then
  echo "Error: at least one platform (ios, macos) is required" >&2
  usage
fi

PROJECT_DIR="${PROJECT_DIR:-$PWD}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

# ── Credential checks ─────────────────────────────────────────────────────────

missing_vars=()
[[ -z "${APPLE_ID:-}" ]]              && missing_vars+=("APPLE_ID")
[[ -z "${APP_SPECIFIC_PASSWORD:-}" ]] && missing_vars+=("APP_SPECIFIC_PASSWORD")
[[ -z "${TEAM_ID:-}" ]]               && missing_vars+=("TEAM_ID")

if [[ ${#missing_vars[@]} -gt 0 ]]; then
  echo "Error: missing required env vars: ${missing_vars[*]}" >&2
  echo "  APPLE_ID              — your Apple ID email" >&2
  echo "  APP_SPECIFIC_PASSWORD — generate at appleid.apple.com → Sign-In and Security → App-Specific Passwords" >&2
  echo "  TEAM_ID               — 10-character Apple Developer Team ID" >&2
  exit 1
fi

# ── Project metadata ──────────────────────────────────────────────────────────

PUBSPEC="$PROJECT_DIR/pubspec.yaml"
if [[ ! -f "$PUBSPEC" ]]; then
  echo "Error: pubspec.yaml not found in $PROJECT_DIR" >&2
  exit 1
fi

APP_NAME=$(grep '^name:' "$PUBSPEC" | head -1 | awk '{print $2}')
APP_VERSION=$(grep '^version:' "$PUBSPEC" | head -1 | awk '{print $2}')

echo "Project  : $PROJECT_DIR"
echo "App      : $APP_NAME $APP_VERSION"
echo "Platforms: ${PLATFORMS[*]}"
echo ""

# ── Temp directory (cleaned up on exit) ──────────────────────────────────────

TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_WORK"' EXIT

# ── Helper: generate ExportOptions.plist ─────────────────────────────────────

generate_export_options() {
  local dest="$1"
  cat > "$dest" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key>
  <string>app-store-connect</string>
  <key>teamID</key>
  <string>${TEAM_ID}</string>
  <key>signingStyle</key>
  <string>automatic</string>
  <key>signingCertificate</key>
  <string>Apple Distribution</string>
  <key>uploadBitcode</key>
  <false/>
  <key>uploadSymbols</key>
  <true/>
</dict>
</plist>
PLIST
}

# ── Helper: build + upload one platform; echoes result to a status file ───────

build_and_upload() {
  local platform="$1"
  local status_file="$2"
  local work_dir="$TMPDIR_WORK/$platform"
  mkdir -p "$work_dir"

  cd "$PROJECT_DIR"

  if [[ "$platform" == "ios" ]]; then
    local export_options="$work_dir/ExportOptions.plist"
    generate_export_options "$export_options"

    echo "==> [$platform] flutter build ipa"
    flutter build ipa --export-options-plist="$export_options" || {
      echo "flutter build ipa failed" > "$status_file"; return 1
    }

    local ipa_path
    ipa_path=$(find "build/ios/ipa" -name "*.ipa" | head -1)
    if [[ -z "$ipa_path" ]]; then
      echo "no .ipa found in build/ios/ipa/" > "$status_file"; return 1
    fi

    echo "==> [$platform] xcrun altool --upload-app"
    xcrun altool --upload-app \
      --file "$ipa_path" \
      --type ios \
      --username "$APPLE_ID" \
      --password "$APP_SPECIFIC_PASSWORD" \
      --verbose || {
      echo "altool upload failed" > "$status_file"; return 1
    }

  else
    echo "==> [$platform] flutter build macos --release"
    flutter build macos --release || {
      echo "flutter build macos failed" > "$status_file"; return 1
    }

    local archive_path="$work_dir/${APP_NAME}.xcarchive"

    echo "==> [$platform] xcodebuild archive"
    xcodebuild archive \
      -workspace "macos/Runner.xcworkspace" \
      -scheme Runner \
      -configuration Release \
      -archivePath "$archive_path" \
      CODE_SIGN_STYLE=Automatic \
      DEVELOPMENT_TEAM="$TEAM_ID" || {
      echo "xcodebuild archive failed" > "$status_file"; return 1
    }

    local export_options="$work_dir/ExportOptions.plist"
    generate_export_options "$export_options"

    local export_path="$work_dir/export"
    echo "==> [$platform] xcodebuild -exportArchive"
    xcodebuild -exportArchive \
      -archivePath "$archive_path" \
      -exportOptionsPlist "$export_options" \
      -exportPath "$export_path" \
      -allowProvisioningUpdates || {
      echo "xcodebuild exportArchive failed" > "$status_file"; return 1
    }

    local pkg_path
    pkg_path=$(find "$export_path" -name "*.pkg" | head -1)
    if [[ -z "$pkg_path" ]]; then
      echo "no .pkg found in export output at $export_path" > "$status_file"; return 1
    fi

    echo "==> [$platform] xcrun altool --upload-app"
    xcrun altool --upload-app \
      --file "$pkg_path" \
      --type macos \
      --username "$APPLE_ID" \
      --password "$APP_SPECIFIC_PASSWORD" \
      --verbose || {
      echo "altool upload failed" > "$status_file"; return 1
    }
  fi

  echo "ok" > "$status_file"
}

# ── Run each platform sequentially, collecting results ───────────────────────

for platform in "${PLATFORMS[@]}"; do
  status_file="$TMPDIR_WORK/${platform}.status"
  build_and_upload "$platform" "$status_file"
  echo ""
done

# ── Summary report ────────────────────────────────────────────────────────────

echo "────────────────────────────────────────────────────────────────────────────"
echo " Build & Upload Report"
echo "────────────────────────────────────────────────────────────────────────────"

all_ok=true
for platform in "${PLATFORMS[@]}"; do
  status="$(cat "$TMPDIR_WORK/${platform}.status" 2>/dev/null || echo "unknown error")"
  if [[ "$status" == "ok" ]]; then
    echo " $platform: Uploaded ✓"
  else
    echo " $platform: Failed ✗ - $status"
    all_ok=false
  fi
done

echo "────────────────────────────────────────────────────────────────────────────"

if [[ "$all_ok" == "true" ]]; then
  echo ""
  echo "$APP_NAME $APP_VERSION uploaded to App Store Connect."
  exit 0
else
  exit 1
fi
