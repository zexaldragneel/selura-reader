import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'manga_sources.dart';

/// Installable, curated sources—not APK plugins, executable downloads or
/// third-party scripts. Installing just enables a reviewed API adapter.
class MangaExtensionsPage extends StatefulWidget {
  const MangaExtensionsPage({super.key, this.client});
  final MangaDexClient? client;

  @override
  State<MangaExtensionsPage> createState() => _MangaExtensionsPageState();
}

class _MangaExtensionsPageState extends State<MangaExtensionsPage> {
  final MangaExtensionStore _store = const MangaExtensionStore();
  bool _loading = true;
  bool _updating = false;
  Set<String> _installed = <String>{};

  @override
  void initState() {
    super.initState();
    unawaited(_read());
  }

  Future<void> _read() async {
    try {
      final installed = await _store.installed();
      if (mounted) {
        setState(() {
          _installed = installed;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _toggle(MangaExtension source) async {
    if (_updating) return;
    setState(() => _updating = true);
    final next = !_installed.contains(source.id);
    try {
      await _store.setInstalled(source.id, next);
      if (mounted) {
        setState(() {
          if (next) {
            _installed.add(source.id);
          } else {
            _installed.remove(source.id);
          }
        });
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(next ? 'MangaDex installed' : 'MangaDex removed'),
        ));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Could not save this manga source. Try again.'),
        ));
      }
    } finally {
      if (mounted) setState(() => _updating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Manga extensions')),
      body: ListView(
        key: const Key('manga-extensions-list'),
        padding: const EdgeInsets.all(18),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: colors.primaryContainer.withValues(alpha: 0.55),
              borderRadius: BorderRadius.circular(23),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.extension_rounded, size: 30,
                    color: colors.onPrimaryContainer),
                const SizedBox(height: 10),
                Text('Find your next manga',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    )),
                const SizedBox(height: 5),
                const Text(
                  'Install a reviewed source to search manga and read its '
                  'chapters online, right inside Selura.',
                ),
                const SizedBox(height: 8),
                Text(
                  'Online sources require internet. EPUB, PDF and local CBZ '
                  'reading remain offline.',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          Text('Available sources', style: theme.textTheme.titleLarge
              ?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 12),
          if (_loading)
            const Center(child: CircularProgressIndicator())
          else
            for (final source in MangaExtensionRegistry.available)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        Container(
                          width: 46,
                          height: 46,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(14),
                            color: colors.primaryContainer,
                          ),
                          child: Icon(Icons.auto_stories_rounded,
                              color: colors.onPrimaryContainer),
                        ),
                        const SizedBox(width: 13),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(source.name,
                                  style: theme.textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.w800)),
                              const Text('Reviewed source · English manga'),
                            ],
                          ),
                        ),
                      ]),
                      const SizedBox(height: 11),
                      Text(source.description),
                      const SizedBox(height: 5),
                      Text(
                        'MangaDex and scanlation groups retain credit for '
                        'their content. Content availability and guest '
                        'limits are controlled by MangaDex.',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colors.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 14),
                      Row(children: [
                        OutlinedButton(
                          key: const Key('manga-extension-toggle'),
                          onPressed: _updating ? null : () => _toggle(source),
                          child: Text(_installed.contains(source.id)
                              ? 'Remove' : 'Install'),
                        ),
                        const SizedBox(width: 10),
                        if (_installed.contains(source.id))
                          Expanded(
                            child: FilledButton.icon(
                              key: const Key('manga-extension-browse'),
                              onPressed: () => Navigator.push(
                                context,
                                MaterialPageRoute<void>(
                                  builder: (_) => MangaCatalogPage(
                                    client: widget.client ?? MangaDexClient(),
                                  ),
                                ),
                              ),
                              icon: const Icon(Icons.search_rounded, size: 18),
                              label: const Text('Browse manga'),
                            ),
                          ),
                      ]),
                    ],
                  ),
                ),
              ),
          const SizedBox(height: 16),
          Text(
            'These are Selura source adapters. Mihon/Tachiyomi APK '
            'extensions cannot be installed into Selura; no outside '
            'executable code is downloaded or run.',
            style: theme.textTheme.bodySmall?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class MangaCatalogPage extends StatefulWidget {
  const MangaCatalogPage({super.key, required this.client});
  final MangaDexClient client;

  @override
  State<MangaCatalogPage> createState() => _MangaCatalogPageState();
}

class _MangaCatalogPageState extends State<MangaCatalogPage> {
  final TextEditingController _search = TextEditingController();
  late Future<List<OnlineManga>> _results;

  @override
  void initState() {
    super.initState();
    _results = widget.client.browse();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _lookup() {
    setState(() => _results = widget.client.browse(query: _search.text));
    FocusScope.of(context).unfocus();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('MangaDex · Browse')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
          child: TextField(
            key: const Key('manga-catalog-search'),
            controller: _search,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _lookup(),
            decoration: InputDecoration(
              hintText: 'Search manga titles',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: IconButton(
                key: const Key('manga-catalog-submit'),
                tooltip: 'Search manga',
                icon: const Icon(Icons.arrow_forward_rounded),
                onPressed: _lookup,
              ),
              border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(18)),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 5),
          child: Text(
            'Powered by MangaDex · English chapters · Safe-rated titles',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
        ),
        Expanded(
          child: FutureBuilder<List<OnlineManga>>(
            future: _results,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return _OnlineError(
                  message: snapshot.error.toString(),
                  onRetry: _lookup,
                );
              }
              if (!snapshot.hasData) {
                return const Center(child: CircularProgressIndicator());
              }
              final items = snapshot.data!;
              if (items.isEmpty) {
                return const Center(child: Text(
                  'No manga found. Try a different title.',
                ));
              }
              return ListView.separated(
                key: const Key('manga-catalog-results'),
                padding: const EdgeInsets.all(14),
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (context, index) {
                  final manga = items[index];
                  return Card(
                    child: InkWell(
                      key: Key('manga-result-' + index.toString()),
                      borderRadius: BorderRadius.circular(20),
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute<void>(builder: (_) =>
                            MangaDetailPage(manga: manga, client: widget.client)),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(children: [
                          _MangaCover(uri: manga.coverUrl, width: 66,
                              height: 94),
                          const SizedBox(width: 14),
                          Expanded(child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(manga.title, maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: Theme.of(context).textTheme.titleMedium
                                      ?.copyWith(fontWeight: FontWeight.w700)),
                              const SizedBox(height: 6),
                              Text(
                                manga.description.isNotEmpty
                                    ? manga.description
                                    : 'English chapters from MangaDex',
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          )),
                          const Icon(Icons.chevron_right_rounded),
                        ]),
                      ),
                    ),
                  );
                },
              );
            },
          ),
        ),
      ]),
    );
  }
}

