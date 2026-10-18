import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/manga_sources.dart';
import 'package:selura_reader/manga_online_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

const mangaId = '11111111-1111-4111-8111-111111111111';
const chapterId = '22222222-2222-4222-8222-222222222222';

final sampleManga = <String, dynamic>{
  'result': 'ok',
  'data': [
    {
      'id': mangaId,
      'attributes': {
        'title': {'en': 'Sample Space Adventure'},
        'description': {'en': 'An offline-safe metadata example'},
      },
      'relationships': [
        {
          'type': 'cover_art',
          'attributes': {'fileName': 'cover.jpeg'},
        },
      ],
    },
  ],
};

final sampleChapters = <String, dynamic>{
  'result': 'ok',
  'data': [
    {
      'id': chapterId,
      'attributes': {
        'chapter': '1',
        'title': 'A beginning',
        'translatedLanguage': 'en',
      },
      'relationships': [
        {
          'type': 'scanlation_group',
          'attributes': {'name': 'Volunteer Translators'},
        },
      ],
    },
    {
      'id': '33333333-3333-4333-8333-333333333333',
      'attributes': {
        'chapter': '2',
        'title': 'External reading only',
        'translatedLanguage': 'en',
        'externalUrl': 'https://example.com',
      },
    },
    {
      'id': '44444444-4444-4444-8444-444444444444',
      'attributes': {
        'chapter': '3',
        'translatedLanguage': 'fr',
      },
    },
  ],
};

