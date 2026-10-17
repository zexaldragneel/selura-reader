import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/bookmarks.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const store = BookmarkStore();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  test('bookmarks are persisted and separated for each book', () async {
    final first = await store.add(
      bookPath: '/books/a.epub',
      location: 'epubcfi(/6/2!/4/2:5)',
      label: 'EPUB reading position',
    );
    final second = await store.add(
      bookPath: '/books/b.pdf',
      location: '42',
      label: 'Page 42',
    );
    expect(first, isTrue);
    expect(second, isTrue);
    final epub = await store.load('/books/a.epub');
    final pdf = await store.load('/books/b.pdf');
    expect(epub, hasLength(1));
    expect(pdf, hasLength(1));
    expect(epub.single.location, 'epubcfi(/6/2!/4/2:5)');
    expect(pdf.single.location, '42');
    expect(await store.load('/books/another.epub'), isEmpty);
  });

  test('duplicate locations are ignored without losing other bookmarks', () async {
    const book = '/books/one.epub';
    expect(
      await store.add(bookPath: book, location: 'epubcfi(/6/2)', label: 'First'),
      isTrue,
    );
    expect(
      await store.add(bookPath: book, location: 'epubcfi(/6/2)', label: 'Again'),
      isFalse,
    );
    expect(
      await store.add(bookPath: book, location: 'epubcfi(/6/4)', label: 'Next'),
      isTrue,
    );
    expect((await store.load(book)).length, 2);
  });

  test('delete removes only the selected bookmark', () async {
    const book = '/books/a.pdf';
    await store.add(bookPath: book, location: '2', label: 'Page 2');
    await store.add(bookPath: book, location: '7', label: 'Page 7');
    final selected = (await store.load(book)).firstWhere(
      (item) => item.location == '2',
    );
    expect(
      await store.delete(bookPath: book, bookmarkId: selected.id),
      isTrue,
    );
    final remaining = await store.load(book);
    expect(remaining.map((item) => item.location), ['7']);
    expect(
      await store.delete(bookPath: book, bookmarkId: selected.id),
      isFalse,
    );
  });

  test('corrupt saved records do not hide valid bookmarks', () async {
    final good = jsonEncode({
      'id': 'valid',
      'location': '9',
      'label': 'Page 9',
      'createdAt': 42,
    });
    SharedPreferences.setMockInitialValues({
      'selura_bookmarks_v1:/books/test.pdf': [
        'broken-json',
        good,
        jsonEncode({
          'id': '',
          'location': '',
          'label': 'Broken',
          'createdAt': -1,
        }),
      ],
    });
    final values = await store.load('/books/test.pdf');
    expect(values, hasLength(1));
    expect(values.single.label, 'Page 9');
  });

  test('blank locations cannot be bookmarked', () async {
    expect(
      await store.add(bookPath: '/books/test.epub', location: '', label: ''),
      isFalse,
    );
    expect(await store.load('/books/test.epub'), isEmpty);
  });
}
