import "../lib/projects.dart";

Future<void> main() async {
  for (var project in projects.values) {
    await project.runCommand("flutter", ["gen-l10n"]);
    print("Generated ${project.name} strings");
  }
}
