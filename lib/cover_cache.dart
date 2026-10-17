import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as image;
import 'package:path_provider/path_provider.dart';
import 'package:xml/xml.dart' as xml;

/// Large EPUBs are deliberately skipped to avoid exhausting phone memory.
const int maxCoverEpubBytes = 128 * 1024 * 1024;
const int maxCoverImageBytes = 16 * 1024 * 1024;
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
      width: (cover.width * scale).round().clamp(1, coverThumbnailLongestSide).toInt(),
      height: (cover.height * scale).round().clamp(1, coverThumbnailLongestSide).toInt(),
    );
  } else {
    thumbnail = cover;
  }
  return image.encodeJpg(thumbnail, quality: 80);
}

xml.XmlElement? _directChild(xml.XmlElement element, String name) {
  for (final child in element.children.whereType<xml.XmlElement>()) {
    if (child.name.local == name) return child;
  }
  return null;
}

ArchiveFile? _fileNamed(Archive archive, String name) {
  for (final entry in archive.files) {
    if (entry.isFile && entry.name == name) return entry;
  }
  return null;
}

/// Resolve manifest hrefs relative to the OPF, without ever writing archive
/// paths to the filesystem.
String? _manifestPath(String opfPath, String href) {
  try {
    final cleaned = Uri.decodeComponent(href.split('#').first.split('?').first);
    if (cleaned.startsWith('/') || cleaned.contains('\\')) return null;
    final parts = <String>[];
    final opfDirectory = opfPath.split('/');
    if (opfDirectory.isNotEmpty) opfDirectory.removeLast();
    for (final part in <String>[...opfDirectory, ...cleaned.split('/')]) {
      if (part.isEmpty || part == '.') continue;
      if (part == '..') {
        if (parts.isEmpty) return null;
        parts.removeLast();
      } else {
        parts.add(part);
      }
    }
    return parts.join('/');
  } catch (_) {
    return null;
  }
}

/// Finds only the manifest-declared EPUB 2 or EPUB 3 cover image.
/// Parsing the package manifest directly also supports EPUB 3's cover-image
/// property, which is not handled by epubx's EPUB 2-only readCover().
@visibleForTesting
Future<List<int>?> readCoverThumbnail(String epubPath) async {
  try {
    final epub = File(epubPath);
    final stat = await epub.stat();
    if (stat.size == 0 || stat.size > maxCoverEpubBytes) return null;
    final archive = ZipDecoder().decodeBytes(await epub.readAsBytes());

    final containerFile = _fileNamed(archive, 'META-INF/container.xml');
    if (containerFile == null) return null;
    final container = xml.XmlDocument.parse(
      utf8.decode(containerFile.content as List<int>),
    );

    String? opfPath;
    for (final node in container.descendants.whereType<xml.XmlElement>()) {
      if (node.name.local == 'rootfile') {
        opfPath = node.getAttribute('full-path');
        break;
      }
    }
    if (opfPath == null || opfPath.isEmpty) return null;
    final packageFile = _fileNamed(archive, opfPath);
    if (packageFile == null) return null;
    final package = xml.XmlDocument.parse(
      utf8.decode(packageFile.content as List<int>),
    ).rootElement;
    final manifest = _directChild(package, 'manifest');
    final metadata = _directChild(package, 'metadata');
    if (manifest == null || metadata == null) return null;

    String? epub2CoverId;
    for (final meta in metadata.children.whereType<xml.XmlElement>()) {
      if (meta.name.local == 'meta' &&
          meta.getAttribute('name')?.toLowerCase() == 'cover') {
        epub2CoverId = meta.getAttribute('content');
        break;
      }
    }

    String? coverHref;
    for (final item in manifest.children.whereType<xml.XmlElement>()) {
      if (item.name.local != 'item') continue;
      final props = item.getAttribute('properties')?.split(RegExp(r'\s+')) ?? [];
      if (props.contains('cover-image')) {
        coverHref = item.getAttribute('href');
        break;
      }
    }

    if (coverHref == null && epub2CoverId != null) {
      for (final item in manifest.children.whereType<xml.XmlElement>()) {
        if (item.name.local == 'item' &&
            item.getAttribute('id') == epub2CoverId) {
          coverHref = item.getAttribute('href');
          break;
        }
      }
    }
    if (coverHref == null || coverHref.isEmpty) return null;
    final entryPath = _manifestPath(opfPath, coverHref);
    if (entryPath == null) return null;
    final coverEntry = _fileNamed(archive, entryPath);
    if (coverEntry == null || coverEntry.size > maxCoverImageBytes) return null;
    final raw = coverEntry.content;
    if (raw is! List<int>) return null;
    final cover = image.decodeImage(raw);
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

      final thumbnail = await compute(readCoverThumbnail, epubPath);
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
