#!/usr/bin/env bash
# Builds a Flutter app for one or more platforms and uploads to the respective store.
#
# Usage (from within a project directory):
#   ../build_and_upload_release.sh <ios|macos|android> [ios|macos|android] ...
#
# Usage (from repo root):
#   ./build_and_upload_release.sh <ios|macos|android> [ios|macos|android] ... <project-dir>
#
# Required env vars (Apple platforms):
#   APPLE_ID                    — Apple ID email (App Store Connect login)
#   APPLE_APP_SPECIFIC_PASSWORD — App-specific password from appleid.apple.com
#   APPLE_TEAM_ID               — 10-character Apple Developer Team ID
#
# Required env vars (Android):
#   GOOGLE_PLAY_JSON_KEY  — Path to the Google service-account JSON key file
#   ANDROID_PACKAGE_NAME  — App package name (e.g. ca.proiq.pro_iq)

set -uo pipefail

# ── Argument parsing ──────────────────────────────────────────────────────────

usage() {
  echo "Usage: $(basename "$0") <ios|macos|android> [ios|macos|android] ... [project-dir]"
  echo ""
  echo "  Platforms    One or more of: ios, macos, android"
  echo "  project-dir  Path to the Flutter project (default: current directory)"
  echo ""
  echo "Required env vars (Apple): APPLE_ID, APP_SPECIFIC_PASSWORD, TEAM_ID"
  echo "Required env vars (Android): GOOGLE_PLAY_JSON_KEY, ANDROID_PACKAGE_NAME"
  exit 1
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
fi

PLATFORMS=()
PROJECT_DIR=""

for arg in "$@"; do
  if [[ "$arg" == "ios" || "$arg" == "macos" || "$arg" == "android" ]]; then
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
  echo "Error: at least one platform (ios, macos, android) is required" >&2
  usage
fi

PROJECT_DIR="${PROJECT_DIR:-$PWD}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

# ── Credential checks ─────────────────────────────────────────────────────────

missing_vars=()

needs_apple=false
needs_android=false
for p in "${PLATFORMS[@]}"; do
  [[ "$p" == "ios" || "$p" == "macos" ]] && needs_apple=true
  [[ "$p" == "android" ]]                && needs_android=true
done

if [[ "$needs_apple" == "true" ]]; then
  [[ -z "${APPLE_ID:-}" ]]              && missing_vars+=("APPLE_ID")
  [[ -z "${APPLE_APP_SPECIFIC_PASSWORD:-}" ]] && missing_vars+=("APPLE_APP_SPECIFIC_PASSWORD")
  [[ -z "${APPLE_TEAM_ID:-}" ]]               && missing_vars+=("APPLE_TEAM_ID")
fi

if [[ "$needs_android" == "true" ]]; then
  [[ -z "${GOOGLE_PLAY_JSON_KEY:-}" ]]  && missing_vars+=("GOOGLE_PLAY_JSON_KEY")
  [[ -z "${ANDROID_PACKAGE_NAME:-}" ]]  && missing_vars+=("ANDROID_PACKAGE_NAME")
fi

if [[ ${#missing_vars[@]} -gt 0 ]]; then
  echo "Error: missing required env vars: ${missing_vars[*]}" >&2
  echo "" >&2
  if [[ "$needs_apple" == "true" ]]; then
    echo "  APPLE_ID              — your Apple ID email" >&2
    echo "  APPLE_APP_SPECIFIC_PASSWORD — generate at appleid.apple.com → Sign-In and Security → App-Specific Passwords" >&2
    echo "  APPLE_TEAM_ID               — 10-character Apple Developer Team ID" >&2
  fi
  if [[ "$needs_android" == "true" ]]; then
    echo "  GOOGLE_PLAY_JSON_KEY  — path to Google service-account JSON key file" >&2
    echo "  ANDROID_PACKAGE_NAME  — app package name (e.g. ca.proiq.pro_iq)" >&2
  fi
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
  <string>${APPLE_TEAM_ID}</string>
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

# ── Helper: upload AAB to Google Play via Publishing API ─────────────────────
#
# Flow:
#   1. Mint a short-lived OAuth2 token from the service-account JSON key (RS256 JWT)
#   2. Create a new edit
#   3. Upload the AAB into that edit
#   4. Assign the build to the internal track (status=completed)
#   5. Commit the edit

google_play_upload() {
  local aab_path="$1"
  local pkg="${ANDROID_PACKAGE_NAME}"
  local key_file="${GOOGLE_PLAY_JSON_KEY}"
  local base_url="https://androidpublisher.googleapis.com/androidpublisher/v3/applications"

  echo "==> [android] Obtaining Google Play OAuth2 token"

  local client_email token_uri private_key now header payload signing_input signature jwt token_response
  client_email=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['client_email'])" "$key_file") || return 1
  token_uri=$(python3    -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['token_uri'])"    "$key_file") || return 1
  private_key=$(python3  -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['private_key'])"  "$key_file") || return 1

  now=$(date +%s)
  header=$(printf '{"alg":"RS256","typ":"JWT"}' \
    | openssl base64 -e -A | tr '+/' '-_' | tr -d '=')
  payload=$(printf '{"iss":"%s","scope":"https://www.googleapis.com/auth/androidpublisher","aud":"%s","iat":%s,"exp":%s}' \
    "$client_email" "$token_uri" "$now" "$((now + 3600))" \
    | openssl base64 -e -A | tr '+/' '-_' | tr -d '=')
  signing_input="${header}.${payload}"
  signature=$(printf '%s' "$signing_input" \
    | openssl dgst -sha256 -sign <(printf '%s' "$private_key") \
    | openssl base64 -e -A | tr '+/' '-_' | tr -d '=') || return 1
  jwt="${signing_input}.${signature}"

  local token
  token_response=$(curl -sf -X POST "$token_uri" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" \
    --data-urlencode "assertion=$jwt") || return 1
  token=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['access_token'])" "$token_response") || return 1

  echo "==> [android] Creating edit"
  local edit_response
  edit_response=$(curl -sf -X POST \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    "${base_url}/${pkg}/edits") || return 1
  local edit_id
  edit_id=$(python3 -c "import sys,json; print(json.loads(sys.argv[1])['id'])" "$edit_response") || return 1
  echo "    edit id: $edit_id"

  echo "==> [android] Uploading AAB"
  local upload_url="https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications/${pkg}/edits/${edit_id}/bundles?uploadType=media"
  curl -sf -X POST \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/octet-stream" \
    --data-binary "@${aab_path}" \
    "$upload_url" > /dev/null || return 1

  echo "==> [android] Assigning to internal track"
  local track_body
  track_body=$(python3 -c "
import json, sys
version_code = int(sys.argv[1].split('+')[1]) if '+' in sys.argv[1] else 1
print(json.dumps({
    'releases': [{'status': 'completed', 'versionCodes': [str(version_code)]}]
}))
" "$APP_VERSION")
  curl -sf -X PUT \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$track_body" \
    "${base_url}/${pkg}/edits/${edit_id}/tracks/internal" > /dev/null || return 1

  echo "==> [android] Committing edit"
  curl -sf -X POST \
    -H "Authorization: Bearer $token" \
    "${base_url}/${pkg}/edits/${edit_id}:commit" > /dev/null || return 1
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
      --password "$APPLE_APP_SPECIFIC_PASSWORD" \
      --verbose || {
      echo "altool upload failed" > "$status_file"; return 1
    }

  elif [[ "$platform" == "macos" ]]; then
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
      DEVELOPMENT_TEAM="$APPLE_TEAM_ID" || {
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
      --password "$APPLE_APP_SPECIFIC_PASSWORD" \
      --verbose || {
      echo "altool upload failed" > "$status_file"; return 1
    }

  elif [[ "$platform" == "android" ]]; then
    echo "==> [$platform] flutter build appbundle --release"
    flutter build appbundle --release || {
      echo "flutter build appbundle failed" > "$status_file"; return 1
    }

    local aab_path
    aab_path=$(find "build/app/outputs/bundle/release" -name "*.aab" | head -1)
    if [[ -z "$aab_path" ]]; then
      echo "no .aab found in build/app/outputs/bundle/release/" > "$status_file"; return 1
    fi

    google_play_upload "$aab_path" || {
      echo "Google Play upload failed" > "$status_file"; return 1
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
  echo "$APP_NAME $APP_VERSION uploaded successfully."
  exit 0
else
  exit 1
fi
