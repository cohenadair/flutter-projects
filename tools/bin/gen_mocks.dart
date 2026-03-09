import "../lib/projects.dart";

Future<void> main(List<String> projectNames) async {
  if (projectNames.isEmpty) {
    print("Usage: dart gen_mocks.dart <project names>");
    return;
  }

  for (var name in projectNames) {
    final proj = projects[name]!;
    await proj.runCommand("dart", [
      "run",
      "build_runner",
      "build",
    ], echoOutput: true);
  }
}
