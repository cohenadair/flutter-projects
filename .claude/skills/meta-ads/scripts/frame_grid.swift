// Renders evenly spaced frames of a video into one labeled PNG contact sheet,
// for reviewing ad videos without ffmpeg (uses AVFoundation).
//
// Usage: swift frame_grid.swift <video> <out.png> [frames=18] [cols=6] [cellWidth=300]
import AVFoundation
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else {
  print("Usage: swift frame_grid.swift <video> <out.png> [frames] [cols] [cellWidth]")
  exit(1)
}
let n = args.count > 3 ? Int(args[3])! : 18
let cols = args.count > 4 ? Int(args[4])! : 6
let cellW = args.count > 5 ? Int(args[5])! : 300

let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.requestedTimeToleranceBefore = .zero
gen.requestedTimeToleranceAfter = .zero

let dur = CMTimeGetSeconds(asset.duration)
let size = asset.tracks(withMediaType: .video)[0].naturalSize
let cellH = Int(Double(cellW) * Double(size.height) / Double(size.width))
gen.maximumSize = CGSize(width: cellW, height: cellH)

let rows = (n + cols - 1) / cols
let labelH = 22
let ctx = CGContext(
  data: nil, width: cols * cellW, height: rows * (cellH + labelH),
  bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: cols * cellW, height: rows * (cellH + labelH)))
NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)

for i in 0..<n {
  let t = dur * Double(i) / Double(max(n - 1, 1)) * 0.995
  guard let img = try? gen.copyCGImage(
    at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil)
  else { continue }
  let x = (i % cols) * cellW
  let y = (rows - 1 - i / cols) * (cellH + labelH)
  ctx.draw(img, in: CGRect(x: x, y: y, width: cellW, height: cellH))
  (String(format: "%.1fs", t) as NSString).draw(
    at: NSPoint(x: x + 4, y: y + cellH + 3),
    withAttributes: [.font: NSFont.boldSystemFont(ofSize: 14), .foregroundColor: NSColor.black])
}

let png = NSBitmapImageRep(cgImage: ctx.makeImage()!).representation(using: .png, properties: [:])!
try! png.write(to: URL(fileURLWithPath: args[2]))
print(String(format: "%@ %.1fs %dx%d", args[1], dur, Int(size.width), Int(size.height)))
