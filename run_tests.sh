#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 <path-to-flutter-project> [<path-to-flutter-project> ...]"
  exit 1
fi

# Resolve all paths up front, since the loop below changes directories.
dirs=()
for dir in "$@"; do
  dirs+=("$(cd "$dir" && pwd)")
done

log="${dirs[0]}/test_results.log"
run_log="$(mktemp)"
: > "$log"

# Each `flutter test --machine` run numbers its tests from 0, and the reporter
# keys tests by ID, so shift each run's IDs past the previous run's highest.
offset=0
for dir in "${dirs[@]}"; do
  cd "$dir"
  dart format lib test
  flutter test --machine > "$run_log" || true

  jq -R -r --argjson offset "$offset" '
    . as $raw
    | (fromjson?
        | if type != "object" then .
          else
            (if .test.id? == null then . else .test.id += $offset end)
            | (if .testID? == null then . else .testID += $offset end)
          end
        | tojson)
      // $raw
  ' "$run_log" >> "$log"

  max_id="$(jq -R 'fromjson? | objects | .test.id? // empty' "$log" | sort -n | tail -1)"
  offset=$(( ${max_id:-0} + 1 ))
done

rm -f "$run_log"
dart_dot_reporter_cpy "$log"
