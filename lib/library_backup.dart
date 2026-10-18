import 'dart:convert';
import 'dart:io';

import 'package:archive/archive_io.dart';
import 'package:crypto/crypto.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'reading_progress.dart';

/// Files stay on-device. A backup contains books and portable (path-free)
/// metadata; it never exposes the old phone's app-private file paths.
class BackupBook {
  const BackupBook({
    required this.path,
    required this.title,
    required this.type,
    this.favorite = false,
    this.lastOpened = 0,
  });

  final String path;
  final String title;
  final String type;
  final bool favorite;
  final int lastOpened;

  Map<String, Object> toLibraryJson() => {
        'path': path,
        'title': title,
        'type': type,
        'favorite': favorite,
        'lastOpened': lastOpened,
      };
}

class BackupRestoreResult {
  const BackupRestoreResult(this.imported, this.skipped);
  final int imported;
  final int skipped;
}

class SeluraBackupService {
  const SeluraBackupService();

  static const schema = 1;
  static const maxBooks = 500;
  static const maxManifestBytes = 2 * 1024 * 1024;
  static const maxBookBytes = 512 * 1024 * 1024;
  static const maxTotalBytes = 3 * 1024 * 1024 * 1024;
  static const globalKeys = <String>[
    'selura_epub_reading_settings_v1',
    'selura_narration_speed_v1',
    'selura_narration_voice_v1',
    'library_grid',
    'library_sort',
  ];

  static Map<String, Object?> _location(SharedPreferences prefs, String path) => {
        'epubCfi': prefs.getString(ReadingProgressStore.epubCfiKey(path)),
        'pdfPage': prefs.getInt(ReadingProgressStore.pdfPageKey(path)),
        'pdfTotal': prefs.getInt(ReadingProgressStore.pdfTotalKey(path)),
        'chapter': prefs.getInt(ReadingProgressStore.epubChapterKey(path)),
        'chapterTitle': prefs.getString(ReadingProgressStore.epubTitleKey(path)),
        'bookmarks': prefs.getStringList('selura_bookmarks_v1:' + path) ?? <String>[],
      };

  static Future<String> _digest(File file) async =>
      (await sha256.bind(file.openRead()).first).toString();

  /// Writes compressed book files incrementally instead of loading the entire
  /// library into RAM. Caller must save the resulting ZIP outside app storage.
  Future<File> export({
    required List<BackupBook> books,
    required SharedPreferences prefs,
    required File output,
  }) async {
    if (books.length > maxBooks) {
      throw const FormatException('Too many books for one backup.');
    }
    final rows = <Map<String, Object?>>[];
    final inputs = <File>[];
    var total = 0;
    for (var i = 0; i < books.length; i++) {
      final book = books[i];
      if (book.type != 'epub' && book.type != 'pdf') {
        throw const FormatException('Unsupported book format.');
      }
      final file = File(book.path);
      if (!await file.exists()) {
        throw const FileSystemException('A library book is missing');
      }
      final size = await file.length();
      total += size;
      if (size <= 0 || size > maxBookBytes || total > maxTotalBytes) {
        throw const FormatException('Backup book exceeds the size limit.');
      }
      final entry = 'books/' + i.toString() + '.' + book.type;
      rows.add({
        'entry': entry,
        'size': size,
        'sha256': await _digest(file),
        'title': book.title,
        'type': book.type,
        'favorite': book.favorite,
        'lastOpened': book.lastOpened,
        'reading': _location(prefs, book.path),
      });
      inputs.add(file);
    }

    final globals = <String, Object?>{};
    for (final key in globalKeys) {
      if (prefs.containsKey(key)) globals[key] = prefs.get(key);
    }
    final manifest = {
      'format': 'selura-library-backup',
      'version': schema,
      'books': rows,
      'preferences': globals,
    };
    final manifestFile = File(output.path + '.manifest');
    final bytes = utf8.encode(jsonEncode(manifest));
    if (bytes.length > maxManifestBytes) {
      throw const FormatException('Backup metadata is too large.');
    }
    await output.parent.create(recursive: true);
    final writer = ZipFileEncoder();
    var opened = false;
    try {
      await manifestFile.writeAsBytes(bytes, flush: true);
      writer.create(output.path);
      opened = true;
      await writer.addFile(manifestFile, 'manifest.json');
      for (var i = 0; i < inputs.length; i++) {
        await writer.addFile(inputs[i], rows[i]['entry']! as String);
      }
      writer.closeSync();
      opened = false;
      return output;
    } catch (_) {
      if (opened) writer.closeSync();
      if (await output.exists()) await output.delete();
      rethrow;
    } finally {
      if (await manifestFile.exists()) await manifestFile.delete();
    }
  }

