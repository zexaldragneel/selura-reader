import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/manga_online_ui.dart';
import 'package:selura_reader/manga_sources.dart';
import 'package:selura_reader/nhentai_source.dart';
import 'package:shared_preferences/shared_preferences.dart';

const safePreview = <String, dynamic>{
  'result': [
    {
      'id': 12345,
      'english_title': 'Sample adult gallery',
      'num_pages': 2,
      'blacklisted': false,
    },
    {
      'id': 12346,
      'english_title': 'Restricted title not displayed',
      'num_pages': 3,
      'blacklisted': true,
    },
  ],
  'num_pages': 1,
};

const sampleDetail = <String, dynamic>{
  'id': 12345,
  'media_id': '45000',
  'title': {'english': 'Sample adult gallery'},
  'tags': [
    {'type': 'language', 'name': 'english'},
  ],
  'num_pages': 2,
  'pages': [
    {'number': 1, 'path': 'galleries/45000/1.jpg'},
    {'number': 2, 'path': 'galleries/45000/2.jpg'},
  ],
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  NhentaiSourceClient fakeClient([List<Uri>? calls]) =>
      NhentaiSourceClient(fetchJson: (uri) async {
        calls?.add(uri);
        if (uri.path == '/api/v2/galleries') return safePreview;
        if (uri.path == '/api/v2/search') return safePreview;
        if (uri.path == '/api/v2/galleries/12345') return sampleDetail;
        if (uri.path == '/api/v2/cdn') {
          return {
            'image_servers': ['https://i1.nhentai.net'],
            'thumb_servers': ['https://t1.nhentai.net'],
          };
        }
        throw StateError('Unexpected test API request');
      });

  test('text-only search uses HTTPS v2 API and limits results', () async {
    final calls = <Uri>[];
    final preview = await fakeClient(calls).browse(query: 'sample title');
    expect(preview, hasLength(1));
    expect(preview.single.title, 'Sample adult gallery');
    expect(preview.single.id, 12345);
    expect(preview.single.pageCount, 2);
    expect(calls.single.scheme, 'https');
    expect(calls.single.host, 'nhentai.net');
    expect(calls.single.path, '/api/v2/search');
    expect(calls.single.queryParameters['query'], 'sample title');

    final recent = await fakeClient(calls).browse();
    expect(recent, hasLength(1));
    expect(calls.last.path, '/api/v2/galleries');
    expect(calls.last.queryParameters['per_page'], '20');
  });

  test('verified page paths use trusted TLS CDN configuration', () async {
    final calls = <Uri>[];
    final item = await fakeClient(calls).gallery(12345);
    expect(item.id, 12345);
    expect(item.pages, hasLength(2));
    expect(item.pages[0].scheme, 'https');
    expect(item.pages[0].host, 'i1.nhentai.net');
    expect(item.pages[0].path, '/galleries/45000/1.jpg');
    expect(item.pages[1].path, '/galleries/45000/2.jpg');
    expect(calls.map((e) => e.path).toList(), [
      '/api/v2/galleries/12345',
      '/api/v2/cdn',
    ]);
  });

  test('unsafe image servers and archive paths are rejected', () async {
    final maliciousHost = NhentaiSourceClient(fetchJson: (uri) async {
      if (uri.path.endsWith('/cdn')) {
        return {'image_servers': ['https://nhentai.net.attacker.invalid']};
      }
      return sampleDetail;
    });
    await expectLater(maliciousHost.gallery(12345),
        throwsA(isA<NhentaiSourceException>()));

    final maliciousPage = NhentaiSourceClient(fetchJson: (uri) async {
      if (uri.path.endsWith('/cdn')) {
        return {'image_servers': ['https://i.nhentai.net']};
      }
      return {
        ...sampleDetail,
        'pages': [
          {'number': 1, 'path': '../../private.png'},
          {'number': 2, 'path': 'galleries/45000/2.jpg'},
        ],
      };
    });
    await expectLater(maliciousPage.gallery(12345),
        throwsA(isA<NhentaiSourceException>()));
  });

  test('blocked tag metadata never enters image reader', () async {
    expect(restrictedNhentaiLabel('ordinary'), isFalse);
    expect(restrictedNhentaiLabel('underage'), isTrue);
    final blocked = NhentaiSourceClient(fetchJson: (uri) async => {
      ...sampleDetail,
      'tags': [{'type': 'tag', 'name': 'underage'}],
    });
    await expectLater(blocked.gallery(12345),
        throwsA(isA<NhentaiSourceException>()));
  });

  test('official API host check rejects HTTP or unexpected API host', () async {
    await expectLater(
      readNhentaiApi(Uri.parse('http://nhentai.net/api/v2/galleries')),
      throwsA(isA<NhentaiSourceException>()),
    );
    await expectLater(
      readNhentaiApi(Uri.parse('https://nhentai.net.attacker.invalid/api/v2/galleries')),
      throwsA(isA<NhentaiSourceException>()),
    );
    await expectLater(
      fakeClient().gallery(0),
      throwsA(isA<NhentaiSourceException>()),
    );
  });

  testWidgets('18+ source requires confirmation before installation',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: MangaExtensionsPage(nhentaiClient: fakeClient()),
    ));
    await tester.pumpAndSettle();
    final nh = find.byKey(const Key('manga-extension-toggle-nhentai'));
    await tester.scrollUntilVisible(
      nh, 230,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(nh);
    await tester.pumpAndSettle();
    expect(find.text('Adult source · 18+'), findsOneWidget);
    await tester.tap(find.text('Cancel').last);
    await tester.pumpAndSettle();
    expect(await const MangaExtensionStore().installed(), isEmpty);

    await tester.scrollUntilVisible(
      nh, 230,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(nh);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nhentai-age-confirm')));
    await tester.pumpAndSettle();
    expect(await const MangaExtensionStore().installed(), {'nhentai'});

    final browse = find.byKey(const Key('manga-extension-browse-nhentai'));
    await tester.ensureVisible(browse);
    await tester.tap(browse);
    await tester.pumpAndSettle();
    expect(find.text('nHentai · Galleries'), findsOneWidget);
    expect(find.text('Sample adult gallery'), findsOneWidget);
    expect(find.byKey(const Key('nhentai-result-0')), findsOneWidget);
  });
}
