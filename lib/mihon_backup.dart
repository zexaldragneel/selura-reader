import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

/// Reads Mihon/Tachiyomi Kotlin ProtoBuf backups (.tachibk, optionally gzip).
/// Schema numbers are taken from Mihon's upstream Backup*.kt models.
/// Backups contain manga metadata/history, NOT downloaded page images or APKs.
const int maxMihonBackupBytes = 32 * 1024 * 1024;
const int maxMihonExpandedBytes = 128 * 1024 * 1024;
const int maxMihonManga = 20000;
const int maxMihonChapters = 200000;
const int maxMihonCategories = 500;

class MihonChapter {
  const MihonChapter({
    required this.url, required this.name, required this.read,
    required this.bookmarked, required this.lastPageRead, this.lastRead = 0,
  });
  final String url;
  final String name;
  final bool read;
  final bool bookmarked;
  final int lastPageRead;
  final int lastRead;

  Map<String, Object> toJson() => {
    'url': url, 'name': name, 'read': read, 'bookmark': bookmarked,
    'lastPageRead': lastPageRead, 'lastRead': lastRead,
  };
  factory MihonChapter.fromJson(Map<String, dynamic> m) => MihonChapter(
    url: m['url'] as String,
    name: m['name'] as String? ?? '',
    read: m['read'] == true,
    bookmarked: m['bookmark'] == true,
    lastPageRead: m['lastPageRead'] as int? ?? 0,
    lastRead: m['lastRead'] as int? ?? 0,
  );
}

class MihonManga {
  const MihonManga({
    required this.source, required this.url, required this.title,
    required this.favorite, required this.chapters, required this.categoryOrders,
    this.description = '', this.author = '', this.artist = '',
    this.thumbnail = '', this.dateAdded = 0, this.sourceName = '',
  });
  final int source;
  final String url;
  final String title;
  final String description;
  final String author;
  final String artist;
  final String thumbnail;
  final String sourceName;
  final bool favorite;
  final int dateAdded;
  /// Mihon associates manga to BackupCategory.order, not BackupCategory.id.
  final List<int> categoryOrders;
  final List<MihonChapter> chapters;

  String get key => source.toString() + ':' + url;
  int get readCount => chapters.where((c) => c.read).length;
  int get bookmarkedCount => chapters.where((c) => c.bookmarked).length;
  MihonChapter? get resumeChapter {
    for (final chapter in chapters) {
      if (chapter.lastPageRead > 0 && !chapter.read) return chapter;
    }
    return null;
  }
  MihonManga named(String label) => MihonManga(
    source: source, url: url, title: title, favorite: favorite,
    chapters: chapters, categoryOrders: categoryOrders, description: description,
    author: author, artist: artist, thumbnail: thumbnail,
    dateAdded: dateAdded, sourceName: label,
  );
  Map<String, Object> toJson() => {
    'source': source, 'url': url, 'title': title,
    'description': description, 'author': author, 'artist': artist,
    'thumbnail': thumbnail, 'sourceName': sourceName,
    'favorite': favorite, 'dateAdded': dateAdded,
    'categories': categoryOrders,
    'chapters': chapters.map((c) => c.toJson()).toList(),
  };
  factory MihonManga.fromJson(Map<String, dynamic> m) => MihonManga(
    source: m['source'] as int,
    url: m['url'] as String,
    title: m['title'] as String,
    description: m['description'] as String? ?? '',
    author: m['author'] as String? ?? '',
    artist: m['artist'] as String? ?? '',
    thumbnail: m['thumbnail'] as String? ?? '',
    sourceName: m['sourceName'] as String? ?? '',
    favorite: m['favorite'] == true,
    dateAdded: m['dateAdded'] as int? ?? 0,
    categoryOrders: (m['categories'] as List<dynamic>? ?? []).whereType<int>().toList(),
    chapters: (m['chapters'] as List<dynamic>? ?? [])
      .map((e) => MihonChapter.fromJson(Map<String, dynamic>.from(e as Map)))
      .toList(),
  );
}

class MihonCategory {
  const MihonCategory(this.id, this.name, this.order);
  final int id;
  final String name;
  final int order;
  Map<String, Object> toJson() => {'id': id, 'name': name, 'order': order};
  factory MihonCategory.fromJson(Map<String, dynamic> m) => MihonCategory(
    m['id'] as int, m['name'] as String, m['order'] as int? ?? 0,
  );
}

