import 'dart:io';
import 'dart:convert';

import 'package:archive/archive_io.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as image;
import 'package:path_provider/path_provider.dart';

import 'cover_cache.dart';

/// CBZ is ZIP containing images. CBR (RAR) is intentionally not supported.
const int maxComicArchiveBytes = 512 * 1024 * 1024;
const int maxComicPageBytes = 32 * 1024 * 1024;
const int maxComicPages = 2000;
const int maxComicUncompressedBytes = 1024 * 1024 * 1024;

class ComicPage {
  const ComicPage(this.name, this.bytes);
  final String name;
  final int bytes;
}

bool _imageName(String name) =>
    RegExp(r'\.(png|jpe?g|webp|gif)$', caseSensitive: false).hasMatch(name);

bool _safeArchiveName(String name) {
  if (name.isEmpty || name.startsWith('/') || name.contains('\\') ||
      name.contains('\u0000') || name.contains(':')) {
    return false;
  }
  final pieces = name.split('/');
  return pieces.every((part) => part.isNotEmpty && part != '.' && part != '..');
}

/// Natural image ordering: page2 precedes page10; directory numbers work too.
@visibleForTesting
int naturalComicOrder(String a, String b) {
  final aa = RegExp(r'\d+|\D+').allMatches(a.toLowerCase())
      .map((e) => e.group(0)!).toList();
  final bb = RegExp(r'\d+|\D+').allMatches(b.toLowerCase())
      .map((e) => e.group(0)!).toList();
  for (var i = 0; i < aa.length && i < bb.length; i++) {
    final x = aa[i], y = bb[i];
    final xn = RegExp(r'^\d+$').hasMatch(x);
    final yn = RegExp(r'^\d+$').hasMatch(y);
    if (xn && yn) {
      final nx = x.replaceFirst(RegExp(r'^0+(?=\d)'), '');
      final ny = y.replaceFirst(RegExp(r'^0+(?=\d)'), '');
      if (nx.length != ny.length) return nx.length.compareTo(ny.length);
      final result = nx.compareTo(ny);
      if (result != 0) return result;
    } else {
      final result = x.compareTo(y);
      if (result != 0) return result;
    }
  }
  if (aa.length != bb.length) return aa.length.compareTo(bb.length);
  return a.compareTo(b);
}

List<ComicPage> _scanCbz(String path) {
  final input = InputFileStream(path);
  try {
    final zip = ZipDecoder().decodeBuffer(input);
    final pages = <ComicPage>[];
    final seen = <String>{};
    var expandedBytes = 0;
    for (final entry in zip.files) {
      if (!entry.isFile) continue;
      final name = entry.name;
      if (!_safeArchiveName(name)) {
        throw const FormatException('CBZ contains an unsafe filename.');
      }
      if (name.startsWith('__MACOSX/') ||
          name.split('/').last.startsWith('.') || !_imageName(name)) {
        continue;
      }
      if (entry.size < 1 || entry.size > maxComicPageBytes ||
          !seen.add(name.toLowerCase())) {
        throw const FormatException('CBZ contains duplicate or oversized pages.');
      }
      expandedBytes += entry.size;
      if (pages.length >= maxComicPages ||
          expandedBytes > maxComicUncompressedBytes) {
        throw const FormatException('CBZ exceeds safe page limits.');
      }
      pages.add(ComicPage(name, entry.size));
    }
    if (pages.isEmpty) {
      throw const FormatException('No supported image pages found in this CBZ.');
    }
    pages.sort((a, b) => naturalComicOrder(a.name, b.name));
    return pages;
  } finally {
    input.close();
  }
}

class ComicArchive {
  const ComicArchive._(this.path, this.pages, this.fingerprint);
  final String path;
  final List<ComicPage> pages;
  final String fingerprint;

  static Future<ComicArchive> open(String path) async {
    final file = File(path);
    final stat = await file.stat();
    if (stat.type != FileSystemEntityType.file ||
        stat.size < 1 || stat.size > maxComicArchiveBytes) {
      throw const FormatException('CBZ file is missing or exceeds 512 MB.');
    }
    final pages = await compute(_scanCbz, path);
    final fingerprint = sha256.convert(utf8.encode(
      path + '|' + stat.size.toString() + '|' +
      stat.modified.millisecondsSinceEpoch.toString(),
    )).toString();
    return ComicArchive._(path, pages, fingerprint);
  }
}

