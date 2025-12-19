/// List of all projects and directories.
///
/// Note that if "has_android_tests" is true, a "testLogging" block in the
/// "android/app/build.gradle" file is required. See Activity Log's for an
/// example.
final projects = [
  {
    "name": "adair-flutter-lib",
    "path": "../adair-flutter-lib",
    "has_ios_tests": false,
    "has_android_tests": false,
  },
  {
    "name": "activity-log",
    "path": "../activity-log/mobile",
    "has_ios_tests": true,
    "has_android_tests": true,
  },
  {
    "name": "anglers-log",
    "path": "../anglers-log/mobile",
    "has_ios_tests": false,
    "has_android_tests": false,
  },
];