class MihonLibraryData {
  const MihonLibraryData({
    required this.manga, required this.categories, required this.sources,
  });
  final List<MihonManga> manga;
  final List<MihonCategory> categories;
  final Map<int, String> sources;
  int get chapterCount => manga.fold(0, (sum, m) => sum + m.chapters.length);
  int get readChapters => manga.fold(0, (sum, m) => sum + m.readCount);
  Map<String, Object> toJson() => {
    'format': 'selura-mihon-import', 'version': 1,
    'manga': manga.map((m) => m.toJson()).toList(),
    'categories': categories.map((c) => c.toJson()).toList(),
    'sources': sources.map((k, v) => MapEntry(k.toString(), v)),
  };
  factory MihonLibraryData.fromJson(Map<String, dynamic> data) {
    if (data['format'] != 'selura-mihon-import' || data['version'] != 1) {
      throw const FormatException('Unsupported Mihon library data.');
    }
    final list = (data['manga'] as List<dynamic>? ?? [])
      .map((e) => MihonManga.fromJson(Map<String, dynamic>.from(e as Map)))
      .toList();
    if (list.length > maxMihonManga ||
        list.fold<int>(0, (sum, m) => sum + m.chapters.length) > maxMihonChapters) {
      throw const FormatException('Mihon library exceeds safe size limits.');
    }
    return MihonLibraryData(
      manga: list,
      categories: (data['categories'] as List<dynamic>? ?? [])
        .map((e) => MihonCategory.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList(),
      sources: (data['sources'] as Map<String, dynamic>? ?? {})
        .map((key, value) => MapEntry(int.parse(key), value as String)),
    );
  }
}

class _Wire {
  _Wire(Uint8List bytes) : data = bytes;
  final Uint8List data;
  int offset = 0;
  bool get done => offset >= data.length;
  int varint() {
    var result = 0;
    for (var i = 0; i < 10; i++) {
      if (done) throw const FormatException('Truncated Mihon protobuf.');
      final byte = data[offset++];
      if (i == 9 && byte > 1) {
        throw const FormatException('Invalid protobuf varint.');
      }
      result |= (byte & 0x7f) << (7 * i);
      if ((byte & 0x80) == 0) return result;
    }
    throw const FormatException('Invalid protobuf integer.');
  }
  (int, int) field() {
    final tag = varint(), wire = tag & 7;
    if (tag >> 3 == 0 || (wire != 0 && wire != 1 && wire != 2 && wire != 5)) {
      throw const FormatException('Unsupported protobuf wire field.');
    }
    return (tag >> 3, wire);
  }
  Uint8List message() {
    final size = varint();
    if (size < 0 || size > maxMihonExpandedBytes || size > data.length - offset) {
      throw const FormatException('Invalid protobuf field length.');
    }
    final bytes = Uint8List.sublistView(data, offset, offset + size);
    offset += size;
    return bytes;
  }
  String string() {
    final bytes = message();
    if (bytes.length > 1024 * 1024) {
      throw const FormatException('Mihon text field exceeds safe limit.');
    }
    return utf8.decode(bytes);
  }
  void skip(int wire) {
    switch (wire) {
      case 0: varint(); break;
      case 1: _skip(8); break;
      case 2: message(); break;
      case 5: _skip(4); break;
      default: throw const FormatException('Invalid protobuf field.');
    }
  }
  void _skip(int count) {
    if (count > data.length - offset) {
      throw const FormatException('Truncated Mihon protobuf.');
    }
    offset += count;
  }
}

String _text(_Wire r, int wire) {
  if (wire != 2) throw const FormatException('Invalid Mihon text field.');
  return r.string();
}
int _number(_Wire r, int wire) {
  if (wire != 0) throw const FormatException('Invalid Mihon integer field.');
  return r.varint();
}

MihonCategory _category(Uint8List bytes) {
  final r = _Wire(bytes);
  var id = 0, order = 0, name = '';
  while (!r.done) {
    final (f, w) = r.field();
    switch (f) {
      case 1: name = _text(r, w); break;
      case 2: order = _number(r, w); break;
      case 3: id = _number(r, w); break;
      default: r.skip(w);
    }
  }
  return MihonCategory(id, name, order);
}
(int, String) _source(Uint8List bytes) {
  final r = _Wire(bytes);
  var id = 0, name = '';
  while (!r.done) {
    final (f, w) = r.field();
    switch (f) {
      case 1: name = _text(r, w); break;
      case 2: id = _number(r, w); break;
      default: r.skip(w);
    }
  }
  return (id, name);
}
MihonChapter _chapter(Uint8List bytes) {
  final r = _Wire(bytes);
  var url = '', name = '', read = false, marked = false, page = 0;
  while (!r.done) {
    final (f, w) = r.field();
    switch (f) {
      case 1: url = _text(r, w); break;
      case 2: name = _text(r, w); break;
      case 4: read = _number(r, w) != 0; break;
      case 5: marked = _number(r, w) != 0; break;
      case 6: page = _number(r, w).clamp(0, 100000).toInt(); break;
      default: r.skip(w);
    }
  }
  if (url.isEmpty || url.length > 4096) {
    throw const FormatException('Mihon chapter URL is invalid.');
  }
  return MihonChapter(
    url: url, name: name, read: read, bookmarked: marked, lastPageRead: page,
  );
}
(String, int) _history(Uint8List bytes) {
  final r = _Wire(bytes);
  var url = '', date = 0;
  while (!r.done) {
    final (f, w) = r.field();
    switch (f) {
      case 1: url = _text(r, w); break;
      case 2: date = _number(r, w); break;
      default: r.skip(w);
    }
  }
  return (url, date);
}
MihonManga _manga(Uint8List bytes) {
  final r = _Wire(bytes);
  var source = 0, url = '', title = '', favorite = true, description = '';
  var author = '', artist = '', thumbnail = '', added = 0;
  final categories = <int>[];
  final chapters = <MihonChapter>[];
  final history = <String, int>{};
  while (!r.done) {
    final (f, w) = r.field();
    switch (f) {
      case 1: source = _number(r, w); break;
      case 2: url = _text(r, w); break;
      case 3: title = _text(r, w); break;
      case 4: artist = _text(r, w); break;
      case 5: author = _text(r, w); break;
      case 6: description = _text(r, w); break;
      case 9: thumbnail = _text(r, w); break;
      case 13: added = _number(r, w); break;
      case 16:
        if (w != 2) throw const FormatException('Invalid chapter list.');
        chapters.add(_chapter(r.message()));
        if (chapters.length > maxMihonChapters) {
          throw const FormatException('Too many chapters in manga.');
        }
        break;
      case 17:
        if (w == 0) {
          categories.add(r.varint());
        } else if (w == 2) {
          final packed = _Wire(r.message());
          while (!packed.done) {
            categories.add(packed.varint());
            if (categories.length > maxMihonCategories) {
              throw const FormatException('Too many manga categories.');
            }
          }
        } else {
          throw const FormatException('Invalid category list.');
        }
        break;
      case 100: favorite = _number(r, w) != 0; break;
      case 104:
        if (w != 2) throw const FormatException('Invalid history field.');
        final (path, date) = _history(r.message());
        if (path.isNotEmpty) history[path] = date;
        break;
      default: r.skip(w);
    }
  }
  if (url.isEmpty || url.length > 4096 || title.isEmpty || title.length > 2048) {
    throw const FormatException('Mihon manga metadata is incomplete.');
  }
  return MihonManga(
    source: source, url: url, title: title, favorite: favorite,
    categoryOrders: categories, description: description, author: author,
    artist: artist, thumbnail: thumbnail, dateAdded: added,
    chapters: [
      for (final chapter in chapters)
        MihonChapter(
          url: chapter.url, name: chapter.name, read: chapter.read,
          bookmarked: chapter.bookmarked, lastPageRead: chapter.lastPageRead,
          lastRead: history[chapter.url] ?? 0,
        ),
    ],
  );
}

@visibleForTesting
MihonLibraryData decodeMihonProto(Uint8List bytes) {
  if (bytes.isEmpty || bytes.length > maxMihonExpandedBytes) {
    throw const FormatException('Mihon backup is empty or too large.');
  }
  final r = _Wire(bytes);
  final manga = <MihonManga>[];
  final categories = <MihonCategory>[];
  final sources = <int, String>{};
  var chapterCount = 0;
  while (!r.done) {
    final (f, w) = r.field();
    switch (f) {
      case 1:
        if (w != 2) throw const FormatException('Invalid manga entry.');
        final row = _manga(r.message());
        manga.add(row);
        chapterCount += row.chapters.length;
        if (manga.length > maxMihonManga || chapterCount > maxMihonChapters) {
          throw const FormatException('Mihon backup exceeds import limits.');
        }
        break;
      case 2:
        if (w != 2) throw const FormatException('Invalid category entry.');
        categories.add(_category(r.message()));
        if (categories.length > maxMihonCategories) {
          throw const FormatException('Too many Mihon categories.');
        }
        break;
      case 101:
        if (w != 2) throw const FormatException('Invalid source entry.');
        final (id, name) = _source(r.message());
        if (name.isNotEmpty) sources[id] = name;
        break;
      default: r.skip(w);
    }
  }
  if (manga.isEmpty) {
    throw const FormatException(
      'No manga found. Choose the .tachibk backup exported by Mihon.',
    );
  }
  return MihonLibraryData(
    manga: manga.map((item) => item.named(
      sources[item.source] ?? 'Unknown source (' + item.source.toString() + ')',
    )).toList(),
    categories: categories,
    sources: sources,
  );
}

/// Bound compressed/uncompressed bytes and decode in Flutter compute isolate.
Future<MihonLibraryData> _decodeFile(String path) async {
  final file = File(path);
  final stat = await file.stat();
  if (stat.type != FileSystemEntityType.file ||
      stat.size <= 0 || stat.size > maxMihonBackupBytes) {
    throw const FormatException('Backup missing or larger than 32 MB.');
  }
  final magic = await file.openRead(0, 2).fold<List<int>>(
    <int>[], (bytes, part) => bytes..addAll(part),
  );
  final isGzip = magic.length >= 2 && magic[0] == 0x1f && magic[1] == 0x8b;
  final builder = BytesBuilder(copy: false);
  final stream = isGzip ? file.openRead().transform(gzip.decoder) : file.openRead();
  try {
    await for (final chunk in stream) {
      builder.add(chunk);
      if (builder.length > maxMihonExpandedBytes) {
        throw const FormatException('Backup expands beyond 128 MB.');
      }
    }
  } on FormatException {
    throw const FormatException('Compressed Mihon backup is corrupted.');
  }
  return decodeMihonProto(builder.takeBytes());
}

class MihonImportReport {
  const MihonImportReport(this.added, this.updated, this.total);
  final int added;
  final int updated;
  final int total;
}

class MihonBackupStore {
  const MihonBackupStore({this.directory});

