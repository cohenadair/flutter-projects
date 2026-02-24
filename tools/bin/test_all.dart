/// Original code written using ChatGPT, then fixed and modified as needed.

import "dart:convert";
import "dart:io";

import "../lib/projects.dart";

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

  for (var project in projects.values) {
    print("🏃‍♂️ Testing project: ${project.name}...");
    results[project.name] = await _runAllTests(project);
  }

  print("Tests for all projects: $totalTests");
  for (var entry in results.entries) {
    final color = entry.value ? green : red;
    final status = entry.value ? "PASS" : "FAIL";
    print("${status == "PASS" ? "✅" : "❌"} ${entry.key}: $color$status$reset");
  }

  if (errors.isNotEmpty) {
    print("\n🚫 Errors:");
    errors.forEach(print);
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
        stdout.write("\n");
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
        line.contains("IDETestOperationsObserverDebug") ||
        // Android deprecated API warnings.
        line.contains("Note")) {
      continue;
    }
    errors.add(line);
  }

  stdout.write("\n");
  return true;
}

void _writeTestSummary(String platform, int index) {
  stdout.write("\r   => $platform: $index");
}

Future<bool> _runAllTests(Project project) async {
  return (!project.hasFlutterTests || await _runFlutterTests(project)) &&
      (!project.hasIosTests || await _runIosTests(project)) &&
      (!project.hasAndroidTests || await _runAndroidTests(project));
}

Future<bool> _runFlutterTests(Project project) async {
  final process = await project.runCommand("flutter", ["test", "--machine"]);

  var testIndex = 0;
  _writeTestSummary("Flutter", testIndex);

  final passed = await _iterateProcessOutput(process, (line) {
    final jsonLine = json.decode(line);
    if (jsonLine is! Map<String, dynamic>) {
      return true;
    }

    switch (jsonLine["type"]) {
      case "testStart":
        testIndex++;
        totalTests++;
        _writeTestSummary("Flutter", testIndex);
        break;
      case "testDone":
        if (jsonLine["result"] != "success") {
          return false;
        }
    }

    return true;
  });

  return passed && await process.exitCode == 0;
}

Future<bool> _runAndroidTests(Project project) async {
  final process = await project.runCommand("./gradlew", [
    ":app:testDebugUnitTest",
    "--tests",
    "com.cohenadair.mobile.*",
    // Forces tests to be run each time.
    "--rerun-tasks",
  ], workingDirectory: "${project.path}/android");

  var testIndex = 0;
  _writeTestSummary("Android", testIndex);

  final passed = await _iterateProcessOutput(process, (line) {
    if (line.contains("SKIPPED")) {
      return true;
    }

    // Gradle outputs: "com.example.MyTest > myTestMethod PASSED". We'll treat
    // these as individual test results.
    if (line.contains("PASSED") || line.contains("FAILED")) {
      testIndex++;
      totalTests++;
      _writeTestSummary("Android", testIndex);
    }

    if (line.contains("FAILED")) {
      return false;
    }

    return true;
  });

  return passed && await process.exitCode == 0;
}

Future<bool> _runIosTests(Project project) async {
  final process = await project.runCommand("xcodebuild", [
    "test",
    "-workspace",
    "Runner.xcworkspace",
    "-scheme",
    "Runner",
    "-destination",
    "platform=iOS Simulator,name=iPhone 17",
  ], workingDirectory: "${project.path}/ios");

  var testIndex = 0;
  _writeTestSummary("iOS", testIndex);

  final passed = await _iterateProcessOutput(process, (line) {
    if (line.contains("skipped")) {
      return true;
    }

    // XCTest typically prints lines like:
    // "Test Case '-[MyTests testExample]' passed (0.001 seconds)."
    if (line.contains("passed") || line.contains("failed")) {
      testIndex++;
      totalTests++;
      _writeTestSummary("iOS", testIndex);
    }

    if (line.contains("failed")) {
      return false;
    }

    return true;
  });

  return passed && await process.exitCode == 0;
}
