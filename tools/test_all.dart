//
//  Original code written using ChatGPT, then fixed and modified as needed.
//

import "dart:convert";
import "dart:io";

/// ANSI escape codes for colored output.
const green = "\x1B[32m";
const red = "\x1B[31m";
const reset = "\x1B[0m";

/// List of project directories.
final projects = [
  {"name": "adair-flutter-lib", "path": "../adair-flutter-lib"},
  // {"name": "activity-log", "path": "../activity-log/mobile"},
  {"name": "anglers-log", "path": "../anglers-log/mobile"},
];

int totalTests = 0;

Future<void> main() async {
  final results = <String, bool>{};

  for (var project in projects) {
    final name = project["name"]!;
    final path = project["path"]!;
    final passed = await runTestsForProject(name, path);
    results[name] = passed;
    stdout.write("\n");
  }

  print("Tests for all projects: $totalTests");
  for (var entry in results.entries) {
    final color = entry.value ? green : red;
    final status = entry.value ? "PASS" : "FAIL";
    print("$color${entry.key}: $status$reset");
  }
}

Future<bool> runTestsForProject(String name, String path) async {
  final process = await Process.start(
    "flutter",
    ["test", "--machine"],
    workingDirectory: path,
    runInShell: true,
  );

  final lines = utf8.decoder.bind(process.stdout).transform(LineSplitter());

  int testIndex = 0;
  bool passed = true;

  await for (var line in lines) {
    try {
      final jsonLine = json.decode(line);
      if (jsonLine is! Map<String, dynamic>) {
        continue;
      }

      switch (jsonLine["type"]) {
        case "testStart":
          testIndex++;
          totalTests++;
          stdout.write("\rTests for $name: $testIndex");
          break;
        case "testDone":
          if (jsonLine["result"] != "success") {
            return false;
          }
      }
    } catch (_) {
      // Nothing to do.
    }
  }

  return passed && await process.exitCode == 0;
}
