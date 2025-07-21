//
//  Original code written using ChatGPT, then fixed and modified as needed.
//
import "dart:io";

void main(List<String> args) async {
  if (args.isEmpty) {
    print("Usage: dart bulk_add_import.dart <directory>");
    exit(1);
  }

  final directoryPath = args[0];
  final targetImport = "import '../../../../adair-flutter-lib/test/test_utils/widget.dart';";

  final directory = Directory(directoryPath);

  if (!directory.existsSync()) {
    print("Directory does not exist: $directoryPath");
    exit(1);
  }

  final dartFiles = directory
      .listSync(recursive: true)
      .whereType<File>()
      .where((file) => file.path.endsWith(".dart"));

  for (final file in dartFiles) {
    final lines = await file.readAsLines();

    int insertIndex = 0;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].startsWith("import") ||
          lines[i].startsWith("///") ||
          lines[i].startsWith("library")) {
        insertIndex = i + 1;
      } else if (lines[i].trim().isEmpty) {
        continue;
      } else {
        break;
      }
    }

    lines.insert(insertIndex, targetImport);

    await file.writeAsString(lines.join("\n") + "\n");
    print("Added import to: ${file.path}");
  }

  print("✅ Finished updating ${dartFiles.length} files.");
}
