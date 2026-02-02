import 'dart:io';

/// List of all projects and directories.
const projects = {
  "adair-flutter-lib": const Project(
    name: "adair-flutter-lib",
    path: "../adair-flutter-lib",
  ),
  "adair-flutter-lib-tester": const Project(
    name: "adair-flutter-lib-tester",
    path: "../adair-flutter-lib-tester",
    hasFlutterTests: false,
  ),
  "activity-log": const Project(
    name: "activity-log",
    path: "../activity-log/mobile",
    // Enable as needed (they take a long time to run).
    hasIosTests: true,
    hasAndroidTests: true,
  ),
  "anglers-log": const Project(
    name: "anglers-log",
    path: "../anglers-log/mobile",
  ),
};

class Project {
  final String name;
  final String path;
  final bool hasFlutterTests;
  final bool hasIosTests;

  /// Note that if true, a "testLogging" block in the "android/app/build.gradle"
  /// file is required. See Activity Log for an example.
  final bool hasAndroidTests;

  const Project({
    required this.name,
    required this.path,
    this.hasFlutterTests = true,
    this.hasIosTests = false,
    this.hasAndroidTests = false,
  });

  Future<Process> runCommand(
    String executable,
    List<String> arguments, {
    String? pathOverride,
    bool runInShell = true,
  }) async {
    return Process.start(
      executable,
      arguments,
      workingDirectory: pathOverride ?? path,
      runInShell: runInShell,
    );
  }
}