class MangaDetailPage extends StatefulWidget {
  const MangaDetailPage({
    super.key, required this.manga, required this.client,
  });
  final OnlineManga manga;
  final MangaDexClient client;

  @override
  State<MangaDetailPage> createState() => _MangaDetailPageState();
}

class _MangaDetailPageState extends State<MangaDetailPage> {
  late Future<List<OnlineMangaChapter>> _chapters;
  String? _resumeId;

  @override
  void initState() {
    super.initState();
    _chapters = widget.client.chapters(widget.manga.id);
    unawaited(_restoreResume());
  }

  Future<void> _restoreResume() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      setState(() => _resumeId = prefs.getString(
        'selura_mangadex_resume:' + widget.manga.id,
      ));
    }
  }

  void _refresh() {
    setState(() => _chapters = widget.client.chapters(widget.manga.id));
  }

  Future<void> _read(OnlineMangaChapter chapter) async {
    await Navigator.push(
      context,
      MaterialPageRoute<void>(builder: (_) => MangaOnlineReaderPage(
        client: widget.client, manga: widget.manga, chapter: chapter,
      )),
    );
    await _restoreResume();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(widget.manga.title,
        overflow: TextOverflow.ellipsis)),
    body: FutureBuilder<List<OnlineMangaChapter>>(
      future: _chapters,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return _OnlineError(
            message: snapshot.error.toString(),
            onRetry: _refresh,
          );
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final chapters = snapshot.data!;
        final resume = chapters.where((c) => c.id == _resumeId).toList();
        return ListView(
          padding: const EdgeInsets.all(18),
          children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _MangaCover(uri: widget.manga.coverUrl,
                  width: 108, height: 154),
              const SizedBox(width: 16),
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(widget.manga.title,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    )),
                  const SizedBox(height: 9),
                  const Text('MangaDex · English chapters'),
                  const SizedBox(height: 6),
                  const Text('Scanlation groups are credited on each chapter.'),
                ],
              )),
            ]),
            if (widget.manga.description.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(widget.manga.description, maxLines: 8,
                  overflow: TextOverflow.ellipsis),
            ],
            if (resume.isNotEmpty) ...[
              const SizedBox(height: 14),
              FilledButton.icon(
                key: const Key('manga-continue-online'),
                onPressed: () => _read(resume.first),
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('Continue reading'),
              ),
            ],
            const SizedBox(height: 24),
            Text('Available chapters (' + chapters.length.toString() + ')',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            if (chapters.isEmpty)
              const Padding(
                padding: EdgeInsets.all(18),
                child: Text('No readable English chapters found. '
                    'Availability is managed by MangaDex.'),
              ),
            for (final chapter in chapters)
              Card(
                child: ListTile(
                  key: Key('manga-chapter-' + chapter.id),
                  title: Text(chapter.label, maxLines: 2,
                      overflow: TextOverflow.ellipsis),
                  subtitle: Text('Scanlation: ' + chapter.group),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => _read(chapter),
                ),
              ),
            const SizedBox(height: 12),
            Text(
              'Manga and images from MangaDex. Credit to their original '
              'creators and the listed scanlation groups. '
              'Content availability and access limits are decided by MangaDex.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        );
      },
    ),
  );
}

