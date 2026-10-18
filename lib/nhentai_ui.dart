import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'nhentai_source.dart';

/// Separate opt-in 18+ gallery browsing. No thumbnails appear in this
/// catalogue because age-restricted galleries need metadata validation first.
class NhentaiBrowserPage extends StatefulWidget {
  const NhentaiBrowserPage({super.key, this.client});
  final NhentaiSourceClient? client;

  @override
  State<NhentaiBrowserPage> createState() => _NhentaiBrowserPageState();
}

class _NhentaiBrowserPageState extends State<NhentaiBrowserPage> {
  final TextEditingController _search = TextEditingController();
  late final NhentaiSourceClient _client =
      widget.client ?? NhentaiSourceClient();
  late Future<List<NhentaiPreview>> _results;
  int _page = 1;

  @override
  void initState() {
    super.initState();
    _results = _client.browse();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _browse([int page = 1]) {
    setState(() {
      _page = page;
      _results = _client.browse(query: _search.text, page: page);
    });
    FocusManager.instance.primaryFocus?.unfocus();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('nHentai · Galleries')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
          child: TextField(
            key: const Key('nhentai-search'),
            controller: _search,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _browse(),
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search_rounded),
              hintText: 'Search gallery titles',
              suffixIcon: IconButton(
                key: const Key('nhentai-submit'),
                tooltip: 'Search galleries',
                icon: const Icon(Icons.arrow_forward_rounded),
                onPressed: () => _browse(),
              ),
              border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(18)),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
          child: Text(
            '18+ source · nHentai gallery volumes, not chapter feeds. '
            'Thumbnails are hidden in search results.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
        ),
        Expanded(
          child: FutureBuilder<List<NhentaiPreview>>(
            future: _results,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return _GalleryProblem(
                  message: snapshot.error.toString(),
                  onRetry: () => _browse(_page),
                );
              }
              if (!snapshot.hasData) {
                return const Center(child: CircularProgressIndicator());
              }
              final items = snapshot.data!;
              if (items.isEmpty) {
                return const Center(
                  child: Text(
                    'No supported galleries found. Try another search.',
                    textAlign: TextAlign.center,
                  ),
                );
              }
              return Column(children: [
                Expanded(
                  child: ListView.separated(
                    key: const Key('nhentai-results'),
                    padding: const EdgeInsets.all(14),
                    itemCount: items.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final gallery = items[index];
                      return Card(
                        child: ListTile(
                          key: Key('nhentai-result-' + index.toString()),
                          leading: const Icon(Icons.collections_bookmark_outlined),
                          title: Text(
                            gallery.title, maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(
                            gallery.pageCount.toString() +
                                ' pages · Gallery #' + gallery.id.toString(),
                          ),
                          trailing: const Icon(Icons.chevron_right_rounded),
                          onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute<void>(
                              builder: (_) => NhentaiGalleryReaderPage(
                                galleryId: gallery.id, client: _client,
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                SafeArea(
                  top: false,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 5,
                    ),
                    child: Row(children: [
                      OutlinedButton(
                        onPressed: _page <= 1 ? null :
                            () => _browse(_page - 1),
                        child: const Text('Previous'),
                      ),
                      Expanded(
                        child: Text(
                          'Results page ' + _page.toString(),
                          textAlign: TextAlign.center,
                        ),
                      ),
                      OutlinedButton(
                        onPressed: items.length < 20 || _page >= 30
                            ? null : () => _browse(_page + 1),
                        child: const Text('Next'),
                      ),
                    ]),
                  ),
                ),
              ]);
            },
          ),
        ),
      ]),
    );
  }
}

class NhentaiGalleryReaderPage extends StatefulWidget {
  const NhentaiGalleryReaderPage({
    super.key,
    required this.galleryId,
    required this.client,
  });
  final int galleryId;
  final NhentaiSourceClient client;

  @override
  State<NhentaiGalleryReaderPage> createState() =>
      _NhentaiGalleryReaderPageState();
}