final samplePages = <String, dynamic>{
  'baseUrl': 'https://reader.mangadex.network/temp-token',
  'chapter': {
    'hash': '0123456789abcdef0123456789abcdef',
    'data': ['one.png', 'two.png'],
    'dataSaver': ['one-saver.jpg', 'two-saver.jpg'],
  },
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  MangaDexClient fakeClient([List<Uri>? visited]) => MangaDexClient(
    fetchJson: (uri) async {
      visited?.add(uri);
      if (uri.path == '/manga') return sampleManga;
      if (uri.path.endsWith('/feed')) return sampleChapters;
      if (uri.path.startsWith('/at-home/server/')) return samplePages;
      throw StateError('Unexpected test API request: ' + uri.toString());
    },
  );

  test('install and uninstall is persisted, idempotent and allowlisted', () async {
    const store = MangaExtensionStore();
    expect(await store.installed(), isEmpty);
    await store.setInstalled('mangadex', true);
    expect(await store.installed(), {'mangadex'});
    await store.setInstalled('mangadex', true);
    expect(await store.installed(), hasLength(1));
    await store.setInstalled('mangadex', false);
    expect(await store.installed(), isEmpty);
    expect(
      () => store.setInstalled('unreviewed-apk', true),
      throwsArgumentError,
    );
  });

  test('browse uses safe titles, English availability and cover art', () async {
    final visited = <Uri>[];
    final manga = await fakeClient(visited).browse(query: 'space & time');
    expect(manga, hasLength(1));
    expect(manga.single.title, 'Sample Space Adventure');
    expect(manga.single.description, contains('metadata example'));
    expect(manga.single.coverUrl?.host, 'uploads.mangadex.org');
    expect(visited.single.scheme, 'https');
    expect(visited.single.host, 'api.mangadex.org');
    expect(visited.single.queryParameters['title'], 'space & time');
    expect(visited.single.queryParameters['availableTranslatedLanguage[]'], 'en');
    expect(visited.single.queryParameters['contentRating[]'], 'safe');
  });

  test('chapter feed honors language and scanlation group credit', () async {
    final chapters = await fakeClient().chapters(mangaId);
    expect(chapters, hasLength(1));
    expect(chapters.single.id, chapterId);
    expect(chapters.single.label, 'Chapter 1 · A beginning');
    expect(chapters.single.group, 'Volunteer Translators');
  });

  test('image page URLs come from MangaDex server and not arbitrary hosts',
      () async {
    final imageUrls = await fakeClient().chapterPages(chapterId);
    expect(imageUrls, hasLength(2));
    expect(imageUrls.first.scheme, 'https');
    expect(imageUrls.first.host, 'reader.mangadex.network');
    expect(imageUrls.first.path,
      '/temp-token/data-saver/0123456789abcdef0123456789abcdef/one-saver.jpg');

    final malicious = MangaDexClient(fetchJson: (_) async => {
      ...samplePages,
      'baseUrl': 'https://mangadex.network.attacker.test/token',
    });
    await expectLater(malicious.chapterPages(chapterId),
        throwsA(isA<MangaSourceException>()));
    await expectLater(
      fakeClient().chapterPages('not-an-id'),
      throwsA(isA<MangaSourceException>()),
    );
  });

  test('manga API only allows the official HTTPS host', () async {
    await expectLater(
      readMangaDexJson(Uri.parse('http://api.mangadex.org/manga')),
      throwsA(isA<MangaSourceException>()),
    );
    await expectLater(
      readMangaDexJson(Uri.parse('https://api.mangadex.org.evil.test/manga')),
      throwsA(isA<MangaSourceException>()),
    );
  });

  test('MangaDex chapter feed supports language fallback and pagination', () async {
    final captured = <Uri>[];
    final client = MangaDexClient(fetchJson: (uri) async {
      captured.add(uri);
      if (uri.queryParameters['offset'] == '100') {
        return {
          'result': 'ok',
          'total': 101,
          'data': [
            {
              'id': '99999999-9999-4999-8999-999999999999',
              'attributes': {
                'chapter': '101',
                'translatedLanguage': 'fr',
              },
            },
          ],
        };
      }
      return {
        'result': 'ok',
        'total': 101,
        'data': List.generate(100, (index) => {
          'id': '11111111-1111-4111-8111-' +
              index.toString().padLeft(12, '0'),
          'attributes': {
            'chapter': (index + 1).toString(),
            'translatedLanguage': index == 0 ? 'fr' : 'en',
            if (index == 1) 'externalUrl': 'https://example.com',
          },
        }),
      };
    });

    final first = await client.chapterPage(mangaId, language: null);
    expect(first.total, 101);
    expect(first.nextOffset, 100);
    expect(first.hasMore, isTrue);
    expect(first.chapters, hasLength(99));
    expect(first.chapters.first.label, '[fr] Chapter 1');
    expect(first.chapters.any((item) => item.label == 'Chapter 2'), isFalse);
    expect(captured.first.queryParameters.containsKey('translatedLanguage[]'),
        isFalse);

    final more = await client.chapterPage(mangaId,
        language: null, offset: first.nextOffset);
    final whole = first.appended(more);
    expect(more.hasMore, isFalse);
    expect(whole.chapters, hasLength(100));
    expect(whole.chapters.last.label, '[fr] Chapter 101');
    expect(captured.last.queryParameters['offset'], '100');

    await client.chapterPage(mangaId, language: 'id');
    expect(captured.last.queryParameters['translatedLanguage[]'], 'id');
    await expectLater(
      client.chapterPage(mangaId, offset: -1),
      throwsA(isA<MangaSourceException>()),
    );
  });

  testWidgets('install source then navigate to working manga catalog',
      (tester) async {
    // No live internet access is needed for the UI integration test.
    final noCover = <String, dynamic>{
      'result': 'ok',
      'data': [
        {
          'id': mangaId,
          'attributes': {
            'title': {'en': 'Sample Space Adventure'},
            'description': {'en': 'A sample manga'},
          },
          'relationships': [],
        },
      ],
    };
    final client = MangaDexClient(fetchJson: (uri) async {
      if (uri.path == '/manga') return noCover;
      if (uri.path.endsWith('/feed')) return sampleChapters;
      throw StateError('Unexpected path');
    });
    await tester.pumpWidget(MaterialApp(
      home: MangaExtensionsPage(client: client),
    ));
    await tester.pumpAndSettle();
    expect(find.text('MangaDex'), findsOneWidget);
    expect(find.byKey(const Key('manga-extension-browse-mangadex')), findsNothing);

    await tester.tap(find.byKey(const Key('manga-extension-toggle-mangadex')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('manga-extension-browse-mangadex')), findsOneWidget);

    await tester.tap(find.byKey(const Key('manga-extension-browse-mangadex')));
    await tester.pumpAndSettle();
    expect(find.text('Sample Space Adventure'), findsOneWidget);

    await tester.tap(find.byKey(const Key('manga-result-0')));
    await tester.pumpAndSettle();
    expect(find.text('Chapter 1 · A beginning'), findsOneWidget);
    expect(find.text('Scanlation: Volunteer Translators'), findsOneWidget);
  });
}
