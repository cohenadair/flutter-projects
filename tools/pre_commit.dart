import 'dart:io';

import 'format_all.dart';
import 'test_all.dart';

void main() async {
  var commands = [formatAll, testAll];

  for (var command in commands) {
    if (!await command()) {
      exit(1);
    }
    print("\n");
  }
}