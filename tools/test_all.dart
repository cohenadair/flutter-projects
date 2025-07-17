//
//  Original code written using ChatGPT, then fixed and modified as needed.
//

import "dart:convert";
import "dart:io";

import "projects.dart";

/// ANSI escape codes for colored output.
const green = "\x1B[32m";
const red = "\x1B[31m";
const reset = "\x1B[0m";

int totalTests = 0;

Future<void> main() async {
  await testAll();
}

Future<bool> testAll() async {
  final results = <String, bool>{};

  for (var project in projects) {
    final name = project["name"]!;
    final path = project["path"]!;
    final passed = await _testProject(name, path);
    results[name] = passed;
    stdout.write("\n");
  }

  print("Tests for all projects: $totalTests");
  for (var entry in results.entries) {
    final color = entry.value ? green : red;
    final status = entry.value ? "PASS" : "FAIL";
    print("${status == "PASS" ? "✅" : "❌"} ${entry.key}: $color$status$reset");
  }

  return !results.containsValue(false);
}

Future<bool> _testProject(String name, String path) async {
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
