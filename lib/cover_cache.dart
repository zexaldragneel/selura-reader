import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:epubx/epubx.dart' as epubx;
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as image;
import 'package:path_provider/path_provider.dart';

/// Large EPUBs are deliberately skipped to avoid exhausting phone memory.
const int maxCoverEpubBytes = 128 * 1024 * 1024;
const int coverThumbnailLongestSide = 720;

/// Create a bounded, compressed JPEG for the bookshelf, never a full-size image.
@visibleForTesting
List<int> encodeCoverThumbnail(image.Image cover) {
  final longestSide = cover.width > cover.height ? cover.width : cover.height;
  if (longestSide < 1) return <int>[];

  final image.Image thumbnail;
  if (longestSide > coverThumbnailLongestSide) {
    final scale = coverThumbnailLongestSide / longestSide;
    thumbnail = image.copyResize(
      cover,
      width: (cover.width * scale).round().clamp(1, coverThumbnailLongestSide),
      height: (cover.height * scale).round().clamp(1, coverThumbnailLongestSide),
    );
  } else {
    thumbnail = cover;
  }
  return image.encodeJpg(thumbnail, quality: 80);
}

/// Invoked by compute() so decoding and resizing cannot stall the Flutter UI.
/// Only the EPUB's declared cover is used; unrelated illustrations are ignored.
Future<List<int>?> _readCoverThumbnail(String epubPath) async {
  try {
    final bytes = await File(epubPath).readAsBytes();
    final book = await epubx.EpubReader.openBook(bytes);
    final cover = await book.readCover();
    if (cover == null || cover.width < 1 || cover.height < 1) return null;
    final thumbnail = encodeCoverThumbnail(cover);
    return thumbnail.isEmpty ? null : thumbnail;
  } catch (_) {
    // Malformed EPUBs and unsupported image formats retain the default artwork.
    return null;
  }
}

/// On-device cover cache. The key includes file identity, size, and mtime to
/// invalidate cached images if a book is replaced. No network is required.
class EpubCoverCache {
  final Map<String, Future<String?>> _requests = {};

  Future<String?> load(String epubPath) =>
      _requests.putIfAbsent(epubPath, () => _load(epubPath));

  Future<String?> _load(String epubPath) async {
    try {
      final file = File(epubPath);
      if (!await file.exists()) return null;
      final stat = await file.stat();
      if (stat.size == 0 || stat.size > maxCoverEpubBytes) return null;

      final fingerprint = sha256
          .convert(utf8.encode(
            epubPath +
                '|' +
                stat.size.toString() +
                '|' +
                stat.modified.millisecondsSinceEpoch.toString(),
          ))
          .toString();
      final support = await getApplicationSupportDirectory();
      final folder = Directory(support.path + '/epub_covers/v1');
      final cache = File(folder.path + '/' + fingerprint + '.jpg');
      final absent = File(folder.path + '/' + fingerprint + '.none');

      if (await cache.exists()) {
        if (await cache.length() > 0) return cache.path;
        await cache.delete();
      }
      if (await absent.exists()) return null;

      final thumbnail = await compute(_readCoverThumbnail, epubPath);
      await folder.create(recursive: true);
      if (thumbnail == null) {
        // Avoid reparsing an EPUB with no usable cover on every app launch.
        await absent.writeAsString('');
        return null;
      }

      // Write to a temporary file before publishing the cache entry.
      final temporary = File(cache.path + '.tmp');
      await temporary.writeAsBytes(thumbnail, flush: true);
      await temporary.rename(cache.path);
      return cache.path;
    } catch (_) {
      // Covers are optional: never interfere with importing or reading.
      return null;
    }
  }
}