  /// Validates *everything* before importing a single book. Unknown ZIP
  /// entries, traversal paths, duplicates, mismatched hashes and bomb-like
  /// declared sizes fail closed. Existing books and preferences are preserved.
  Future<BackupRestoreResult> restore({
    required File backup,
    required Directory documents,
    required SharedPreferences prefs,
  }) async {
    if (!await backup.exists() || await backup.length() > maxTotalBytes) {
      throw const FormatException('Backup file is missing or too large.');
    }
    final input = InputFileStream(backup.path);
    late final Archive archive;
    try {
      archive = ZipDecoder().decodeBuffer(input);
    } finally {
      input.close();
    }
    final entries = <String, ArchiveFile>{};
    for (final entry in archive.files) {
      final name = entry.name;
      if (!entry.isFile || name == 'manifest.json' && entry.size > maxManifestBytes ||
          name != 'manifest.json' &&
          !RegExp(r'^books/[0-9]+\.(epub|pdf)$').hasMatch(name) ||
          entries.containsKey(name)) {
        throw const FormatException('Unsafe or unsupported backup entry.');
      }
      entries[name] = entry;
    }
    final metadata = entries['manifest.json'];
    if (metadata == null || metadata.size > maxManifestBytes) {
      throw const FormatException('Missing Selura backup manifest.');
    }
    final dynamic decoded = jsonDecode(utf8.decode(metadata.content as List<int>));
    if (decoded is! Map<String, dynamic> ||
        decoded['format'] != 'selura-library-backup' || decoded['version'] != schema ||
        decoded['books'] is! List || decoded['preferences'] is! Map) {
      throw const FormatException('Unsupported backup version or manifest.');
    }
    final sourceBooks = decoded['books'] as List;
    if (sourceBooks.length > maxBooks || entries.length != sourceBooks.length + 1) {
      throw const FormatException('Backup entries do not match the manifest.');
    }
    final globals = Map<String, dynamic>.from(decoded['preferences'] as Map);
    if (globals.keys.any((key) => !globalKeys.contains(key))) {
      throw const FormatException('Unexpected backup settings.');
    }
    for (final key in globals.keys) {
      final v = globals[key];
      if (key == 'library_grid' && v is! bool ||
          (key == 'library_sort' || key == 'selura_narration_speed_v1') && v is! int ||
          (key == 'selura_epub_reading_settings_v1' ||
              key == 'selura_narration_voice_v1') && v is! String) {
        throw const FormatException('Invalid backup settings.');
      }
    }

    final rows = <Map<String, dynamic>>[];
    var total = 0;
    for (var i = 0; i < sourceBooks.length; i++) {
      if (sourceBooks[i] is! Map) {
        throw const FormatException('Invalid book manifest.');
      }
      final row = Map<String, dynamic>.from(sourceBooks[i] as Map);
      final type = row['type'];
      final entry = row['entry'];
      final size = row['size'];
      final digest = row['sha256'];
      final title = row['title'];
      final reading = row['reading'];
      if ((type != 'epub' && type != 'pdf') ||
          entry != 'books/' + i.toString() + '.' + type.toString() ||
          title is! String || title.length > 512 ||
          row['favorite'] is! bool || row['lastOpened'] is! int ||
          size is! int || size <= 0 || size > maxBookBytes ||
          digest is! String || !RegExp(r'^[0-9a-f]{64}$').hasMatch(digest) ||
          reading is! Map || entries[entry]?.size != size) {
        throw const FormatException('Invalid book record or size.');
      }
      total += size;
      if (total > maxTotalBytes) {
        throw const FormatException('Backup exceeds storage safety limits.');
      }
      final values = Map<String, dynamic>.from(reading);
      if (values.keys.any((key) => !const <String>{
            'epubCfi', 'pdfPage', 'pdfTotal', 'chapter',
            'chapterTitle', 'bookmarks',
          }.contains(key)) ||
          (values['epubCfi'] != null && values['epubCfi'] is! String) ||
          (values['chapterTitle'] != null && values['chapterTitle'] is! String) ||
          (values['pdfPage'] != null && values['pdfPage'] is! int) ||
          (values['pdfTotal'] != null && values['pdfTotal'] is! int) ||
          (values['chapter'] != null && values['chapter'] is! int) ||
          values['bookmarks'] is! List ||
          (values['bookmarks'] as List).any((v) => v is! String)) {
        throw const FormatException('Invalid saved reading data.');
      }
      row['reading'] = values;
      rows.add(row);
    }

    await documents.create(recursive: true);
    final stamp = DateTime.now().microsecondsSinceEpoch.toString();
    final staging = await Directory(documents.path + '/.selura-restore-' + stamp)
        .create(recursive: true);
    final moved = <File>[];
    try {
      // Extract fixed, validated filenames only. Never extract arbitrary paths.
      for (var i = 0; i < rows.length; i++) {
        final row = rows[i];
        final file = File(staging.path + '/' + i.toString() + '.' + row['type'].toString());
        final stream = OutputFileStream(file.path);
        try {
          entries[row['entry']]!.writeContent(stream);
        } finally {
          stream.close();
        }
        if (await file.length() != row['size'] ||
            await _digest(file) != row['sha256']) {
          throw const FormatException('Backup file checksum mismatch.');
        }
      }

      final current = prefs.getStringList('books') ?? <String>[];
      final knownDigests = <String, String>{};
      for (final raw in current) {
        try {
          final existing = jsonDecode(raw);
          if (existing is! Map || existing['path'] is! String) continue;
          final file = File(existing['path'] as String);
          if (await file.exists()) {
            knownDigests[await _digest(file)] = file.path;
          }
        } catch (_) {
          // Preserve malformed current library data; do not delete it.
        }
      }

      final additions = <String>[];
      final metadataToWrite = <({String path, Map<String, dynamic> values})>[];
      var skipped = 0;
      for (var i = 0; i < rows.length; i++) {
        final row = rows[i];
        if (knownDigests.containsKey(row['sha256'])) {
          skipped++;
          continue;
        }
        final file = File(documents.path + '/selura_restored_' +
            stamp + '_' + i.toString() + '.' + row['type'].toString());
        if (await file.exists()) {
          throw const FileSystemException('Restore destination already exists.');
        }
        await File(staging.path + '/' + i.toString() + '.' + row['type'].toString())
            .rename(file.path);
        moved.add(file);
        knownDigests[row['sha256'] as String] = file.path;
        additions.add(jsonEncode(BackupBook(
          path: file.path,
          title: row['title'] as String,
          type: row['type'] as String,
          favorite: row['favorite'] as bool,
          lastOpened: row['lastOpened'] as int,
        ).toLibraryJson()));
        metadataToWrite.add((
          path: file.path,
          values: row['reading'] as Map<String, dynamic>,
        ));
      }

      // Write metadata for *new* file paths only. The existing library index
      // is committed last; no existing book state is ever overwritten.
      for (final record in metadataToWrite) {
        final path = record.path;
        final v = record.values;
        if (v['epubCfi'] is String) {
          await prefs.setString(ReadingProgressStore.epubCfiKey(path), v['epubCfi'] as String);
        }
        if (v['pdfPage'] is int) {
          await prefs.setInt(ReadingProgressStore.pdfPageKey(path), v['pdfPage'] as int);
        }
        if (v['pdfTotal'] is int) {
          await prefs.setInt(ReadingProgressStore.pdfTotalKey(path), v['pdfTotal'] as int);
        }
        if (v['chapter'] is int) {
          await prefs.setInt(ReadingProgressStore.epubChapterKey(path), v['chapter'] as int);
        }
        if (v['chapterTitle'] is String) {
          await prefs.setString(ReadingProgressStore.epubTitleKey(path), v['chapterTitle'] as String);
        }
        await prefs.setStringList(
          'selura_bookmarks_v1:' + path,
          (v['bookmarks'] as List).cast<String>(),
        );
      }
      for (final key in globals.keys) {
        if (prefs.containsKey(key)) continue; // Never overwrite current settings.
        final v = globals[key];
        if (v is bool) await prefs.setBool(key, v);
        if (v is int) await prefs.setInt(key, v);
        if (v is String) await prefs.setString(key, v);
      }
      if (additions.isNotEmpty && !await prefs.setStringList('books', [
        ...current,
        ...additions,
      ])) {
        throw const FileSystemException('Could not save restored library index.');
      }
      return BackupRestoreResult(additions.length, skipped);
    } catch (_) {
      // Existing book files are never touched. Orphans of a failed restore
      // are removed; unreferenced new preference keys are harmless.
      for (final file in moved) {
        if (await file.exists()) await file.delete();
      }
      rethrow;
    } finally {
      if (await staging.exists()) await staging.delete(recursive: true);
    }
  }
}
