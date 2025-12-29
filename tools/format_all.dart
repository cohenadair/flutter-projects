import "dart:convert";
import "dart:io";

import "projects.dart";

void main() async {
  await formatAll();
}

Future<bool> formatAll() async {
  for (var project in projects) {
    if (!(await _formatProject(
      project["name"]! as String,
      project["path"]! as String,
    ))) {
      return false;
    }
  }
  return true;
}

Future<bool> _formatProject(String name, String path) async {
  print("🔍 Formatting project: $name...");

  final process = await Process.start("dart", [
    "format",
    "lib",
    "test",
  ], workingDirectory: path);

  process.stdout
      .transform(utf8.decoder)
      .transform(const LineSplitter())
      .listen((data) => print("   => $data"));

  process.stderr
      .transform(utf8.decoder)
      .transform(const LineSplitter())
      .listen(print);

  if (await process.exitCode == 0) {
    return true;
  } else {
    print("❌ Failed to format $name");
    return false;
  }
}
