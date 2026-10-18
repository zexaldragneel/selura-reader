import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:io';

import 'package:shared_preferences/shared_preferences.dart';

/// Built-in, reviewed source adapters. Installing a source only enables its
/// Dart API client; Selura never executes downloaded APKs or untrusted scripts.
class MangaExtension {
  const MangaExtension({
    required this.id,
    required this.name,
    required this.description,
    required this.credit,
  });
  final String id;
  final String name;
  final String description;
  final String credit;
}

class MangaExtensionRegistry {
  static const mangadex = MangaExtension(
    id: 'mangadex',
    name: 'MangaDex',
    description: 'Browse and read English manga chapters online.',
    credit: 'Manga and images are supplied by MangaDex and their scanlation '
        'groups. Internet access required.',
  );
  static const nhentai = MangaExtension(
    id: 'nhentai',
    name: 'nHentai',
    description: 'Optional 18+ illustrated galleries from nHentai.',
    credit: 'Adult gallery source. Content and media are provided by '
        'nHentai and their uploaders. Internet and explicit opt-in required.',
  );
  static const available = <MangaExtension>[mangadex, nhentai];
}

class MangaExtensionStore {
  const MangaExtensionStore();

  static const key = 'selura_manga_enabled_sources_v1';

  Future<Set<String>> installed() async {
    final prefs = await SharedPreferences.getInstance();
    final values = prefs.getStringList(key) ?? <String>[];
    final known = MangaExtensionRegistry.available.map((e) => e.id).toSet();
    return values.where(known.contains).toSet();
  }

  Future<void> setInstalled(String id, bool enabled) async {
    if (!MangaExtensionRegistry.available.any((e) => e.id == id)) {
      throw ArgumentError.value(id, 'id', 'Unknown manga source');
    }
    final prefs = await SharedPreferences.getInstance();
    final current = await installed();
    if (enabled) {
      current.add(id);
    } else {
      current.remove(id);
    }
    final ordered = current.toList()..sort();
    if (!await prefs.setStringList(key, ordered)) {
      throw const FileSystemException('Manga source setting could not be saved');
    }
  }
}

class MangaSourceException implements Exception {
  const MangaSourceException(this.message);
  final String message;
  @override
  String toString() => message;
}

class OnlineManga {
  const OnlineManga({
    required this.id,
    required this.title,
    required this.description,
    this.coverUrl,
  });
  final String id;
  final String title;
  final String description;
  final Uri? coverUrl;
}

class OnlineMangaChapter {
  const OnlineMangaChapter({
    required this.id,
    required this.label,
    required this.group,
  });
  final String id;
  final String label;
  final String group;
}

/// An offset-paginated chapter feed. The total may include offsite chapters.
class OnlineMangaChapterPage {
  const OnlineMangaChapterPage({
    required this.chapters,
    required this.total,
    required this.nextOffset,
    required this.hasMore,
  });
  final List<OnlineMangaChapter> chapters;
  final int total;
  final int nextOffset;
  final bool hasMore;

  OnlineMangaChapterPage appended(OnlineMangaChapterPage next) =>
      OnlineMangaChapterPage(
        chapters: [...chapters, ...next.chapters],
        total: next.total,
        nextOffset: next.nextOffset,
        hasMore: next.hasMore,
      );
}

typedef MangaJsonLoader = Future<Map<String, dynamic>> Function(Uri uri);

const _mangaApiHost = 'api.mangadex.org';
const _idPattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';

bool _validId(String value) => RegExp(_idPattern).hasMatch(value);

String _languageString(dynamic value) {
  if (value is String && value.trim().isNotEmpty) return value.trim();
  if (value is Map) {
    final m = Map<String, dynamic>.from(value);
    for (final key in const ['en', 'ja-ro', 'ja', 'ko', 'zh', 'zh-ro']) {
      final candidate = m[key];
      if (candidate is String && candidate.trim().isNotEmpty) {
        return candidate.trim();
      }
    }
    for (final candidate in m.values) {
      if (candidate is String && candidate.trim().isNotEmpty) {
        return candidate.trim();
      }
    }
  }
  return '';
}

String _plainDescription(dynamic value) {
  final raw = _languageString(value).replaceAll(RegExp(r'<[^>]*>'), '');
  if (raw.length <= 800) return raw;
  return raw.substring(0, 800) + '…';
}

Map<String, dynamic> _map(dynamic item) =>
    item is Map ? Map<String, dynamic>.from(item) : <String, dynamic>{};

List<dynamic> _list(dynamic item) => item is List ? item : const <dynamic>[];

