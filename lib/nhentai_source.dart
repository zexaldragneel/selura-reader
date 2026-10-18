import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

/// Official nHentai v2 API adapter. An opt-in, adult-only source.
/// This code does not bypass authentication, CAPTCHA, PoW or access controls.
typedef NhentaiJsonLoader = Future<Map<String, dynamic>> Function(Uri uri);

class NhentaiSourceException implements Exception {
  const NhentaiSourceException(this.message);
  final String message;
  @override
  String toString() => message;
}

class NhentaiPreview {
  const NhentaiPreview({
    required this.id,
    required this.title,
    required this.pageCount,
  });
  final int id;
  final String title;
  final int pageCount;
}

class NhentaiGallery {
  const NhentaiGallery({
    required this.id,
    required this.title,
    required this.pages,
    required this.credit,
  });
  final int id;
  final String title;
  final List<Uri> pages;
  final String credit;
}

/// Never show restricted material based on known title/tag indicators.
/// This is a precaution and does not replace legal/content review.
bool restrictedNhentaiLabel(String value) {
  final normalized = value.toLowerCase().replaceAll(
    RegExp(r'[^a-z0-9]+'), ' ',
  );
  return RegExp(
    r'\b(loli|lolicon|shota|shotacon|underage|minor|child|children|'
    r'bestiality|zoophilia)\b',
  ).hasMatch(normalized);
}

bool _officialHost(String host) =>
    host == 'nhentai.net' || host.endsWith('.nhentai.net');

bool _safeCdnHost(Uri uri) =>
    uri.scheme == 'https' &&
    uri.userInfo.isEmpty &&
    uri.port == 443 &&
    _officialHost(uri.host);

Map<String, dynamic> _asMap(dynamic value) =>
    value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};

List<dynamic> _asList(dynamic value) =>
    value is List ? value : const <dynamic>[];

/// Public API only, using bounded JSON responses. No cookies, proxying,
/// anti-bot challenge solving or user API keys are requested.
Future<Map<String, dynamic>> readNhentaiApi(Uri uri) async {
  if (!_safeCdnHost(uri) || uri.host != 'nhentai.net' ||
      !uri.path.startsWith('/api/v2/')) {
    throw const NhentaiSourceException('Untrusted gallery API address.');
  }
  final client = HttpClient()
    ..connectionTimeout = const Duration(seconds: 12);
  client.userAgent = 'SeluraReader/0.2 (personal comic reader)';
  try {
    final req = await client.getUrl(uri).timeout(
      const Duration(seconds: 15),
    );
    req.followRedirects = false;
    req.headers.set(HttpHeaders.acceptHeader, 'application/json');
    final res = await req.close().timeout(const Duration(seconds: 20));
    if (res.statusCode == 429) {
      await res.drain<void>();
      throw const NhentaiSourceException(
        'Gallery source rate limit reached. Try again later.',
      );
    }
    if (res.statusCode == 401 || res.statusCode == 403) {
      await res.drain<void>();
      throw const NhentaiSourceException(
        'This source requires an account or access verification. '
        'Open its official website separately; Selura cannot bypass this.',
      );
    }
    if (res.statusCode != 200) {
      await res.drain<void>();
      throw NhentaiSourceException(
        'Gallery source unavailable (HTTP ' +
        res.statusCode.toString() + ').',
      );
    }
    final buffer = BytesBuilder(copy: false);
    await for (final chunk in res.timeout(const Duration(seconds: 20))) {
      buffer.add(chunk);
      if (buffer.length > 2 * 1024 * 1024) {
        throw const NhentaiSourceException('Gallery response is too large.');
      }
    }
    final decoded = jsonDecode(utf8.decode(buffer.takeBytes()));
    if (decoded is! Map) {
      throw const NhentaiSourceException('Invalid gallery response.');
    }
    return Map<String, dynamic>.from(decoded);
  } on SocketException {
    throw const NhentaiSourceException(
      'Cannot reach gallery source. Check your connection.',
    );
  } on HandshakeException {
    throw const NhentaiSourceException(
      'Gallery TLS connection failed.',
    );
  } on TimeoutException {
    throw const NhentaiSourceException(
      'Gallery source timed out. Try again later.',
    );
  } on FormatException {
    throw const NhentaiSourceException(
      'Gallery source returned malformed JSON.',
    );
  } finally {
    client.close(force: true);
  }
}

/// nHentai has galleries (single volumes), not conventional chapter feeds.
/// Metadata is deliberately text-only in the catalogue; no adult cover
/// thumbnails are fetched before a gallery is selected and validated.
class NhentaiSourceClient {
  NhentaiSourceClient({NhentaiJsonLoader? fetchJson})
      : _fetchJson = fetchJson ?? readNhentaiApi;

  final NhentaiJsonLoader _fetchJson;

  static Uri _api(String path, [Map<String, String>? query]) =>
      Uri.https('nhentai.net', '/api/v2/' + path, query);

