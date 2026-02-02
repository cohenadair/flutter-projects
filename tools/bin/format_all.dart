import "dart:convert";

import "../lib/projects.dart";

void main() async {
  await formatAll();
}

Future<bool> formatAll() async {
  for (var project in projects.values) {
    if (!(await _formatProject(project))) {
      return false;
    }
  }
  return true;
}

Future<bool> _formatProject(Project project) async {
  print("🔍 Formatting project: ${project.name}...");

  final process = await project.runCommand("dart", [
    "format",
    "lib",
    "test",
  ], runInShell: false);

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
    print("❌ Failed to format ${project.name}");
    return false;
  }
}