  /// Tests supply an isolated directory; Android uses app-private storage.
  final Directory? directory;

  Future<File> _file() async {
    final dir = directory ?? await getApplicationSupportDirectory();
    return File(dir.path + '/mihon_library_v1.json');
  }
  Future<MihonLibraryData> preview(File backup) =>
      compute(_decodeFile, backup.path);
  Future<MihonLibraryData> load() async {
    final file = await _file();
    if (!await file.exists()) {
      return const MihonLibraryData(manga: [], categories: [], sources: {});
    }
    if (await file.length() > maxMihonExpandedBytes) {
      throw const FormatException('Stored Mihon library is oversized.');
    }
    return MihonLibraryData.fromJson(
      jsonDecode(await file.readAsString()) as Map<String, dynamic>,
    );
  }
  /// Non-destructive and idempotent by source-ID + manga-URL identity.
  /// No changes to EPUB/PDF/CBZ records or Mihon's original backup.
  Future<MihonImportReport> restore(MihonLibraryData incoming) async {
    final existing = await load();
    final merged = <String, MihonManga>{
      for (final item in existing.manga) item.key: item,
    };
    var added = 0, updated = 0;
    for (final item in incoming.manga) {
      if (merged.containsKey(item.key)) {
        updated++;
      } else {
        added++;
      }
      merged[item.key] = item;
    }
    if (merged.length > maxMihonManga ||
        merged.values.fold<int>(0, (sum, m) => sum + m.chapters.length) >
            maxMihonChapters) {
      throw const FormatException('Merged library exceeds safe limits.');
    }
    final categoryMap = <int, MihonCategory>{
      for (final item in existing.categories) item.id: item,
      for (final item in incoming.categories) item.id: item,
    };
    final combined = MihonLibraryData(
      manga: merged.values.toList(),
      categories: categoryMap.values.toList()
        ..sort((a, b) => a.order.compareTo(b.order)),
      sources: {...existing.sources, ...incoming.sources},
    );
    final output = await _file();
    final staging = File(output.path + '.pending');
    try {
      await staging.writeAsString(jsonEncode(combined.toJson()), flush: true);
      await staging.rename(output.path);
    } finally {
      if (await staging.exists()) await staging.delete();
    }
    return MihonImportReport(added, updated, combined.manga.length);
  }
}