Future<void> _extractComicPage(Map<String, Object> args) async {
  final path = args['path']! as String;
  final name = args['name']! as String;
  final expectedBytes = args['bytes']! as int;
  final destination = args['destination']! as String;
  final temporary = File(destination + '.partial');
  final input = InputFileStream(path);
  try {
    final zip = ZipDecoder().decodeBuffer(input);
    ArchiveFile? target;
    for (final entry in zip.files) {
      if (entry.isFile && entry.name == name) {
        target = entry;
        break;
      }
    }
    if (target == null || target.size != expectedBytes ||
        target.size > maxComicPageBytes) {
      throw const FormatException('Comic page missing or modified.');
    }
    final output = OutputFileStream(temporary.path);
    try {
      target.writeContent(output);
    } finally {
      output.close();
    }
    if (await temporary.length() != expectedBytes) {
      throw const FormatException('Comic page could not be extracted.');
    }
    await temporary.rename(destination);
  } finally {
    input.close();
    if (await temporary.exists()) await temporary.delete();
  }
}

class ComicPageCache {
  ComicPageCache._(this.archive, this.directory);

  @visibleForTesting
  ComicPageCache.forTesting(this.archive, this.directory);
  final ComicArchive archive;
  final Directory directory;
  final Map<int, Future<File>> _pending = {};

  static Future<ComicPageCache> open(ComicArchive archive) async {
    final temp = await getTemporaryDirectory();
    final dir = Directory(temp.path + '/selura_comic_pages/' +
        archive.fingerprint);
    await dir.create(recursive: true);
    return ComicPageCache._(archive, dir);
  }

  File _fileAt(int index) {
    final extension = archive.pages[index].name.split('.').last.toLowerCase();
    return File(directory.path + '/page-' + index.toString() + '.' + extension);
  }

  Future<File> page(int index) async {
    if (index < 0 || index >= archive.pages.length) {
      throw RangeError.index(index, archive.pages);
    }
    final ready = _fileAt(index);
    if (await ready.exists() &&
        await ready.length() == archive.pages[index].bytes) {
      return ready;
    }
    final pending = _pending.putIfAbsent(index, () async {
      final file = _fileAt(index);
      await compute(_extractComicPage, <String, Object>{
        'path': archive.path,
        'name': archive.pages[index].name,
        'bytes': archive.pages[index].bytes,
        'destination': file.path,
      });
      return file;
    });
    try {
      return await pending;
    } finally {
      _pending.remove(index);
    }
  }

  /// Limit disk cache to nearby decoded pages; originals remain in the CBZ.
  Future<void> trimTo(int currentIndex) async {
    try {
      await for (final entity in directory.list()) {
        if (entity is! File) continue;
        final found = RegExp(r'^page-(\d+)\.(png|jpe?g|webp|gif)$')
            .firstMatch(entity.uri.pathSegments.last);
        if (found == null) continue;
        final index = int.parse(found.group(1)!);
        if ((index - currentIndex).abs() > 4 && !_pending.containsKey(index)) {
          await entity.delete();
        }
      }
    } catch (_) {
      // Temporary page files may be cleared by Android at any time.
    }
  }
}

List<int>? _readComicThumbnail(Map<String, String> args) {
  final input = InputFileStream(args['path']!);
  try {
    final zip = ZipDecoder().decodeBuffer(input);
    for (final entry in zip.files) {
      if (entry.name != args['name'] || !entry.isFile) continue;
      if (entry.size < 1 || entry.size > maxCoverImageBytes) return null;
      final data = entry.content;
      if (data is! List<int>) return null;
      final decoded = image.decodeImage(data);
      if (decoded == null || decoded.width < 1 || decoded.height < 1) {
        return null;
      }
      return encodeCoverThumbnail(decoded);
    }
    return null;
  } finally {
    input.close();
  }
}

/// Page one becomes a bounded on-disk cover; malformed covers use default art.
class ComicCoverCache {
  final Map<String, Future<String?>> _requests = {};

  Future<String?> load(String path) =>
      _requests.putIfAbsent(path, () => _load(path));

  Future<String?> _load(String path) async {
    try {
      final archive = await ComicArchive.open(path);
      final root = await getApplicationSupportDirectory();
      final folder = Directory(root.path + '/comic_covers/v1');
      final cover = File(folder.path + '/' + archive.fingerprint + '.jpg');
      if (await cover.exists() && await cover.length() > 0) {
        return cover.path;
      }
      final data = await compute(_readComicThumbnail, <String, String>{
        'path': archive.path,
        'name': archive.pages.first.name,
      });
      if (data == null || data.isEmpty) return null;
      await folder.create(recursive: true);
      final temporary = File(cover.path + '.partial');
      try {
        await temporary.writeAsBytes(data, flush: true);
        await temporary.rename(cover.path);
      } finally {
        if (await temporary.exists()) await temporary.delete();
      }
      return cover.path;
    } catch (_) {
      return null;
    }
  }
}