class _NhentaiGalleryReaderPageState
    extends State<NhentaiGalleryReaderPage> {
  NhentaiGallery? _gallery;
  PageController? _controller;
  String? _error;
  int _current = 1;
  bool _focus = false;

  String get _progressKey =>
      'selura_nhentai_gallery_page:' + widget.galleryId.toString();

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  Future<void> _load() async {
    try {
      final gallery = await widget.client.gallery(widget.galleryId);
      final prefs = await SharedPreferences.getInstance();
      final saved = (prefs.getInt(_progressKey) ?? 1)
          .clamp(1, gallery.pages.length).toInt();
      if (!mounted) return;
      setState(() {
        _gallery = gallery;
        _current = saved;
        _controller = PageController(initialPage: saved - 1);
        _error = null;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  void _retry() {
    final old = _controller;
    setState(() {
      _gallery = null;
      _controller = null;
      _error = null;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      old?.dispose();
      if (mounted) unawaited(_load());
    });
  }

  void _changed(int index) {
    setState(() => _current = index + 1);
    SharedPreferences.getInstance().then(
      (prefs) => prefs.setInt(_progressKey, index + 1),
    );
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const bg = Color(0xFF17151D);
    const text = Color(0xFFF5EDF7);
    final gallery = _gallery;
    final controller = _controller;

    return Scaffold(
      backgroundColor: bg,
      appBar: _focus ? null : AppBar(
        backgroundColor: bg,
        foregroundColor: text,
        title: Text(
          gallery?.title ?? 'Gallery ' + widget.galleryId.toString(),
          maxLines: 1, overflow: TextOverflow.ellipsis,
        ),
        actions: [
          IconButton(
            tooltip: 'Enter gallery focus mode',
            icon: const Icon(Icons.fullscreen_rounded),
            onPressed: gallery == null ? null :
                () => setState(() => _focus = true),
          ),
        ],
      ),
      body: Stack(children: [
        Positioned.fill(
          child: _error != null
              ? _GalleryProblem(message: _error!, onRetry: _retry)
              : gallery == null || controller == null
                  ? const Center(child: CircularProgressIndicator())
                  : PageView.builder(
                      key: const Key('nhentai-gallery-pages'),
                      controller: controller,
                      itemCount: gallery.pages.length,
                      scrollDirection: Axis.vertical,
                      onPageChanged: _changed,
                      itemBuilder: (context, index) {
                        final pixelWidth = (MediaQuery.sizeOf(context).width *
                            MediaQuery.devicePixelRatioOf(context) * 2)
                            .ceil().clamp(1, 2200).toInt();
                        return InteractiveViewer(
                          minScale: 1,
                          maxScale: 4,
                          child: Center(
                            child: Image.network(
                              gallery.pages[index].toString(),
                              fit: BoxFit.contain,
                              cacheWidth: pixelWidth,
                              errorBuilder: (_, __, ___) => const Padding(
                                padding: EdgeInsets.all(24),
                                child: Center(
                                  child: Text(
                                    'Image unavailable. The source may '
                                    'require verification or be rate-limiting '
                                    'this connection.',
                                    style: TextStyle(color: text),
                                    textAlign: TextAlign.center,
                                  ),
                                ),
                              ),
                              loadingBuilder: (_, child, loading) =>
                                  loading == null ? child
                                  : const Center(
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
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
            right: 16, top: MediaQuery.paddingOf(context).top + 8,
            child: FilledButton.tonalIcon(
              onPressed: () => setState(() => _focus = false),
              icon: const Icon(Icons.fullscreen_exit_rounded),
              label: const Text('Show controls'),
            ),
          ),
      ]),
      bottomNavigationBar: _focus || gallery == null ? null : SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 4, 8, 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                gallery.credit,
                style: const TextStyle(color: text, fontSize: 10),
                textAlign: TextAlign.center,
                maxLines: 2,
              ),
              Row(children: [
                IconButton(
                  color: text,
                  tooltip: 'Previous gallery page',
                  onPressed: _current == 1 ? null :
                      () => controller?.jumpToPage(_current - 2),
                  icon: const Icon(Icons.chevron_left_rounded),
                ),
                Expanded(
                  child: Text(
                    'Page ' + _current.toString() + ' of ' +
                        gallery.pages.length.toString(),
                    style: const TextStyle(color: text),
                    textAlign: TextAlign.center,
                  ),
                ),
                IconButton(
                  color: text,
                  tooltip: 'Next gallery page',
                  onPressed: _current >= gallery.pages.length ? null :
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

class _GalleryProblem extends StatelessWidget {
  const _GalleryProblem({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.info_outline_rounded, size: 38),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('Retry'),
          ),
        ],
      ),
    ),
  );
}
