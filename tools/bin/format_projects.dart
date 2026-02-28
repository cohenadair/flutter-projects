import "dart:convert";

import "../lib/projects.dart";

void main(List<String> projectNames) async {
  await format(projectNames);
}

Future<bool> format([List<String> projectNames = const []]) async {
  Iterable<Project> toFormat = projects.values;
  if (projectNames.isNotEmpty) {
    toFormat = projects.values
        .where((project) => projectNames.contains(project.name))
        .toList();
  }

  for (var project in toFormat) {
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
