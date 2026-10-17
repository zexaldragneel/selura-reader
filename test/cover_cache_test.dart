import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as image;
import 'package:selura_reader/cover_cache.dart';

void main() {
  test('large cover images are reduced without changing their proportions', () {
    final pixels = image.Image(800, 1200);
    final bytes = encodeCoverThumbnail(pixels);
    final result = image.decodeJpg(bytes);
    expect(result, isNotNull);
    expect(result!.width, 480);
    expect(result.height, 720);
  });

  test('small cover images are not enlarged', () {
    final pixels = image.Image(120, 180);
    final result = image.decodeJpg(encodeCoverThumbnail(pixels));
    expect(result!.width, 120);
    expect(result.height, 180);
  });

  test('reads a declared cover from a local EPUB archive', () async {
    final archive = Archive();

    void addText(String name, String value) {
      final data = utf8.encode(value);
      archive.addFile(ArchiveFile(name, data.length, data));
    }

    addText('mimetype', 'application/epub+zip');
    addText('META-INF/container.xml', '''
<?xml version="1.0" encoding="utf-8"?>
<container version="1.0"
 xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
 <rootfiles>
  <rootfile full-path="OEBPS/content.opf"
   media-type="application/oebps-package+xml"/>
 </rootfiles>
</container>
''');
    addText('OEBPS/content.opf', '''
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
 version="2.0" unique-identifier="uid">
 <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Selura Cover Fixture</dc:title>
  <dc:identifier id="uid">selura-cover-test</dc:identifier>
  <meta name="cover" content="cover-image"/>
 </metadata>
 <manifest>
  <item id="cover-image" href="cover.png" media-type="image/png"/>
  <item id="chapter1" href="chapter.xhtml"
    media-type="application/xhtml+xml"/>
 </manifest>
 <spine>
  <itemref idref="chapter1"/>
 </spine>
</package>
''');
    addText('OEBPS/chapter.xhtml', '''
<html xmlns="http://www.w3.org/1999/xhtml">
 <head><title>Chapter 1</title></head>
 <body><p>Cover image regression test.</p></body>
</html>
''');
    final coverBytes = image.encodePng(image.Image(320, 480));
    archive.addFile(
      ArchiveFile('OEBPS/cover.png', coverBytes.length, coverBytes),
    );

    final folder = await Directory.systemTemp.createTemp('selura-cover-');
    addTearDown(() => folder.delete(recursive: true));
    final epub = File(folder.path + '/test.epub');
    await epub.writeAsBytes(ZipEncoder().encode(archive)!);

    final jpegBytes = await readCoverThumbnail(epub.path);
    expect(jpegBytes, isNotNull);
    final decoded = image.decodeJpg(jpegBytes!);
    expect(decoded, isNotNull);
    expect(decoded!.width, 320);
    expect(decoded.height, 480);
  });

  test('corrupt EPUB falls back without crashing', () async {
    final folder = await Directory.systemTemp.createTemp('selura-bad-');
    addTearDown(() => folder.delete(recursive: true));
    final epub = File(folder.path + '/invalid.epub');
    await epub.writeAsString('This is not an EPUB');
    expect(await readCoverThumbnail(epub.path), isNull);
  });
}