class MangaOnlineReaderPage extends StatefulWidget {
  const MangaOnlineReaderPage({
    super.key, required this.client, required this.manga,
    required this.chapter,
  });
  final MangaDexClient client;
  final OnlineManga manga;
  final OnlineMangaChapter chapter;

  @override
  State<MangaOnlineReaderPage> createState() => _MangaOnlineReaderPageState();
}

class _MangaOnlineReaderPageState extends State<MangaOnlineReaderPage> {
  PageController? _pagesController;
  List<Uri>? _pages;
  String? _error;
  int _current = 1;
  bool _focus = false;

  @override
  void initState() {
    super.initState();
    unawaited(_open());
  }

  Future<void> _open() async {
    try {
      final urls = await widget.client.chapterPages(widget.chapter.id);
      final prefs = await SharedPreferences.getInstance();
      final initial = (prefs.getInt(
        'selura_mangadex_page:' + widget.chapter.id,
      ) ?? 1).clamp(1, urls.length).toInt();
      if (!mounted) return;
      setState(() {
        _pages = urls;
        _current = initial;
        _error = null;
        _pagesController = PageController(initialPage: initial - 1);
      });
      await _savePosition(initial);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    }
  }

  Future<void> _savePosition(int page) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      'selura_mangadex_resume:' + widget.manga.id,
      widget.chapter.id,
    );
    await prefs.setInt(
      'selura_mangadex_page:' + widget.chapter.id, page,
    );
  }

  void _changed(int index) {
    setState(() => _current = index + 1);
    unawaited(_savePosition(index + 1));
  }

  void _retry() {
    _pagesController?.dispose();
    setState(() {
      _pagesController = null;
      _pages = null;
      _error = null;
    });
    unawaited(_open());
  }

  @override
  void dispose() {
    _pagesController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pages = _pages;
    final controller = _pagesController;
    const bg = Color(0xFF17151D);
    const ink = Color(0xFFF4EFF9);
    return Scaffold(
      backgroundColor: bg,
      appBar: _focus ? null : AppBar(
        backgroundColor: bg,
        foregroundColor: ink,
        title: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.manga.title, maxLines: 1,
                overflow: TextOverflow.ellipsis),
            Text(widget.chapter.label,
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12)),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Enter manga focus mode',
            onPressed: () => setState(() => _focus = true),
            icon: const Icon(Icons.fullscreen_rounded),
          ),
        ],
      ),
      body: Stack(children: [
        Positioned.fill(
          child: _error != null
              ? _OnlineError(message: _error!, onRetry: _retry)
              : pages == null || controller == null
                  ? const Center(child: CircularProgressIndicator())
                  : PageView.builder(
                      key: const Key('manga-online-pages'),
                      controller: controller,
                      scrollDirection: Axis.vertical,
                      itemCount: pages.length,
                      onPageChanged: _changed,
                      itemBuilder: (context, index) {
                        final physicalWidth =
                          (MediaQuery.sizeOf(context).width *
                           MediaQuery.devicePixelRatioOf(context) * 2)
                            .ceil().clamp(1, 2200).toInt();
                        return InteractiveViewer(
                          minScale: 1,
                          maxScale: 4,
                          child: Center(
                            child: Image.network(
                              pages[index].toString(),
                              fit: BoxFit.contain,
                              cacheWidth: physicalWidth,
                              loadingBuilder: (ctx, child, loading) =>
                                  loading == null
                                  ? child
                                  : const Center(child:
                                      CircularProgressIndicator(strokeWidth: 2)),
                              errorBuilder: (_, __, ___) => const Center(
                                child: Padding(
                                  padding: EdgeInsets.all(28),
                                  child: Text(
                                    'This image could not be loaded. '
                                    'MangaDex may be limiting access or the '
                                    'image server may be unavailable.',
                                    style: TextStyle(color: ink),
                                    textAlign: TextAlign.center,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
        ),
        if (_focus)
          Positioned(
            right: 16, top: MediaQuery.paddingOf(context).top + 10,
            child: FilledButton.tonalIcon(
              onPressed: () => setState(() => _focus = false),
              icon: const Icon(Icons.fullscreen_exit),
              label: const Text('Show controls'),
            ),
          ),
      ]),
      bottomNavigationBar: _focus || pages == null ? null : SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 4, 8, 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('MangaDex · Scanlation: ' + widget.chapter.group,
                style: const TextStyle(color: ink, fontSize: 11),
                textAlign: TextAlign.center, maxLines: 2),
              Row(children: [
                IconButton(
                  tooltip: 'Previous page',
                  color: ink,
                  onPressed: _current <= 1 ? null :
                      () => controller?.jumpToPage(_current - 2),
                  icon: const Icon(Icons.chevron_left_rounded),
                ),
                Expanded(
                  child: Text('Page ' + _current.toString() +
                      ' of ' + pages.length.toString(),
                    style: const TextStyle(color: ink),
                    textAlign: TextAlign.center),
                ),
                IconButton(
                  tooltip: 'Next page',
                  color: ink,
                  onPressed: _current >= pages.length ? null :
                      () => controller?.jumpToPage(_current),
                  icon: const Icon(Icons.chevron_right_rounded),
                ),
              ]),
            ],
          ),
        ),
      ),
    );
  }
}

class _MangaCover extends StatelessWidget {
  const _MangaCover({
    required this.uri, required this.width, required this.height,
  });
  final Uri? uri;
  final double width;
  final double height;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: SizedBox(
        width: width, height: height,
        child: ColoredBox(
          color: colors.primaryContainer,
          child: uri == null
              ? Icon(Icons.auto_stories_rounded,
                  color: colors.onPrimaryContainer)
              : Image.network(
                  uri.toString(),
                  fit: BoxFit.cover,
                  cacheWidth: 380,
                  errorBuilder: (_, __, ___) => Icon(
                    Icons.auto_stories_rounded,
                    color: colors.onPrimaryContainer,
                  ),
                ),
        ),
      ),
    );
  }
}

class _OnlineError extends StatelessWidget {
  const _OnlineError({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded, size: 38),
          const SizedBox(height: 14),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('Try again'),
          ),
        ],
      ),
    ),
  );
}
