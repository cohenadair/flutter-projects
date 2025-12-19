import "dart:io";

import "projects.dart";

/// ANSI escape codes for colored output.
const green = "\x1B[32m";
const red = "\x1B[31m";
const reset = "\x1B[0m";

Future<void> main() async {
  for (var project in projects) {
    await Process.start(
      "flutter",
      ["gen-l10n"],
      workingDirectory: project["path"] as String,
      runInShell: true,
    );
    print("Generated ${project["name"]} strings");
  }
  print("DONE!");
}
