import 'dart:io';

import 'package:archive/archive_io.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as image;
import 'package:selura_reader/comic_archive.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory temp;
  late List<int> png;

  setUp(() async {
    temp = await Directory.systemTemp.createTemp('selura_cbz_');
    png = image.encodePng(image.Image(8, 12));
  });

  tearDown(() async {
    if (await temp.exists()) await temp.delete(recursive: true);
  });

  Future<File> createComic(List<String> names) async {
    final zip = File(temp.path + '/comic.cbz');
    final encoder = ZipFileEncoder();
    encoder.create(zip.path);
    for (var i = 0; i < names.length; i++) {
      final path = temp.path + '/source_' + i.toString() + '.png';
      final source = await File(path).writeAsBytes(png);
      await encoder.addFile(source, names[i]);
    }
    encoder.closeSync();
    return zip;
  }

  test('naturally sorts pages and numbered chapter directories', () async {
    final zip = await createComic([
      'chapter10/page10.png',
      'chapter2/page10.png',
      'chapter2/page2.png',
      'chapter1/page1.png',
      'ComicInfo.xml',
      '__MACOSX/.DS_Store',
    ]);
    final archive = await ComicArchive.open(zip.path);
    expect(archive.pages.map((page) => page.name).toList(), [
      'chapter1/page1.png',
      'chapter2/page2.png',
      'chapter2/page10.png',
      'chapter10/page10.png',
    ]);
    expect(archive.pages.every((page) => page.bytes == png.length), isTrue);
    expect(naturalComicOrder('page9.jpg', 'page10.jpg'), lessThan(0));
    expect(naturalComicOrder('Chapter12/1.png', 'Chapter2/1.png'),
        greaterThan(0));
  });

  test('extracts a selected page without touching source archive', () async {
    final zip = await createComic([
      'page10.png', 'page2.png', 'page1.png',
    ]);
    final archive = await ComicArchive.open(zip.path);
    final dir = Directory(temp.path + '/cache');
    await dir.create();
    final cache = ComicPageCache.forTesting(archive, dir);
    final second = await cache.page(1);
    expect(second.path, endsWith('page-1.png'));
    expect(await second.readAsBytes(), png);
    expect(await cache.page(1), second);
    expect(await zip.exists(), isTrue);
    expect(await zip.length(), greaterThan(0));
    expect(() => cache.page(99), throwsRangeError);
  });

  test('rejects empty comics, unsafe archive paths and duplicates', () async {
    final noImages = await createComic(['ComicInfo.xml']);
    await expectLater(ComicArchive.open(noImages.path),
        throwsA(isA<FormatException>()));

    final bad = await createComic(['../escape.png']);
    await expectLater(ComicArchive.open(bad.path),
        throwsA(isA<FormatException>()));

    final repeated = await createComic(['page1.png', 'PAGE1.PNG']);
    await expectLater(ComicArchive.open(repeated.path),
        throwsA(isA<FormatException>()));
  });

  test('rejects fake CBZ and missing local files', () async {
    final invalid = await File(temp.path + '/broken.cbz')
        .writeAsString('Not really a ZIP file');
    await expectLater(ComicArchive.open(invalid.path), throwsA(isA<Exception>()));
    await expectLater(
      ComicArchive.open(temp.path + '/not-found.cbz'),
      throwsA(isA<FormatException>()),
    );
  });
}
