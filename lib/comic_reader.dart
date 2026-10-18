import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'bookmarks.dart';
import 'comic_archive.dart';
import 'reader_chrome.dart';
import 'reading_progress.dart';
import 'selura_ui.dart';

/// Offline CBZ manga reader; one image per swipe, vertically or horizontally.
/// EPUB/PDF readers and their controllers are completely independent.
class ComicReaderPage extends StatefulWidget {
  const ComicReaderPage({
    super.key,
    required this.bookPath,
    required this.bookTitle,
  });
  final String bookPath;
  final String bookTitle;

  @override
  State<ComicReaderPage> createState() => _ComicReaderPageState();
}

class _ComicReaderPageState extends State<ComicReaderPage> {
  final BookmarkStore _bookmarks = const BookmarkStore();
  ComicArchive? _archive;
  ComicPageCache? _cache;
  PageController? _controller;
  String? _error;
  int _page = 1;
  bool _vertical = true;
  bool _focus = false;

  static const background = Color(0xFF17151D);
  static const foreground = Color(0xFFF2EDF5);

  @override
  void initState() {
    super.initState();
    unawaited(_open());
  }

  Future<void> _open() async {
    try {
      final archive = await ComicArchive.open(widget.bookPath);
      final cache = await ComicPageCache.open(archive);
      final prefs = await SharedPreferences.getInstance();
      final initial = (prefs.getInt(
        ReadingProgressStore.comicPageKey(widget.bookPath),
      ) ?? 1).clamp(1, archive.pages.length).toInt();
      final axisVertical = prefs.getBool('selura_comic_vertical') ?? true;
      if (!mounted) return;
      setState(() {
        _archive = archive;
        _cache = cache;
        _page = initial;
        _vertical = axisVertical;
        _error = null;
        _controller = PageController(initialPage: initial - 1);
      });
      unawaited(cache.trimTo(initial - 1));
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'This CBZ could not be opened. Your original comic '
            'and saved progress have not been removed.';
      });
    }
  }

  Future<void> _retry() async {
    final old = _controller;
    if (!mounted) return;
    setState(() {
      _error = null;
      _archive = null;
      _cache = null;
      _controller = null;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      old?.dispose();
      if (mounted) unawaited(_open());
    });
  }

  Future<void> _savePage(int page) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(ReadingProgressStore.comicPageKey(widget.bookPath), page);
  }

  void _onPage(int index) {
    final page = index + 1;
    if (!mounted) return;
    setState(() => _page = page);
    unawaited(_savePage(page));
    final cache = _cache;
    if (cache != null) unawaited(cache.trimTo(index));
  }

  void _switchDirection() {
    final old = _controller;
    final nextVertical = !_vertical;
    setState(() {
      _vertical = nextVertical;
      _controller = PageController(initialPage: _page - 1);
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => old?.dispose());
    SharedPreferences.getInstance().then(
      (prefs) => prefs.setBool('selura_comic_vertical', nextVertical),
    );
  }

  void _message(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _addBookmark() async {
    try {
      final saved = await _bookmarks.add(
        bookPath: widget.bookPath,
        location: _page.toString(),
        label: 'Manga page ' + _page.toString(),
      );
      _message(saved ? 'Manga bookmark saved' : 'Already bookmarked here');
    } catch (_) {
      _message('Could not save manga bookmark');
    }
  }

  Future<void> _showBookmarks() async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => ReaderBookmarksSheet(
        bookPath: widget.bookPath,
        onGoToBookmark: (bookmark) {
          final index = int.tryParse(bookmark.location);
          if (index == null || index < 1 ||
              index > (_archive?.pages.length ?? 0)) {
            _message('Manga bookmark is no longer valid');
            return;
          }
          _controller?.jumpToPage(index - 1);
        },
      ),
    );
  }

  Future<void> _goToPage() async {
    final total = _archive?.pages.length;
    if (total == null) return;
    final input = TextEditingController(text: _page.toString());
    try {
      final selected = await showDialog<int>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Go to manga page'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Choose a page from 1 to ' + total.toString()),
              const SizedBox(height: 10),
              TextField(
                key: const Key('comic-page-input'),
                controller: input,
                autofocus: true,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(labelText: 'Page number'),
                onSubmitted: (_) {
                  final target = int.tryParse(input.text);
                  if (target != null && target >= 1 && target <= total) {
                    Navigator.pop(dialogContext, target);
                  }
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                final target = int.tryParse(input.text);
                if (target != null && target >= 1 && target <= total) {
                  Navigator.pop(dialogContext, target);
                }
              },
              child: const Text('Go'),
            ),
          ],
        ),
      );
      if (mounted && selected != null) {
        _controller?.jumpToPage(selected - 1);
      }
    } finally {
      input.dispose();
    }
  }

  @override
  void dispose() {
    // A damaged CBZ must not overwrite a previously saved valid location.
    if (_archive != null) unawaited(_savePage(_page));
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final archive = _archive;
    final cache = _cache;
    final controller = _controller;
    return ReaderFrame(
      focusMode: _focus,
      onExitFocus: () => setState(() => _focus = false),
      backgroundColor: background,
      foregroundColor: foreground,
      appBar: AppBar(
        backgroundColor: background,
        foregroundColor: foreground,
        title: Text(
          widget.bookTitle,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        actions: [
          IconButton(
            key: const Key('comic-direction'),
            tooltip: _vertical ? 'Switch to horizontal paging'
                : 'Switch to vertical paging',
            onPressed: controller == null ? null : _switchDirection,
            icon: Icon(_vertical
                ? Icons.swap_horiz_rounded : Icons.swap_vert_rounded),
          ),
          IconButton(
            tooltip: 'Add manga bookmark',
            onPressed: controller == null ? null : _addBookmark,
            icon: const Icon(Icons.bookmark_add_outlined),
          ),
          IconButton(
            tooltip: 'Manga bookmarks',
            onPressed: controller == null ? null : _showBookmarks,
            icon: const Icon(Icons.bookmarks_outlined),
          ),
          IconButton(
            tooltip: 'Enter manga focus mode',
            onPressed: () => setState(() => _focus = true),
            icon: const Icon(Icons.fullscreen_rounded),
          ),
        ],
      ),
      bottomBar: archive == null ? null : ReaderChromeFooter(
        category: _vertical ? 'MANGA · VERTICAL' : 'MANGA · HORIZONTAL',
        label: 'Page ' + _page.toString() + ' of ' +
            archive.pages.length.toString(),
        leadingIcon: Icons.auto_stories_rounded,
        backgroundColor: background,
        foregroundColor: foreground,
        progressFraction: _page / archive.pages.length,
        trailing: IconButton(
          tooltip: 'Go to manga page',
          onPressed: _goToPage,
          icon: const Icon(Icons.pin_drop_outlined),
          color: foreground,
        ),
      ),
      body: _error != null
          ? SeluraLoadError(
              title: 'Unable to open manga',
              message: _error!,
              onRetry: _retry,
            )
          : archive == null || cache == null || controller == null
              ? const SeluraLoadingView(
                  title: 'Opening your manga',
                  subtitle: 'Sorting comic pages and restoring your place',
                )
              : PageView.builder(
                  key: ValueKey(_vertical),
                  controller: controller,
                  scrollDirection: _vertical ? Axis.vertical : Axis.horizontal,
                  itemCount: archive.pages.length,
                  onPageChanged: _onPage,
                  itemBuilder: (context, index) => _ComicImagePage(
                    key: ValueKey(index),
                    cache: cache,
                    index: index,
                  ),
                ),
    );
  }
}

