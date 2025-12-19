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

var totalTests = 0;
var errors = <String>[];

Future<void> main() async {
  await testAll();
}

Future<bool> testAll() async {
  final results = <String, bool>{};

  for (var project in projects) {
    final name = project["name"]! as String;
    results[name] = await _runAllTests(
      name,
      project["path"]! as String,
      hasIosTests: project["has_ios_tests"]! as bool,
      hasAndroidTests: project["has_android_tests"]! as bool,
    );
    stdout.write("\n");
  }

  print("Tests for all projects: $totalTests");
  for (var entry in results.entries) {
    final color = entry.value ? green : red;
    final status = entry.value ? "PASS" : "FAIL";
    print("${status == "PASS" ? "✅" : "❌"} ${entry.key}: $color$status$reset");
  }

  if (errors.isNotEmpty) {
    print("\n🚫 Errors:");
    errors.forEach((e) => print(e));
  }

  return !results.containsValue(false);
}

/// If [callback] returns true, loop continues, otherwise the loop stops and
/// the function returns false.
Future<bool> _iterateProcessOutput(
  Process process,
  bool Function(String) callback,
) async {
  final lines = utf8.decoder.bind(process.stdout).transform(LineSplitter());
  await for (var line in lines) {
    try {
      if (!callback(line)) {
        return false;
      }
    } catch (_) {
      // Nothing to do.
    }
  }

  final errStream = utf8.decoder.bind(process.stderr).transform(LineSplitter());
  await for (var line in errStream) {
    if (line.contains("warning") ||
        // xcodebuild run summary writes to stderr.
        line.contains("IDETestOperationsObserverDebug")) {
      continue;
    }
    errors.add(line);
  }

  return true;
}

void _writeTestSummary(String platform, String name, int index) {
  stdout.write("\r🏃‍♂️ $platform tests for $name: $index");
}

Future<bool> _runAllTests(
  String name,
  String path, {
  required bool hasIosTests,
  required bool hasAndroidTests,
}) async {
  return await _runFlutterTests(name, path) &&
      (!hasIosTests || await _runIosTests(name, path)) &&
      (!hasAndroidTests || await _runAndroidTests(name, path));
}

Future<bool> _runFlutterTests(String name, String path) async {
  final process = await Process.start(
    "flutter",
    ["test", "--machine"],
    workingDirectory: path,
    runInShell: true,
  );

  var testIndex = 0;
  _writeTestSummary("Running Flutter", name, testIndex);

  final passed = await _iterateProcessOutput(process, (line) {
    final jsonLine = json.decode(line);
    if (jsonLine is! Map<String, dynamic>) {
      return true;
    }

    switch (jsonLine["type"]) {
      case "testStart":
        testIndex++;
        totalTests++;
        _writeTestSummary("Running Flutter", name, testIndex);
        break;
      case "testDone":
        if (jsonLine["result"] != "success") {
          return false;
        }
    }

    return true;
  });

  stdout.write("\n");
  return passed && await process.exitCode == 0;
}

Future<bool> _runAndroidTests(String name, String path) async {
  final process = await Process.start(
    "./gradlew",
    [
      ":app:testDebugUnitTest",
      "--tests",
      "com.cohenadair.mobile.*",
      // Forces tests to be run each time.
      "--rerun-tasks",
    ],
    workingDirectory: "$path/android",
    runInShell: true,
  );

  var testIndex = 0;
  _writeTestSummary("Running Android", name, testIndex);

  final passed = await _iterateProcessOutput(process, (line) {
    if (line.contains("SKIPPED")) {
      return true;
    }

    // Gradle outputs: "com.example.MyTest > myTestMethod PASSED". We'll treat
    // these as individual test results.
    if (line.contains("PASSED") || line.contains("FAILED")) {
      testIndex++;
      totalTests++;
      _writeTestSummary("Running Android", name, testIndex);
    }

    if (line.contains("FAILED")) {
      return false;
    }

    return true;
  });

  stdout.write("\n");
  return passed && await process.exitCode == 0;
}

Future<bool> _runIosTests(String name, String path) async {
  final process = await Process.start(
    "xcodebuild",
    [
      "test",
      "-workspace",
      "Runner.xcworkspace",
      "-scheme",
      "Runner",
      "-destination",
      "platform=iOS Simulator,name=iPhone 17",
    ],
    workingDirectory: "$path/ios",
    runInShell: true,
  );

  var testIndex = 0;
  _writeTestSummary("Running iOS", name, testIndex);

  final passed = await _iterateProcessOutput(process, (line) {
    if (line.contains("skipped")) {
      return true;
    }

    // XCTest typically prints lines like:
    // "Test Case '-[MyTests testExample]' passed (0.001 seconds)."
    if (line.contains("passed") || line.contains("failed")) {
      testIndex++;
      totalTests++;
      _writeTestSummary("Running iOS", name, testIndex);
    }

    if (line.contains("failed")) {
      return false;
    }

    return true;
  });

  stdout.write("\n");
  return passed && await process.exitCode == 0;
}
