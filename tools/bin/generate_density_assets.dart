/// Generates 1x, 1.5x, 2x, 3x, and 4x assets for the given image at the given
/// size using ImageMagick: https://imagemagick.org/#gsc.tab=0.
///
/// Original image should be greater than or equal to the 4x size so the
/// original image is never upscaled. This tool should only be used for images
/// that can't be converted to an SVG or a custom icon.
import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart';

import '../lib/projects.dart';

// Modify as needed.
final project = projects["anglers-log"]!;
const assetPath = "../active-pin.png";
const baseWidth = 30;

void main() async {
  if (assetPath.endsWith("svg")) {
    print("SVG assets are not supported.");
    return;
  }

  const outputs = {
    "4.0x": 4.0,
    "3.0x": 3.0,
    "2.0x": 2.0,
    "1.5x": 1.5,
    "1.0": 1.0,
  };

  for (var entry in outputs.entries) {
    _scaleImage(entry);
  }
}

Future<void> _scaleImage(MapEntry<String, double> output) async {
  final outputDir =
      "${project.path}/assets${output.key == "1.0" ? "" : "/${output.key}"}";
  await Directory(outputDir).create();

  // magick ~/Downloads/pro-iq.png -resize 800x ~/Downloads/pro-iq@4x.png
  final cmd = "magick";
  final resize = "-resize";
  final size = "${(baseWidth * output.value).toInt()}x";
  final out = "$outputDir/${basename(assetPath)}";

  print("$cmd $assetPath $resize $size $out");
  final process = await project.runCommand(cmd, [assetPath, resize, size, out]);

  final errStream = utf8.decoder.bind(process.stderr).transform(LineSplitter());
  await for (var line in errStream) {
    print(line);
  }
}
