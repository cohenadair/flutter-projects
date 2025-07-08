import "dart:io";

/// ANSI escape codes for colored output.
const green = "\x1B[32m";
const red = "\x1B[31m";
const reset = "\x1B[0m";

/// List of project directories
final projects = [
  {"name": "adair-flutter-lib", "path": "../adair-flutter-lib"},
  {"name": "activity-log", "path": "../activity-log/mobile"},
  {"name": "anglers-log", "path": "../anglers-log/mobile"},
];

Future<void> main() async {
  for (var project in projects) {
    await Process.start(
      "flutter",
      ["gen-l10n",],
      workingDirectory: project["path"],
      runInShell: true,
    );
    print("Generated ${project["name"]} strings");
  }
  print("DONE!");
}
