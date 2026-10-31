#!/bin/bash
# Drives an Android emulator for the reproduce-bug and verify-feature skills.
# Targets $ANDROID_SERIAL (default emulator-5554).
#
# Usage: android.sh <command> [args]
#   shot <file.png>    Waits for the screen to settle, saves a full-size
#                      screenshot, and writes <file>-view.png at 40% for
#                      reading. View coordinates are what `tap` takes.
#   tap <x> <y>        Taps at view (40%) coordinates, then waits to settle.
#   type <text>        Clears the focused field and types <text> with key
#                      events (`adb shell input text` doesn't reach Flutter
#                      text fields). Letters, digits, and spaces only.
#   settle [max]       Waits until two screenshots in a row match (max
#                      seconds, default 30). Exits 1 if it never settles.
#   focus              Prints the focused window's package. Use it to check
#                      the app is still in front before the next step.
#   launch <package>   Starts the package's launcher activity and settles.
#   fresh <apk> <package> [permission ...]
#                      Uninstalls, installs <apk>, grants each permission
#                      (e.g. android.permission.ACCESS_FINE_LOCATION), and
#                      launches.

set -euo pipefail
export ANDROID_SERIAL="${ANDROID_SERIAL:-emulator-5554}"

settle() {
  local max="${1:-30}" prev="" cur i
  for ((i = 0; i < max * 2; i++)); do
    cur=$(adb exec-out screencap | md5)
    if [ "$cur" = "$prev" ]; then
      return 0
    fi
    prev="$cur"
    sleep 0.5
  done
  echo "Screen didn't settle within ${max}s" >&2
  return 1
}

cmd="${1:-}"
shift || true

case "$cmd" in
  shot)
    settle 15 || true
    adb exec-out screencap -p > "$1"
    magick "$1" -resize 40% "${1%.png}-view.png"
    ;;
  tap)
    adb shell input tap $(($1 * 5 / 2)) $(($2 * 5 / 2))
    sleep 0.5
    # A blinking text cursor never settles, so don't fail on it.
    settle 15 || true
    ;;
  type)
    keys="KEYCODE_MOVE_END"
    for _ in $(seq 1 60); do
      keys="$keys KEYCODE_DEL"
    done
    adb shell input keyevent $keys
    text="$1"
    for ((i = 0; i < ${#text}; i++)); do
      c="${text:$i:1}"
      if [ "$c" = " " ]; then
        adb shell input keyevent KEYCODE_SPACE
      elif [[ "$c" =~ [A-Z] ]]; then
        adb shell input keycombination KEYCODE_SHIFT_LEFT "KEYCODE_$c"
      else
        adb shell input keyevent "KEYCODE_$(echo "$c" | tr '[:lower:]' '[:upper:]')"
      fi
      # Typing faster than this makes the keyboard stop responding (ANR) on a
      # loaded emulator.
      sleep 0.3
    done
    settle 5 || true
    ;;
  settle)
    settle "${1:-30}"
    ;;
  focus)
    adb shell dumpsys window | grep -m1 mCurrentFocus \
      | sed -E 's/.* ([^ /]+)\/.*/\1/'
    ;;
  launch)
    activity=$(adb shell cmd package resolve-activity --brief "$1" | tail -1 | tr -d '\r')
    adb shell am start -W -n "$activity" > /dev/null
    settle 120 || true
    ;;
  fresh)
    apk="$1"
    pkg="$2"
    shift 2
    adb uninstall "$pkg" > /dev/null 2>&1 || true
    adb install -r "$apk" > /dev/null
    for permission in "$@"; do
      adb shell pm grant "$pkg" "$permission"
    done
    "$0" launch "$pkg"
    ;;
  *)
    sed -n '2,25p' "$0"
    exit 1
    ;;
esac
