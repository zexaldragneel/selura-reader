import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/mihon_backup.dart';
import 'package:selura_reader/mihon_library_ui.dart';

List<int> _varint(int value) {
  final bytes = <int>[];
  var current = value;
  while (current > 127) {
    bytes.add((current & 127) | 128);
    current >>= 7;
  }
  bytes.add(current);
  return bytes;
}

List<int> _num(int tag, int value) =>
    [..._varint(tag << 3), ..._varint(value)];
List<int> _entry(int tag, List<int> bytes) =>
    [..._varint((tag << 3) | 2), ..._varint(bytes.length), ...bytes];
List<int> _text(int tag, String s) => _entry(tag, utf8.encode(s));

List<int> _sampleBackup({
  String title = 'Library Manga',
  bool favorite = true,
  int source = 42,
  String mangaUrl = '/title/11111111-1111-4111-8111-111111111111',
}) {
  final chapterOne = [
    ..._text(1, '/chapter/22222222-2222-4222-8222-222222222222'),
    ..._text(2, 'Chapter 1'),
    ..._num(4, 1), // read
    ..._num(5, 1), // bookmarked
    ..._num(6, 3), // lastPageRead
  ];
  final chapterTwo = [
    ..._text(1, '/chapter/33333333-3333-4333-8333-333333333333'),
    ..._text(2, 'Chapter 2'),
    ..._num(6, 8), // current progress on unread chapter
  ];
  final mangaHistory = [
    ..._text(1, '/chapter/22222222-2222-4222-8222-222222222222'),
    ..._num(2, 1729000000000),
  ];
  final manga = [
    ..._num(1, source),
    ..._text(2, mangaUrl),
    ..._text(3, title),
    ..._text(4, 'Test Artist'),
    ..._text(5, 'Test Author'),
    ..._text(6, 'Synopsis'),
    ..._text(9, 'https://example.invalid/cover.jpg'),
    ..._num(13, 1729000000000),
    ..._entry(16, chapterOne),
    ..._entry(16, chapterTwo),
    ..._entry(17, [..._varint(7), ..._varint(9)]),
    ..._num(100, favorite ? 1 : 0),
    ..._entry(104, mangaHistory),
    ..._text(108, 'ignored future field'), // unknown string
  ];
  final categoryOne = [
    ..._text(1, 'Favorites'),
    ..._num(2, 7),
    ..._num(3, 71),
  ];
  final categoryTwo = [
    ..._text(1, 'On Hold'),
    ..._num(2, 9),
    ..._num(3, 91),
  ];
  final sourceMeta = [
    ..._text(1, 'MangaDex'),
    ..._num(2, source),
  ];
  return [
    ..._entry(1, manga),
    ..._entry(2, categoryOne),
    ..._entry(2, categoryTwo),
    ..._entry(101, sourceMeta),
    ..._entry(106, _text(1, 'ignored extension setting')),
  ];
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory temp;
  setUp(() async {
    temp = await Directory.systemTemp.createTemp('selura_mihon_');
  });
  tearDown(() async {
    if (await temp.exists()) await temp.delete(recursive: true);
  });

  test('parses upstream Mihon ProtoBuf manga, chapters, history, categories',
      () {
    final model = decodeMihonProto(Uint8List.fromList(_sampleBackup()));
    expect(model.manga, hasLength(1));
    expect(model.categories.map((item) => item.name),
        ['Favorites', 'On Hold']);
    expect(model.sources[42], 'MangaDex');
    expect(model.chapterCount, 2);
    expect(model.readChapters, 1);
    final book = model.manga.single;
    expect(book.title, 'Library Manga');
    expect(book.author, 'Test Author');
    expect(book.artist, 'Test Artist');
    expect(book.source, 42);
    expect(book.sourceName, 'MangaDex');
    expect(book.favorite, isTrue);
    expect(book.dateAdded, 1729000000000);
    expect(book.categoryOrders, [7, 9]);
    expect(book.chapters.first.read, isTrue);
    expect(book.chapters.first.bookmarked, isTrue);
    expect(book.chapters.first.lastPageRead, 3);
    expect(book.chapters.first.lastRead, 1729000000000);
    expect(book.resumeChapter?.name, 'Chapter 2');
    expect(book.resumeChapter?.lastPageRead, 8);
    expect(mihonMangaDexId(book),
        '11111111-1111-4111-8111-111111111111');
  });

  test('reads gzip and uncompressed Mihon backups in worker isolate',
      () async {
    final source = _sampleBackup();
    final gzipFile = await File(temp.path + '/mihon.tachibk')
        .writeAsBytes(gzip.encode(source));
    const store = MihonBackupStore();
    final result = await store.preview(gzipFile);
    expect(result.manga.single.title, 'Library Manga');
    final raw = await File(temp.path + '/mihon-protobuf.backup')
        .writeAsBytes(source);
    final plain = await store.preview(raw);
    expect(plain.manga.single.chapters, hasLength(2));
  });

  test('restore merges by source and URL and persists original progress',
      () async {
    final store = MihonBackupStore(directory: temp);
    final first = decodeMihonProto(Uint8List.fromList(_sampleBackup()));
    final report1 = await store.restore(first);
    expect(report1.added, 1);
    expect(report1.updated, 0);
    expect(report1.total, 1);

    final after1 = await store.load();
    expect(after1.manga.single.chapters.last.lastPageRead, 8);
    expect(after1.manga.single.chapters.first.bookmarked, isTrue);
    expect(after1.categories, hasLength(2));

    final same = await store.restore(first);
    expect(same.added, 0);
    expect(same.updated, 1);
    expect((await store.load()).manga.length, 1);

    final updated = decodeMihonProto(Uint8List.fromList(_sampleBackup(
      title: 'Updated volume',
      favorite: false,
    )));
    final report2 = await store.restore(updated);
    expect(report2.updated, 1);
    expect((await store.load()).manga.single.title, 'Updated volume');
    expect((await store.load()).manga.single.favorite, isFalse);
    expect((await store.load()).readChapters, 1);

    final another = decodeMihonProto(Uint8List.fromList(_sampleBackup(
      source: 77, mangaUrl: '/different/source',
    )));
    final report3 = await store.restore(another);
    expect(report3.added, 1);
    expect((await store.load()).manga, hasLength(2));
  });

  test('rejects invalid wire tags, corrupt gzip and unsafe empty records',
      () async {
    expect(() => decodeMihonProto(Uint8List.fromList([0])),
        throwsA(isA<FormatException>()));
    expect(() => decodeMihonProto(Uint8List.fromList([0x0a, 0xff])),
        throwsA(isA<FormatException>()));
    expect(() => decodeMihonProto(Uint8List.fromList([])),
        throwsA(isA<FormatException>()));
    expect(() => decodeMihonProto(Uint8List.fromList(
        _entry(1, _num(1, 42)))),
        throwsA(isA<FormatException>()));
    final bad = await File(temp.path + '/corrupt.tachibk')
        .writeAsBytes([0x1f, 0x8b, 0, 1, 2]);
    await expectLater(const MihonBackupStore().preview(bad),
        throwsA(isA<Exception>()));
    expect((await MihonBackupStore(directory: temp).load()).manga, isEmpty);
  });

  testWidgets('restored manga library searches, filters and shows chapter states',
      (tester) async {
    final data = decodeMihonProto(Uint8List.fromList(_sampleBackup()));
    await tester.pumpWidget(MaterialApp(
      home: MihonLibraryPage(initialLibrary: data),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Your Mihon collection'), findsOneWidget);
    expect(find.text('Library Manga'), findsOneWidget);
    expect(find.byKey(const Key('mihon-import-button')), findsOneWidget);
    await tester.enterText(find.byKey(const Key('mihon-search')), 'not-found');
    await tester.pumpAndSettle();
    expect(find.text('Library Manga'), findsNothing);
    await tester.enterText(find.byKey(const Key('mihon-search')), 'mangadex');
    await tester.pumpAndSettle();
    final row = find.text('Library Manga');
    expect(row, findsOneWidget);
    await tester.ensureVisible(row);
    await tester.tap(row);
    await tester.pumpAndSettle();
    expect(find.text('Chapter 1'), findsOneWidget);
    expect(find.text('Chapter 2'), findsOneWidget);
    expect(find.byKey(const Key('mihon-read-with-mangadex')),
        findsOneWidget);
    expect(find.textContaining('Last page 8'), findsOneWidget);
  });
}
