import 'dart:io';

import 'format_projects.dart';
import 'test_all.dart';

// TODO: Should convert to a chained run config in Android Studio so all unit
//  test details are shown.
void main() async {
  var commands = [format, testAll];

  for (var command in commands) {
    if (!await command()) {
      exit(1);
    }
  }
}