#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 <path-to-flutter-project>"
  exit 1
fi

cd "$1"

dart format lib test
flutter test --machine > test_results.log || true
dart_dot_reporter_cpy test_results.log