/// Strict TLS endpoint protection: remote JSON may only come from MangaDex.
Future<Map<String, dynamic>> readMangaDexJson(Uri uri) async {
  if (uri.scheme != 'https' || uri.host != _mangaApiHost ||
      uri.userInfo.isNotEmpty || uri.port != 443) {
    throw const MangaSourceException('Untrusted manga API address.');
  }
  final client = HttpClient()
    ..connectionTimeout = const Duration(seconds: 12);
  client.userAgent = 'SeluraReader/0.2 (personal eBook and manga reader)';
  try {
    final request = await client.getUrl(uri).timeout(const Duration(seconds: 15));
    request.followRedirects = false;
    request.headers.set(HttpHeaders.acceptHeader, 'application/json');
    final response = await request.close().timeout(const Duration(seconds: 20));
    if (response.statusCode == 429) {
      await response.drain<void>();
      throw const MangaSourceException(
        'MangaDex is rate-limiting requests. Please try again later.',
      );
    }
    if (response.statusCode != 200) {
      await response.drain<void>();
      throw MangaSourceException('MangaDex request failed (HTTP ' +
          response.statusCode.toString() + '). Try again later.');
    }
    final buffer = BytesBuilder(copy: false);
    await for (final bytes in response.timeout(const Duration(seconds: 20))) {
      buffer.add(bytes);
      if (buffer.length > 2 * 1024 * 1024) {
        throw const MangaSourceException('MangaDex response is too large.');
      }
    }
    final decoded = jsonDecode(utf8.decode(buffer.takeBytes()));
    if (decoded is! Map) {
      throw const MangaSourceException('Invalid MangaDex response.');
    }
    return Map<String, dynamic>.from(decoded);
  } on SocketException {
    throw const MangaSourceException(
      'No connection to MangaDex. Connect to the internet and retry.',
    );
  } on HandshakeException {
    throw const MangaSourceException('MangaDex TLS connection failed.');
  } on TimeoutException {
    throw const MangaSourceException('MangaDex took too long to respond.');
  } on FormatException {
    throw const MangaSourceException('MangaDex returned invalid data.');
  } finally {
    client.close(force: true);
  }
}

/// Uses only the documented MangaDex JSON API, without executing extensions.
/// The source requires a connection and is subject to MangaDex guest limits.
class MangaDexClient {
  MangaDexClient({MangaJsonLoader? fetchJson})
      : _fetchJson = fetchJson ?? readMangaDexJson;

  final MangaJsonLoader _fetchJson;

  static Uri _api(String path, Map<String, String> query) =>
      Uri.https(_mangaApiHost, path, query);

  Future<List<OnlineManga>> browse({String query = ''}) async {
    final terms = query.trim();
    if (terms.length > 100) {
      throw const MangaSourceException('Search term is too long.');
    }
    final params = <String, String>{
      'limit': '24',
      'includes[]': 'cover_art',
      'availableTranslatedLanguage[]': 'en',
      'contentRating[]': 'safe',
      'order[followedCount]': 'desc',
    };
    if (terms.isNotEmpty) params['title'] = terms;
    final raw = await _fetchJson(_api('/manga', params));
    if (raw['result'] == 'error') {
      throw const MangaSourceException('MangaDex could not complete this search.');
    }
    final results = <OnlineManga>[];
    for (final item in _list(raw['data'])) {
      final row = _map(item);
      final id = row['id'];
      if (id is! String || !_validId(id)) continue;
      final attrs = _map(row['attributes']);
      final title = _languageString(attrs['title']);
      if (title.isEmpty) continue;
      String? filename;
      for (final rel in _list(row['relationships'])) {
        final relation = _map(rel);
        if (relation['type'] != 'cover_art') continue;
        final f = _map(relation['attributes'])['fileName'];
        if (f is String && RegExp(r'^[a-zA-Z0-9._-]{1,150}$').hasMatch(f)) {
          filename = f;
        }
        break;
      }
      final cover = filename == null ? null : Uri.https(
        'uploads.mangadex.org',
        '/covers/' + id + '/' + filename + '.256.jpg',
      );
      results.add(OnlineManga(
        id: id, title: title, description: _plainDescription(attrs['description']),
        coverUrl: cover,
      ));
    }
    return results;
  }

  Future<List<OnlineMangaChapter>> chapters(
    String mangaId, {
    String? language = 'en',
  }) async => (await chapterPage(mangaId, language: language)).chapters;

