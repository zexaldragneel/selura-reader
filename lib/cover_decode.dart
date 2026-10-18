/// Requests a bounded decoded cover dimension from Flutter's Image.file.
/// A full-resolution EPUB image can occupy tens of MB per visible bookshelf
/// card; the screen only needs enough pixels for the card at device density.
///
/// Returns null for unconstrained layouts, letting Flutter's codec choose.
int? seluraCoverDecodePixels(double extent, double devicePixelRatio) {
  if (!extent.isFinite || extent <= 0 ||
      !devicePixelRatio.isFinite || devicePixelRatio <= 0) {
    return null;
  }
  return (extent * devicePixelRatio).ceil().clamp(1, 1536).toInt();
}