  Future<List<NhentaiPreview>> browse({
    String query = '',
    int page = 1,
  }) async {
    if (page < 1 || page > 30) {
      throw const NhentaiSourceException('Invalid page number.');
    }
    final term = query.trim();
    if (term.length > 80 || restrictedNhentaiLabel(term)) {
      throw const NhentaiSourceException('Unsupported search term.');
    }
    final uri = term.isEmpty
        ? _api('galleries', {'page': page.toString(), 'per_page': '20'})
        : _api('search', {
            'query': term,
            'page': page.toString(),
            'sort': 'date',
          });
    final decoded = await _fetchJson(uri);
    final results = <NhentaiPreview>[];
    for (final raw in _asList(decoded['result'])) {
      final data = _asMap(raw);
      final id = data['id'];
      final title = data['english_title'];
      final count = data['num_pages'];
      if (data['blacklisted'] == true || id is! int || id < 1 ||
          title is! String || title.isEmpty ||
          restrictedNhentaiLabel(title) ||
          count is! int || count < 1 || count > 350) {
        continue;
      }
      results.add(NhentaiPreview(
        id: id,
        title: title.length > 180 ? title.substring(0, 180) : title,
        pageCount: count,
      ));
    }
    return results;
  }

  /// Constructs only official, HTTPS image URLs using server configuration
  /// supplied by the provider, never third-party hostnames in gallery JSON.
  Future<NhentaiGallery> gallery(int id) async {
    if (id < 1 || id > 999999999) {
      throw const NhentaiSourceException('Invalid gallery ID.');
    }
    final data = await _fetchJson(_api('galleries/' + id.toString()));
    if (data['id'] != id) {
      throw const NhentaiSourceException('Invalid gallery metadata.');
    }
    final tagList = _asList(data['tags']);
    if (tagList.isEmpty || tagList.any((row) {
      final tag = _asMap(row);
      return restrictedNhentaiLabel(tag['name']?.toString() ?? '');
    })) {
      throw const NhentaiSourceException(
        'This gallery is unavailable in Selura.',
      );
    }
    final title = _asMap(data['title'])['english'];
    if (title is! String || title.isEmpty || restrictedNhentaiLabel(title)) {
      throw const NhentaiSourceException(
        'This gallery is unavailable in Selura.',
      );
    }
    final entries = _asList(data['pages']);
    if (entries.isEmpty || entries.length > 350) {
      throw const NhentaiSourceException(
        'This gallery has no supported pages.',
      );
    }
    final config = await _fetchJson(_api('cdn'));
    final serverValues = _asList(config['image_servers']);
    final servers = <Uri>[];
    for (final item in serverValues) {
      if (item is! String) continue;
      final server = Uri.tryParse(item.contains('://') ? item : 'https://' + item);
      if (server != null && _safeCdnHost(server)) servers.add(server);
    }
    if (servers.isEmpty) {
      throw const NhentaiSourceException('No trusted image server available.');
    }
    final urls = <Uri>[];
    final server = servers.first;
    final mediaId = data['media_id']?.toString();
    if (mediaId == null || !RegExp(r'^\d{1,15}$').hasMatch(mediaId)) {
      throw const NhentaiSourceException('Invalid gallery media identifier.');
    }
    for (var i = 0; i < entries.length; i++) {
      final row = _asMap(entries[i]);
      final sequence = row['number'];
      if (sequence != i + 1) {
        throw const NhentaiSourceException('Invalid gallery page sequence.');
      }
      final value = row['path'];
      if (value is! String || value.isEmpty) {
        throw const NhentaiSourceException('Invalid gallery image location.');
      }
      // v2 supplies an image path. Accept only official, HTTPS CDN URLs or
      // sanitized relative paths. Never use arbitrary redirects or protocols.
      final parsed = Uri.tryParse(value);
      if (parsed == null) {
        throw const NhentaiSourceException('Invalid image URI.');
      }
      final Uri result;
      if (parsed.hasScheme) {
        if (!_safeCdnHost(parsed)) {
          throw const NhentaiSourceException('Unsafe image server.');
        }
        result = parsed;
      } else {
        if (parsed.hasAuthority || value.contains('..') ||
            value.contains('\\') || value.contains('?') ||
            value.contains('#')) {
          throw const NhentaiSourceException('Unsafe image path.');
        }
        final parts = parsed.pathSegments.where((p) => p.isNotEmpty).toList();
        if (parts.isEmpty || parts.length > 6 ||
            parts.any((p) => !RegExp(r'^[a-zA-Z0-9._-]+$').hasMatch(p))) {
          throw const NhentaiSourceException('Unsafe image filename.');
        }
        result = server.replace(pathSegments: parts, query: null);
      }
      urls.add(result);
    }
    return NhentaiGallery(
      id: id,
      title: title,
      pages: urls,
      credit: 'Images and gallery data provided by nHentai. '
          'Rights belong to the original creators and uploaders.',
    );
  }
}