  /// The offset counts raw feed rows, including skipped external chapters.
  Future<OnlineMangaChapterPage> chapterPage(
    String mangaId, {
    String? language = 'en',
    int offset = 0,
  }) async {
    if (!_validId(mangaId)) {
      throw const MangaSourceException('Invalid manga identifier.');
    }
    if (offset < 0 || offset > 10000) {
      throw const MangaSourceException('Invalid chapter feed offset.');
    }
    if (language != null &&
        !const {'en', 'ja', 'es', 'es-la', 'id', 'fil', 'fr', 'pt-br'}
            .contains(language)) {
      throw const MangaSourceException('Unsupported chapter language.');
    }
    final query = <String, String>{
      'limit': '100',
      'offset': offset.toString(),
      'includes[]': 'scanlation_group',
      'order[chapter]': 'asc',
      'includeExternalUrl': '0',
    };
    if (language != null) query['translatedLanguage[]'] = language;
    final raw = await _fetchJson(_api(
      '/manga/' + mangaId + '/feed', query,
    ));
    if (raw['result'] == 'error') {
      throw const MangaSourceException('MangaDex chapters are unavailable.');
    }
    final data = _list(raw['data']);
    final result = <OnlineMangaChapter>[];
    for (final item in data) {
      final row = _map(item);
      final id = row['id'];
      if (id is! String || !_validId(id)) continue;
      final attrs = _map(row['attributes']);
      if (attrs['externalUrl'] is String &&
          (attrs['externalUrl'] as String).isNotEmpty) continue;
      final translated = attrs['translatedLanguage'];
      if (translated is! String || translated.isEmpty) continue;
      if (language != null && translated != language) continue;
      final chapter = attrs['chapter']?.toString() ?? '?';
      final name = attrs['title'] is String
          ? (attrs['title'] as String).trim() : '';
      final label = (translated == 'en' ? '' : '[' + translated + '] ') +
          'Chapter ' + chapter + (name.isEmpty ? '' : ' · ' + name);
      var group = 'Unknown scanlation group';
      for (final rel in _list(row['relationships'])) {
        final relation = _map(rel);
        if (relation['type'] != 'scanlation_group') continue;
        final attr = _map(relation['attributes']);
        if (attr['name'] is String && (attr['name'] as String).isNotEmpty) {
          group = attr['name'] as String;
        }
        break;
      }
      result.add(OnlineMangaChapter(id: id, label: label, group: group));
    }
    final total = raw['total'] is int
        ? (raw['total'] as int).clamp(0, 1000000).toInt()
        : offset + data.length;
    final nextOffset = offset + data.length;
    return OnlineMangaChapterPage(
      chapters: result,
      total: total,
      nextOffset: nextOffset,
      hasMore: data.isNotEmpty && nextOffset < 10000 &&
          (nextOffset < total || (raw['total'] == null && data.length == 100)),
    );
  }

  Future<List<Uri>> chapterPages(String chapterId) async {
    if (!_validId(chapterId)) {
      throw const MangaSourceException('Invalid chapter identifier.');
    }
    final raw = await _fetchJson(_api(
      '/at-home/server/' + chapterId,
      {'forcePort443': 'true'},
    ));
    final base = Uri.tryParse(raw['baseUrl'] is String
        ? raw['baseUrl'] as String : '');
    if (base == null || base.scheme != 'https' || base.userInfo.isNotEmpty ||
        !(base.host == 'mangadex.org' ||
          base.host.endsWith('.mangadex.org') ||
          base.host == 'mangadex.network' ||
          base.host.endsWith('.mangadex.network'))) {
      throw const MangaSourceException('Unsafe MangaDex image server.');
    }
    final chapter = _map(raw['chapter']);
    final hash = chapter['hash'];
    if (hash is! String || !RegExp(r'^[0-9a-fA-F]{32}$').hasMatch(hash)) {
      throw const MangaSourceException('Invalid manga chapter data.');
    }
    final files = _list(chapter['dataSaver']).isNotEmpty
        ? _list(chapter['dataSaver']) : _list(chapter['data']);
    if (files.isEmpty || files.length > 350) {
      throw const MangaSourceException('This manga chapter has no usable pages.');
    }
    final quality = _list(chapter['dataSaver']).isNotEmpty
        ? 'data-saver' : 'data';
    final images = <Uri>[];
    for (final item in files) {
      if (item is! String ||
          !RegExp(r'^[a-zA-Z0-9._-]{1,180}$').hasMatch(item)) {
        throw const MangaSourceException('Invalid image filename in chapter.');
      }
      final path = base.pathSegments.where((e) => e.isNotEmpty).toList();
      images.add(base.replace(pathSegments: [
        ...path, quality, hash, item,
      ]));
    }
    return images;
  }
}
