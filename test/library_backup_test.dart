import 'dart:convert';
import 'dart:io';

import 'package:archive/archive_io.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/library_backup.dart';
import 'package:selura_reader/reading_progress.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory root;
  late Directory restored;
  late SharedPreferences prefs;
  late File epub;
  late File pdf;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    prefs = await SharedPreferences.getInstance();
    root = await Directory.systemTemp.createTemp('selura_backup_test_');
    restored = await Directory(root.path + '/new-phone').create();
    epub = await File(root.path + '/original.epub').writeAsString('EPUB book file data.');
    pdf = await File(root.path + '/original.pdf').writeAsString('PDF book file data.');
  });

  tearDown(() async {
    if (await root.exists()) await root.delete(recursive: true);
  });

  test('ZIP snapshot contains portable book metadata and original files',
      () async {
    await prefs.setString(ReadingProgressStore.epubCfiKey(epub.path),
        'epubcfi(/6/4!/4/2:12)');
    await prefs.setStringList('selura_bookmarks_v1:' + epub.path, [
      jsonEncode({
        'id': 'id-1',
        'location': 'epubcfi(/6/4)',
        'label': 'Important page',
        'createdAt': 50,
      }),
    ]);
    await prefs.setInt(ReadingProgressStore.pdfPageKey(pdf.path), 7);
    await prefs.setInt(ReadingProgressStore.pdfTotalKey(pdf.path), 90);
    await prefs.setString('selura_epub_reading_settings_v1',
        '{"fontSize":24,"theme":"sepia"}');
    final output = File(root.path + '/snapshot.zip');
    await const SeluraBackupService().export(
      books: [
        BackupBook(path: epub.path, title: 'EPUB Story',
            type: 'epub', favorite: true, lastOpened: 123),
        BackupBook(path: pdf.path, title: 'PDF Story', type: 'pdf'),
      ],
      prefs: prefs,
      output: output,
    );

    final archive = ZipDecoder().decodeBytes(await output.readAsBytes());
    expect(archive.files.map((entry) => entry.name), containsAll([
      'manifest.json', 'books/0.epub', 'books/1.pdf',
    ]));
    final manifest = jsonDecode(utf8.decode(
        archive.files.firstWhere((entry) => entry.name == 'manifest.json')
            .content as List<int>)) as Map<String, dynamic>;
    expect(manifest['version'], 1);
    expect(manifest['format'], 'selura-library-backup');
    expect(jsonEncode(manifest), isNot(contains(epub.path)));
    expect(jsonEncode(manifest), isNot(contains(pdf.path)));
    expect((manifest['books'] as List).length, 2);

    SharedPreferences.setMockInitialValues(<String, Object>{});
    final newPrefs = await SharedPreferences.getInstance();
    final first = await const SeluraBackupService().restore(
      backup: output, documents: restored, prefs: newPrefs,
    );
    expect(first.imported, 2);
    expect(first.skipped, 0);
    final saved = newPrefs.getStringList('books')!;
    expect(saved, hasLength(2));
    final book0 = jsonDecode(saved[0]) as Map<String, dynamic>;
    final book1 = jsonDecode(saved[1]) as Map<String, dynamic>;
    final newEpubPath = book0['path'] as String;
    final newPdfPath = book1['path'] as String;
    expect(newEpubPath, isNot(epub.path));
    expect(File(newEpubPath).readAsStringSync(), 'EPUB book file data.');
    expect(book0['favorite'], true);
    expect(book0['lastOpened'], 123);
    expect(newPrefs.getString(ReadingProgressStore.epubCfiKey(newEpubPath)),
        'epubcfi(/6/4!/4/2:12)');
    expect(newPrefs.getStringList('selura_bookmarks_v1:' + newEpubPath),
        hasLength(1));
    expect(newPrefs.getInt(ReadingProgressStore.pdfPageKey(newPdfPath)), 7);
    expect(newPrefs.getInt(ReadingProgressStore.pdfTotalKey(newPdfPath)), 90);
    expect(newPrefs.getString('selura_epub_reading_settings_v1'),
        '{"fontSize":24,"theme":"sepia"}');

    final second = await const SeluraBackupService().restore(
      backup: output, documents: restored, prefs: newPrefs,
    );
    expect(second.imported, 0);
    expect(second.skipped, 2);
    expect(newPrefs.getStringList('books'), hasLength(2));
  });

  test('existing library positions and appearance settings are untouched',
      () async {
    final zip = File(root.path + '/snapshot.zip');
    await const SeluraBackupService().export(
      books: [BackupBook(path: epub.path, title: 'Novel', type: 'epub')],
      prefs: prefs,
      output: zip,
    );
    final current = await File(restored.path + '/current.pdf')
        .writeAsString('Already installed.');
    await prefs.setStringList('books', [
      jsonEncode(BackupBook(path: current.path, title: 'Current book',
          type: 'pdf', favorite: true).toLibraryJson()),
    ]);
    await prefs.setInt(ReadingProgressStore.pdfPageKey(current.path), 22);
    await prefs.setString('selura_epub_reading_settings_v1', 'custom-current');

    final result = await const SeluraBackupService().restore(
      backup: zip, documents: restored, prefs: prefs,
    );
    expect(result.imported, 1);
    expect(prefs.getStringList('books'), hasLength(2));
    expect(prefs.getInt(ReadingProgressStore.pdfPageKey(current.path)), 22);
    expect(prefs.getString('selura_epub_reading_settings_v1'), 'custom-current');
    expect(current.readAsStringSync(), 'Already installed.');
  });

  test('unknown traversal entry fails before changing existing library',
      () async {
    final zip = File(root.path + '/malicious.zip');
    final archive = ZipFileEncoder()..create(zip.path);
    await archive.addFile(epub, '../escape.epub');
    archive.closeSync();
    await prefs.setStringList('books', ['keep-this-entry']);
    await expectLater(
      const SeluraBackupService().restore(
        backup: zip, documents: restored, prefs: prefs,
      ),
      throwsFormatException,
    );
    expect(prefs.getStringList('books'), ['keep-this-entry']);
    expect(await File(root.path + '/escape.epub').exists(), isFalse);
  });

  test('altered book content fails checksum before import', () async {
    final valid = File(root.path + '/original.zip');
    await const SeluraBackupService().export(
      books: [BackupBook(path: epub.path, title: 'Novel', type: 'epub')],
      prefs: prefs,
      output: valid,
    );
    final decoded = ZipDecoder().decodeBytes(await valid.readAsBytes());
    final manifestBytes = decoded.files
        .firstWhere((entry) => entry.name == 'manifest.json').content as List<int>;
    final manifestFile = await File(root.path + '/manifest.json')
        .writeAsBytes(manifestBytes);
    final wrongBook = await File(root.path + '/wrong.epub')
        .writeAsString('Wrong content entirely.');
    final damaged = File(root.path + '/altered.zip');
    final writer = ZipFileEncoder()..create(damaged.path);
    await writer.addFile(manifestFile, 'manifest.json');
    await writer.addFile(wrongBook, 'books/0.epub');
    writer.closeSync();
    await expectLater(
      const SeluraBackupService().restore(
        backup: damaged, documents: restored, prefs: prefs,
      ),
      throwsFormatException,
    );
    expect(prefs.getStringList('books'), isNull);
    expect(await restored.list().length, 0);
  });

  test('missing source book blocks export without modifying library', () async {
    await epub.delete();
    await expectLater(
      const SeluraBackupService().export(
        books: [BackupBook(path: epub.path, title: 'Missing', type: 'epub')],
        prefs: prefs,
        output: File(root.path + '/missing.zip'),
      ),
      throwsA(isA<FileSystemException>()),
    );
    expect(prefs.getStringList('books'), isNull);
  });

  test('CBZ backups retain manga originals, page progress and bookmarks', () async {
    final manga = File(root.path + '/volume.cbz');
    final writer = ZipFileEncoder();
    writer.create(manga.path);
    final imageFile = await File(root.path + '/page1.png')
        .writeAsBytes(<int>[137, 80, 78, 71]);
    await writer.addFile(imageFile, 'page1.png');
    writer.closeSync();
    await prefs.setInt(ReadingProgressStore.comicPageKey(manga.path), 13);
    await prefs.setInt(ReadingProgressStore.comicTotalKey(manga.path), 99);
    await prefs.setStringList('selura_bookmarks_v1:' + manga.path, [
      jsonEncode({
        'id': 'cbz-1',
        'location': '13',
        'label': 'Manga page 13',
        'createdAt': 123,
      }),
    ]);
    final output = File(root.path + '/manga-library.zip');
    await const SeluraBackupService().export(
      books: [BackupBook(path: manga.path, title: 'Volume 1', type: 'cbz')],
      prefs: prefs,
      output: output,
    );
    final result = await const SeluraBackupService().restore(
      backup: output, documents: restored, prefs: prefs,
    );
    expect(result.imported, 0);
    expect(result.skipped, 1);

    SharedPreferences.setMockInitialValues(<String, Object>{});
    final otherPrefs = await SharedPreferences.getInstance();
    final otherDir = Directory(root.path + '/another-device');
    final recovered = await const SeluraBackupService().restore(
      backup: output, documents: otherDir, prefs: otherPrefs,
    );
    expect(recovered.imported, 1);
    final item = jsonDecode(otherPrefs.getStringList('books')!.single)
        as Map<String, dynamic>;
    expect(item['type'], 'cbz');
    expect(item['title'], 'Volume 1');
    final newPath = item['path'] as String;
    expect(await File(newPath).readAsBytes(), await manga.readAsBytes());
    expect(otherPrefs.getInt(ReadingProgressStore.comicPageKey(newPath)), 13);
    expect(otherPrefs.getInt(ReadingProgressStore.comicTotalKey(newPath)), 99);
    expect(otherPrefs.getStringList('selura_bookmarks_v1:' + newPath),
        hasLength(1));
  });
}
