/// Inserts `import` value into each dart file under `path` who has a single
/// line that contains `searchTerm`. Good for when files are moved from a
/// Flutter app into adair-flutter-lib.
///
/// This Script should be followed by a manual "Optimize Imports" in Android
/// Studio to fix import ordering.
///
/// Original code written using ChatGPT, then fixed and modified as needed.
import "dart:io";

final import = "import 'package:adair_flutter_lib/widgets/loading.dart';";
final path = "../anglers-log/mobile/test";
final searchTerm = "Loading";

void main(List<String> args) async {
  final directory = Directory(path);
  if (!directory.existsSync()) {
    print("Directory does not exist: $path");
    exit(1);
  }

  final dartFiles = directory
      .listSync(recursive: true)
      .whereType<File>()
      .where((file) => file.path.endsWith(".dart"));

  var filesUpdated = 0;

  for (final file in dartFiles) {
    final lines = await file.readAsLines();

    var shouldInsert = false;
    for (var line in lines) {
      if (line.contains(searchTerm)) {
        shouldInsert = true;
        break;
      }
    }

    if (!shouldInsert) {
      continue;
    }

    int insertIndex = 0;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].startsWith("import") ||
          lines[i].startsWith("library")) {
        insertIndex = i + 1;
      } else if (lines[i].trim().isEmpty) {
        continue;
      } else {
        break;
      }
    }

    lines.insert(insertIndex, import);
    filesUpdated++;

    await file.writeAsString(lines.join("\n") + "\n");
    print("Added import to: ${file.path}");
  }

  print("✅ Finished updating $filesUpdated files.");
}