class _ComicImagePage extends StatefulWidget {
  const _ComicImagePage({
    super.key,
    required this.cache,
    required this.index,
  });
  final ComicPageCache cache;
  final int index;

  @override
  State<_ComicImagePage> createState() => _ComicImagePageState();
}

class _ComicImagePageState extends State<_ComicImagePage> {
  late Future<File> _image;

  @override
  void initState() {
    super.initState();
    _image = widget.cache.page(widget.index);
  }

  @override
  void didUpdateWidget(covariant _ComicImagePage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.index != widget.index || oldWidget.cache != widget.cache) {
      _image = widget.cache.page(widget.index);
    }
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<File>(
    future: _image,
    builder: (context, snapshot) {
      if (snapshot.hasError) {
        return Center(
          child: Text(
            'Could not display this manga page',
            style: const TextStyle(color: Colors.white70),
          ),
        );
      }
      if (!snapshot.hasData) {
        return const Center(
          child: CircularProgressIndicator(strokeWidth: 2),
        );
      }
      final pixelWidth = (MediaQuery.sizeOf(context).width *
              MediaQuery.devicePixelRatioOf(context))
          .ceil().clamp(1, 2200).toInt();
      return InteractiveViewer(
        minScale: 1,
        maxScale: 4,
        child: Center(
          child: Image.file(
            snapshot.data!,
            fit: BoxFit.contain,
            cacheWidth: pixelWidth,
            filterQuality: FilterQuality.medium,
            errorBuilder: (_, __, ___) => const Center(
              child: Text(
                'Unable to decode this image',
                style: TextStyle(color: Colors.white70),
              ),
            ),
          ),
        ),
      );
    },
  );
}
