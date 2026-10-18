import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:epub_view/epub_view.dart' hide Image;
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdfx/pdfx.dart' hide DefaultBuilderOptions;
import 'package:pdfx/pdfx.dart' as pdfx;
import 'package:shared_preferences/shared_preferences.dart';

import 'bookmarks.dart';
import 'cover_cache.dart';
import 'reader_settings.dart';
import 'reading_progress.dart';
import 'epub_narration.dart';
import 'epub_narration_sheet.dart';
import 'selura_ui.dart';

void main() => runApp(const SeluraApp());

ThemeData _seluraTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final colors = ColorScheme.fromSeed(
    seedColor: dark ? const Color(0xFFB9A5ED) : const Color(0xFF8066B8),
    brightness: brightness,
  );
  return ThemeData(
    colorScheme: colors,
    useMaterial3: true,
    scaffoldBackgroundColor:
        dark ? const Color(0xFF14121D) : const Color(0xFFFCFAFF),
    appBarTheme: AppBarTheme(
      elevation: 0,
      backgroundColor:
          dark ? const Color(0xFF14121D) : const Color(0xFFFCFAFF),
      surfaceTintColor: Colors.transparent,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: colors.surfaceContainerLow,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
        side: BorderSide(
          color: colors.outlineVariant.withValues(alpha: 0.35),
        ),
      ),
    ),
    snackBarTheme: const SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(15),
        ),
      ),
    ),
  );
}

class SeluraApp extends StatelessWidget {
  const SeluraApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Selura',
        debugShowCheckedModeBanner: false,
        theme: _seluraTheme(Brightness.light),
        darkTheme: _seluraTheme(Brightness.dark),
        themeMode: ThemeMode.system,
        home: const LibraryPage(),
      );
}

class Book {
  final String path;
  final String title;
  final String type;
  final bool favorite;
  final int lastOpened;

  const Book(
    this.path,
    this.title,
    this.type, {
    this.favorite = false,
    this.lastOpened = 0,
  });

  Book copyWith({
    bool? favorite,
    int? lastOpened,
  }) =>
      Book(
        path,
        title,
        type,
        favorite: favorite ?? this.favorite,
        lastOpened: lastOpened ?? this.lastOpened,
      );

  Map<String, dynamic> toJson() => {
        'path': path,
        'title': title,
        'type': type,
        'favorite': favorite,
        'lastOpened': lastOpened,
      };

  factory Book.fromJson(Map<String, dynamic> json) => Book(
        json['path'] as String,
        json['title'] as String,
        json['type'] as String,
        favorite: json['favorite'] as bool? ?? false,
        lastOpened: json['lastOpened'] as int? ?? 0,
      );
}

String _epubProgressKey(Book book) => 'reading_epub_cfi:${book.path}';
String _pdfProgressKey(Book book) => 'reading_pdf_page:${book.path}';

enum _LibrarySort { recent, title, favorites, format }

class LibraryPage extends StatefulWidget {
  const LibraryPage({super.key});

  @override
  State<LibraryPage> createState() => _LibraryPageState();
}

class _LibraryPageState extends State<LibraryPage> {
  List<Book> books = [];
  final Map<String, ReadingProgressSummary> progressLabels = {};
  final Map<String, String> coverPaths = {};
  final EpubCoverCache coverCache = EpubCoverCache();
  final TextEditingController searchController = TextEditingController();
  bool busy = false;
  bool loadingLibrary = true;
  String? libraryLoadError;
  bool gridView = true;
  String query = '';
  _LibrarySort sort = _LibrarySort.recent;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      loadingLibrary = true;
      libraryLoadError = null;
    });
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getStringList('books') ?? [];
      // A broken entry should not prevent other books from appearing.
      final loadedBooks = <Book>[];
      for (final entry in raw) {
        try {
          final book = Book.fromJson(
            jsonDecode(entry) as Map<String, dynamic>,
          );
          if (await File(book.path).exists()) loadedBooks.add(book);
        } catch (_) {
          // Ignore only the malformed entry, not the whole local library.
        }
      }
      final savedSort = prefs.getInt('library_sort') ?? 0;
      final sortIndex = savedSort.clamp(
        0,
        _LibrarySort.values.length - 1,
      ).toInt();
      if (!mounted) return;
      setState(() {
        books = loadedBooks;
        gridView = prefs.getBool('library_grid') ?? true;
        sort = _LibrarySort.values[sortIndex];
      });
      await _refreshProgress();
      // Covers resolve asynchronously and are cached for future launches.
      unawaited(_warmCovers(loadedBooks));
    } catch (_) {
      if (mounted) {
        setState(() => libraryLoadError =
            'Selura could not open its local library. Your book files '
            'have not been deleted.');
      }
    } finally {
      if (mounted) setState(() => loadingLibrary = false);
    }
  }

  Future<void> _warmCovers(Iterable<Book> requestedBooks) async {
    final candidates = requestedBooks
        .where(
          (book) => book.type == 'epub' &&
              !coverPaths.containsKey(book.path),
        )
        .toList();
    var next = 0;

    Future<void> worker() async {
      while (mounted && next < candidates.length) {
        // At most three background extraction jobs run concurrently.
        final book = candidates[next++];
        final cachedPath = await coverCache.load(book.path);
        if (!mounted) return;
        if (cachedPath != null &&
            coverPaths[book.path] != cachedPath) {
          setState(() => coverPaths[book.path] = cachedPath);
        }
      }
    }

    final count = candidates.length < 3 ? candidates.length : 3;
    await Future.wait(List.generate(count, (_) => worker()));
  }

  Future<void> _saveBooks() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(
      'books',
      books.map((book) => jsonEncode(book.toJson())).toList(),
    );
  }

  Future<void> _refreshProgress() async {
    final prefs = await SharedPreferences.getInstance();
    const store = ReadingProgressStore();
    final next = <String, ReadingProgressSummary>{};
    for (final book in books) {
      next[book.path] = store.read(
        prefs,
        path: book.path,
        type: book.type,
      );
    }
    if (!mounted) return;
    setState(() {
      progressLabels
        ..clear()
        ..addAll(next);
    });
  }

  Future<void> _import() async {
    setState(() => busy = true);
    try {
      final files = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['epub', 'pdf'],
      );
      if (files.isEmpty) return;

      final dir = await getApplicationDocumentsDirectory();
      final imported = <Book>[];
      for (final file in files) {
        if (file.path == null) continue;
        final extension = file.extension?.toLowerCase() ?? '';
        if (extension != 'epub' && extension != 'pdf') continue;

        final dest =
            '${dir.path}/${DateTime.now().microsecondsSinceEpoch}_${books.length}.$extension';
        await File(file.path!).copy(dest);
        final newBook = Book(
          dest,
          file.name.replaceFirst(
            RegExp(r'\.(epub|pdf)$', caseSensitive: false),
            '',
          ),
          extension,
        );
        books.add(newBook);
        imported.add(newBook);
      }

      await _saveBooks();
      await _refreshProgress();
      if (mounted) setState(() {});
      // Rendering the bookshelf never waits for EPUB image decoding.
      unawaited(_warmCovers(imported));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Could not import this book.'),
            action: SnackBarAction(
              label: 'Details',
              onPressed: () {
                if (!mounted) return;
                showDialog<void>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text('Import details'),
                    content: SizedBox(
                      width: double.maxFinite,
                      child: SingleChildScrollView(
                        child: SelectableText(e.toString()),
                      ),
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Close'),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _toggleFavorite(Book book) async {
    final index = books.indexWhere((item) => item.path == book.path);
    if (index < 0) return;
    setState(() {
      books[index] = book.copyWith(favorite: !book.favorite);
    });
    await _saveBooks();
  }

  Future<void> _openBook(Book book) async {
    final index = books.indexWhere((item) => item.path == book.path);
    if (index >= 0) {
      final updated = book.copyWith(
        lastOpened: DateTime.now().millisecondsSinceEpoch,
      );
      setState(() => books[index] = updated);
      await _saveBooks();
      book = updated;
    }

    if (!mounted) return;
    await Navigator.push(
      context,
      PageRouteBuilder<void>(
        transitionDuration: const Duration(milliseconds: 260),
        reverseTransitionDuration: const Duration(milliseconds: 190),
        pageBuilder: (_, __, ___) => book.type == 'pdf'
            ? PdfBookPage(book: book)
            : EpubBookPage(book: book),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          final fade = CurvedAnimation(
            parent: animation,
            curve: Curves.easeOutCubic,
          );
          return FadeTransition(
            opacity: fade,
            child: SlideTransition(
              position: Tween<Offset>(
                begin: const Offset(0, 0.025),
                end: Offset.zero,
              ).animate(fade),
              child: child,
            ),
          );
        },
      ),
    );
    await _refreshProgress();
  }

  Future<void> _toggleView() async {
    final next = !gridView;
    setState(() => gridView = next);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('library_grid', next);
  }

  Future<void> _setSort(_LibrarySort value) async {
    setState(() => sort = value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('library_sort', value.index);
  }

  void _clearSearch() {
    searchController.clear();
    setState(() => query = '');
  }

  List<Book> get _visibleBooks {
    final normalized = query.trim().toLowerCase();
    final result = books
        .where(
          (book) => normalized.isEmpty ||
              book.title.toLowerCase().contains(normalized) ||
              book.type.toLowerCase().contains(normalized),
        )
        .toList();

    switch (sort) {
      case _LibrarySort.recent:
        result.sort((a, b) {
          final recent = b.lastOpened.compareTo(a.lastOpened);
          return recent == 0
              ? a.title.toLowerCase().compareTo(b.title.toLowerCase())
              : recent;
        });
        break;
      case _LibrarySort.title:
        result.sort(
          (a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()),
        );
        break;
      case _LibrarySort.favorites:
        result.sort((a, b) {
          if (a.favorite != b.favorite) return a.favorite ? -1 : 1;
          return a.title.toLowerCase().compareTo(b.title.toLowerCase());
        });
        break;
      case _LibrarySort.format:
        result.sort((a, b) {
          final format = a.type.compareTo(b.type);
          return format == 0
              ? a.title.toLowerCase().compareTo(b.title.toLowerCase())
              : format;
        });
        break;
    }
    return result;
  }

  List<Book> get _continueReading {
    final result = books.where((book) => book.lastOpened > 0).toList()
      ..sort((a, b) => b.lastOpened.compareTo(a.lastOpened));
    return result.take(5).toList();
  }

  String _sortLabel(_LibrarySort value) => switch (value) {
        _LibrarySort.recent => 'Recent',
        _LibrarySort.title => 'Title',
        _LibrarySort.favorites => 'Favorites',
        _LibrarySort.format => 'Format',
      };

  String _relativeOpened(Book book) {
    if (book.lastOpened <= 0) return 'Not opened yet';
    final difference = DateTime.now().difference(
      DateTime.fromMillisecondsSinceEpoch(book.lastOpened),
    );
    if (difference.inMinutes < 1) return 'Opened just now';
    if (difference.inHours < 1) return 'Opened ${difference.inMinutes}m ago';
    if (difference.inDays < 1) return 'Opened ${difference.inHours}h ago';
    if (difference.inDays < 7) return 'Opened ${difference.inDays}d ago';
    return 'Opened recently';
  }

  @override
  Widget build(BuildContext context) {
    final visibleBooks = _visibleBooks;
    final continueReading = _continueReading;

    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'SELURA',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 2.4,
              ),
            ),
            Text('My Library'),
          ],
        ),
        actions: [
          PopupMenuButton<_LibrarySort>(
            tooltip: 'Sort library',
            initialValue: sort,
            onSelected: _setSort,
            icon: const Icon(Icons.sort_rounded),
            itemBuilder: (context) => _LibrarySort.values
                .map(
                  (value) => PopupMenuItem(
                    value: value,
                    child: Row(
                      children: [
                        if (value == sort) ...[
                          const Icon(Icons.check_rounded, size: 18),
                          const SizedBox(width: 8),
                        ],
                        Text(_sortLabel(value)),
                      ],
                    ),
                  ),
                )
                .toList(),
          ),
          IconButton(
            tooltip: gridView ? 'List view' : 'Grid view',
            onPressed: _toggleView,
            icon: Icon(
              gridView ? Icons.view_list_rounded : Icons.grid_view_rounded,
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: loadingLibrary
                ? const SeluraLoadingView(
                    title: 'Preparing your library',
                    subtitle: 'Your stories stay private and offline',
                  )
                : libraryLoadError != null
                    ? SeluraLoadError(
                        title: 'Library unavailable',
                        message: libraryLoadError!,
                        onRetry: _load,
                      )
                    : books.isEmpty
                        ? _EmptyLibrary(onImport: busy ? null : _import)
                        : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
              children: [
                SeluraLibraryBanner(
                  bookCount: books.length,
                  onImport: busy ? null : _import,
                ),
                const SizedBox(height: 24),
                TextField(
                  controller: searchController,
                  onChanged: (value) => setState(() => query = value),
                  decoration: InputDecoration(
                    hintText: 'Search your library',
                    prefixIcon: const Icon(Icons.search_rounded),
                    suffixIcon: query.isEmpty
                        ? null
                        : IconButton(
                            tooltip: 'Clear search',
                            onPressed: _clearSearch,
                            icon: const Icon(Icons.close_rounded),
                          ),
                    filled: true,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(18),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
                if (continueReading.isNotEmpty) ...[
                  const SizedBox(height: 28),
                  Text(
                    'Continue reading',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 158,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: continueReading.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 12),
                      itemBuilder: (context, index) {
                        final book = continueReading[index];
                        return _ContinueCard(
                          book: book,
                          coverPath: coverPaths[book.path],
                          progress: progressLabels[book.path] ?? ReadingProgressSummary.notStarted,
                          onTap: () => _openBook(book),
                        );
                      },
                    ),
                  ),
                ],
                const SizedBox(height: 28),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Library',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                    ),
                    Text(
                      '${visibleBooks.length} ${visibleBooks.length == 1 ? 'book' : 'books'}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (visibleBooks.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 56),
                    child: Center(child: Text('No books match your search.')),
                  )
                else if (gridView)
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: visibleBooks.length,
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount:
                          MediaQuery.sizeOf(context).width >= 700 ? 4 : 2,
                      crossAxisSpacing: 14,
                      mainAxisSpacing: 18,
                      childAspectRatio: 0.63,
                    ),
                    itemBuilder: (context, index) {
                      final book = visibleBooks[index];
                      return _GridBookCard(
                        book: book,
                        coverPath: coverPaths[book.path],
                        progress: progressLabels[book.path] ?? ReadingProgressSummary.notStarted,
                        onTap: () => _openBook(book),
                        onFavorite: () => _toggleFavorite(book),
                      );
                    },
                  )
                else
                  ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: visibleBooks.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final book = visibleBooks[index];
                      return _ListBookCard(
                        book: book,
                        coverPath: coverPaths[book.path],
                        progress: progressLabels[book.path] ?? ReadingProgressSummary.notStarted,
                        opened: _relativeOpened(book),
                        onTap: () => _openBook(book),
                        onFavorite: () => _toggleFavorite(book),
                      );
                    },
                  ),
              ],
            ),
          ),
          if (busy)
            Positioned.fill(
              child: ColoredBox(
                color: Theme.of(context)
                    .colorScheme
                    .surface
                    .withValues(alpha: 0.94),
                child: const SeluraLoadingView(
                  key: Key('selura-import-loading'),
                  title: 'Adding your book',
                  subtitle: 'Copying your file into your offline library',
                  compact: true,
                ),
              ),
            ),
        ],
      ),
      floatingActionButton: loadingLibrary || libraryLoadError != null ||
              books.isEmpty
          ? null
          : FloatingActionButton.extended(
              onPressed: busy ? null : _import,
              icon: busy
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.add_rounded),
              label: const Text('Import'),
            ),
    );
  }
}

class _EmptyLibrary extends StatelessWidget {
  final VoidCallback? onImport;

  const _EmptyLibrary({required this.onImport});

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 104,
                height: 104,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Icon(
                  Icons.auto_stories_rounded,
                  size: 52,
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Build your Selura library',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 10),
              Text(
                'Import EPUB and PDF books for private, offline reading.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: onImport,
                icon: const Icon(Icons.upload_file_rounded),
                label: const Text('Import EPUB or PDF'),
              ),
            ],
          ),
        ),
      );
}

class _BookCover extends StatelessWidget {
  final Book book;
  final String? coverPath;
  final double? width;
  final double? height;
  final BorderRadius borderRadius;

  const _BookCover({
    required this.book,
    this.coverPath,
    this.width,
    this.height,
    this.borderRadius = const BorderRadius.all(Radius.circular(18)),
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        borderRadius: borderRadius,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            scheme.primaryContainer,
            scheme.secondaryContainer,
          ],
        ),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (coverPath != null)
            ClipRRect(
              borderRadius: borderRadius,
              child: Image.file(
                File(coverPath!),
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => Center(
                  child: Icon(
                    Icons.auto_stories_rounded,
                    size: 46,
                    color: scheme.onPrimaryContainer,
                  ),
                ),
              ),
            )
          else
            Center(
              child: Icon(
                book.type == 'pdf'
                    ? Icons.picture_as_pdf_rounded
                    : Icons.auto_stories_rounded,
                size: 46,
                color: scheme.onPrimaryContainer,
              ),
            ),
          Positioned(
            left: 10,
            bottom: 10,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: scheme.surface.withValues(alpha: 0.86),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                book.type.toUpperCase(),
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.8,
                    ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BookProgressIndicator extends StatelessWidget {
  const _BookProgressIndicator({required this.progress});

  final ReadingProgressSummary progress;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            progress.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (progress.pageFraction != null) ...[
            const SizedBox(height: 5),
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: LinearProgressIndicator(
                value: progress.pageFraction,
                minHeight: 4,
                backgroundColor: Theme.of(context)
                    .colorScheme
                    .surfaceContainerHighest,
              ),
            ),
          ],
        ],
      );
}

class _ContinueCard extends StatelessWidget {
  final Book book;
  final String? coverPath;
  final ReadingProgressSummary progress;
  final VoidCallback onTap;

  const _ContinueCard({
    required this.book,
    this.coverPath,
    required this.progress,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 290,
        child: Card(
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  _BookCover(
                    book: book,
                    coverPath: coverPath,
                    width: 82,
                    height: 128,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          book.title,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.w700,
                              ),
                        ),
                        const SizedBox(height: 8),
                        _BookProgressIndicator(progress: progress),
                        const Spacer(),
                        Row(
                          children: [
                            Icon(
                              Icons.play_circle_fill_rounded,
                              color: Theme.of(context).colorScheme.primary,
                            ),
                            const SizedBox(width: 6),
                            const Text('Continue'),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class _GridBookCard extends StatelessWidget {
  final Book book;
  final String? coverPath;
  final ReadingProgressSummary progress;
  final VoidCallback onTap;
  final VoidCallback onFavorite;

  const _GridBookCard({
    required this.book,
    this.coverPath,
    required this.progress,
    required this.onTap,
    required this.onFavorite,
  });

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  _BookCover(book: book, coverPath: coverPath),
                  Positioned(
                    top: 6,
                    right: 6,
                    child: IconButton.filledTonal(
                      tooltip: book.favorite
                          ? 'Remove from favorites'
                          : 'Add to favorites',
                      onPressed: onFavorite,
                      icon: Icon(
                        book.favorite
                            ? Icons.favorite_rounded
                            : Icons.favorite_border_rounded,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            Text(
              book.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 3),
            _BookProgressIndicator(progress: progress),
          ],
        ),
      );
}

class _ListBookCard extends StatelessWidget {
  final Book book;
  final String? coverPath;
  final ReadingProgressSummary progress;
  final String opened;
  final VoidCallback onTap;
  final VoidCallback onFavorite;

  const _ListBookCard({
    required this.book,
    this.coverPath,
    required this.progress,
    required this.opened,
    required this.onTap,
    required this.onFavorite,
  });

  @override
  Widget build(BuildContext context) => Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Row(
              children: [
                _BookCover(
                  book: book,
                  coverPath: coverPath,
                  width: 68,
                  height: 102,
                  borderRadius: BorderRadius.circular(12),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        book.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                      const SizedBox(height: 7),
                      Text(book.type.toUpperCase()),
                      const SizedBox(height: 4),
                      _BookProgressIndicator(progress: progress),
                      const SizedBox(height: 3),
                      Text(
                        opened,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: book.favorite
                      ? 'Remove from favorites'
                      : 'Add to favorites',
                  onPressed: onFavorite,
                  icon: Icon(
                    book.favorite
                        ? Icons.favorite_rounded
                        : Icons.favorite_border_rounded,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class EpubBookPage extends StatefulWidget {
  final Book book;

  const EpubBookPage({super.key, required this.book});

  @override
  State<EpubBookPage> createState() => _EpubBookPageState();
}

class _EpubBookPageState extends State<EpubBookPage> {
  EpubController? controller;
  EpubChapter? _currentSpeechChapter;
  final EpubNarrationController _narration = EpubNarrationController();
  String? _openingError;
  final BookmarkStore _bookmarkStore = const BookmarkStore();

  Future<void> _showNarration() async {
    final chapter = _currentSpeechChapter;
    if (chapter == null) {
      _bookmarkMessage('Wait for the chapter to load before listening.');
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => EpubNarrationSheet(
        narration: _narration,
        chapterHtml: chapter.HtmlContent,
        chapterTitle: chapter.Title,
      ),
    );
  }

  Future<void> _retryOpening() async {
    final oldController = controller;
    if (!mounted) return;
    setState(() {
      controller = null;
      _openingError = null;
    });
    // Detach the old document view before disposing its controller.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      oldController?.dispose();
      if (mounted) unawaited(_restoreProgress());
    });
  }

  final ReadingProgressStore _progressStore = const ReadingProgressStore();
  String? _chapterStatus;
  int? _lastChapterNumber;
  String? _lastChapterTitle;
  Future<void> _chapterWriteQueue = Future<void>.value();

  void _onReadingChapterChanged(int? chapterNumber, String? chapterTitle) {
    if (chapterNumber == null || chapterNumber < 1) return;
    final title = ReadingProgressSummary.normalizedChapterTitle(chapterTitle);
    if (_lastChapterNumber == chapterNumber && _lastChapterTitle == title) {
      return;
    }
    _lastChapterNumber = chapterNumber;
    _lastChapterTitle = title;
    final currentLabel = ReadingProgressSummary.epub(
      cfi: 'current-position',
      chapterNumber: chapterNumber,
      chapterTitle: title,
    ).label;
    // The EPUB position listener can notify during layout; avoid calling
    // setState synchronously during the descendant's build phase.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _chapterStatus != currentLabel) {
        setState(() => _chapterStatus = currentLabel);
      }
    });
    _chapterWriteQueue = _chapterWriteQueue.then((_) {
      return _progressStore.recordEpubChapter(
        widget.book.path,
        chapterNumber: chapterNumber,
        chapterTitle: title,
      );
    }).catchError((Object _) {
      // Metadata is supplementary: bookmark and reading resume still work.
    });
  }
  EpubReadingSettings _readingSettings = const EpubReadingSettings();
  bool _readingSettingsLoaded = false;
  Future<void> _settingsWriteQueue = Future<void>.value();

  Future<void> _restoreReadingSettings() async {
    final settings = await EpubReadingSettings.load();
    if (!mounted) return;
    setState(() {
      _readingSettings = settings;
      _readingSettingsLoaded = true;
    });
  }

  void _changeReadingSettings(EpubReadingSettings next) {
    if (!mounted) return;
    setState(() => _readingSettings = next);
    // Serialize writes so rapid slider movement never saves an older setting last.
    _settingsWriteQueue = _settingsWriteQueue.then((_) async {
      final saved = await next.save();
      if (!saved) throw const FileSystemException('Could not save settings');
    }).catchError((Object _) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not save reading settings')),
        );
      }
    });
  }

  Future<void> _showReadingSettings() async {
    if (!_readingSettingsLoaded) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => EpubReaderSettingsSheet(
        settings: _readingSettings,
        onChanged: _changeReadingSettings,
      ),
    );
  }


  void _bookmarkMessage(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _addBookmark() async {
    final cfi = controller?.generateEpubCfi();
    if (cfi == null || cfi.isEmpty) {
      _bookmarkMessage('Wait until the EPUB has loaded, then try again.');
      return;
    }
    try {
      final added = await _bookmarkStore.add(
        bookPath: widget.book.path,
        location: cfi,
        label: 'EPUB reading position',
      );
      _bookmarkMessage(added ? 'Bookmark saved' : 'Already bookmarked here');
    } catch (_) {
      _bookmarkMessage('Could not save bookmark');
    }
  }

  Future<void> _showBookmarks() async {
    final activeController = controller;
    if (activeController == null) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => ReaderBookmarksSheet(
        bookPath: widget.book.path,
        onGoToBookmark: (bookmark) {
          try {
            activeController.gotoEpubCfi(bookmark.location);
          } catch (_) {
            _bookmarkMessage('Could not open this bookmark');
          }
        },
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _restoreReadingSettings();
    _restoreProgress();
  }

  Future<void> _restoreProgress() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedCfi = prefs.getString(_epubProgressKey(widget.book));
      final savedSummary = _progressStore.read(
        prefs,
        path: widget.book.path,
        type: 'epub',
      );
      final epubController = EpubController(
        document: EpubDocument.openFile(File(widget.book.path)),
        epubCfi: savedCfi,
      );
      if (!mounted) {
        epubController.dispose();
        return;
      }
      setState(() {
        controller = epubController;
        _openingError = null;
        if (savedSummary.label != 'Not started' &&
            savedSummary.label != 'Resume available') {
          _chapterStatus = savedSummary.label;
        }
      });
    } catch (_) {
      if (mounted) {
        setState(() => _openingError =
            'Selura could not prepare this EPUB. Your saved progress '
            'and bookmarks are still stored.');
      }
    }
  }

  Future<void> _saveProgress() async {
    final cfi = controller?.generateEpubCfi();
    if (cfi == null || cfi.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_epubProgressKey(widget.book), cfi);
  }

  @override
  void dispose() {
    _narration.close();
    final activeController = controller;
    if (activeController != null) {
      final cfi = activeController.generateEpubCfi();
      if (cfi != null && cfi.isNotEmpty) {
        SharedPreferences.getInstance().then(
          (prefs) => prefs.setString(_epubProgressKey(widget.book), cfi),
        );
      }
      activeController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final activeController = controller;
    final palette = _readingSettings.theme.palette;
    return Scaffold(
      backgroundColor: palette.background,
      appBar: AppBar(
        backgroundColor: palette.background,
        foregroundColor: palette.foreground,
        title: Text(widget.book.title),
        actions: [
          IconButton(
            tooltip: 'Listen to chapter',
            onPressed: activeController == null ? null : _showNarration,
            icon: const Icon(Icons.headphones_rounded),
          ),
          IconButton(
            tooltip: 'Reading appearance',
            onPressed: _readingSettingsLoaded ? _showReadingSettings : null,
            icon: const Icon(Icons.text_fields_rounded),
          ),
          IconButton(
            tooltip: 'Add bookmark',
            onPressed: activeController == null ? null : _addBookmark,
            icon: const Icon(Icons.bookmark_add_outlined),
          ),
          IconButton(
            tooltip: 'View bookmarks',
            onPressed: activeController == null ? null : _showBookmarks,
            icon: const Icon(Icons.bookmarks_outlined),
          ),
          IconButton(
            tooltip: 'Chapters',
            icon: const Icon(Icons.list),
            onPressed: activeController == null
                ? null
                : () => showModalBottomSheet(
                      context: context,
                      builder: (_) => EpubViewTableOfContents(
                        controller: activeController,
                      ),
                    ),
          ),
        ],
      ),
      bottomNavigationBar: _chapterStatus == null
          ? null
          : ColoredBox(
              color: palette.background,
              child: SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 10),
                  child: Text(
                    _chapterStatus!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: palette.foreground.withValues(alpha: 0.75),
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
            ),
      body: _openingError != null
          ? SeluraLoadError(
              title: 'Unable to open EPUB',
              message: _openingError!,
              onRetry: _retryOpening,
            )
          : activeController == null
              ? const SeluraLoadingView(
                  title: 'Opening your story',
                  subtitle: 'Preparing chapters and restoring your place',
                )
              : EpubView(
              controller: activeController,
              builders: EpubViewBuilders<DefaultBuilderOptions>(
                loaderBuilder: (_) => const SeluraLoadingView(
                  title: 'Preparing this book',
                  subtitle: 'Formatting text for comfortable reading',
                ),
                errorBuilder: (_, error) => SeluraLoadError(
                  title: 'This EPUB could not be loaded',
                  message: 'The file may be damaged or unsupported. '
                      'You can retry without losing your library.',
                  onRetry: _retryOpening,
                ),
                options: DefaultBuilderOptions(
                  textStyle: _readingSettings.textStyle,
                  paragraphPadding: EdgeInsets.symmetric(
                    horizontal: _readingSettings.horizontalMargin,
                  ),
                  chapterPadding: EdgeInsets.symmetric(
                    horizontal: _readingSettings.horizontalMargin,
                    vertical: 8,
                  ),
                ),
                chapterDividerBuilder: (chapter) => Container(
                  width: double.infinity,
                  padding: const EdgeInsets.fromLTRB(20, 22, 20, 22),
                  color: palette.chapterBackground,
                  child: Text(
                    chapter.Title ?? '',
                    style: TextStyle(
                      color: palette.foreground,
                      fontSize: _readingSettings.fontSize + 4,
                      fontFamily: _readingSettings.font.family,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
              onChapterChanged: (value) {
                final chapter = value?.chapter;
                if (chapter != _currentSpeechChapter) {
                  _currentSpeechChapter = chapter;
                  if (_narration.status == NarrationStatus.playing ||
                      _narration.status == NarrationStatus.paused) {
                    unawaited(_narration.stop());
                  }
                }
                _saveProgress();
                _onReadingChapterChanged(
                  value?.chapterNumber,
                  value?.chapter?.Title,
                );
              },
            ),
    );
  }
}

class PdfBookPage extends StatefulWidget {
  final Book book;

  const PdfBookPage({super.key, required this.book});

  @override
  State<PdfBookPage> createState() => _PdfBookPageState();
}

class _PdfBookPageState extends State<PdfBookPage> {
  PdfControllerPinch? controller;
  String? _openingError;
  final BookmarkStore _bookmarkStore = const BookmarkStore();

  Future<void> _retryOpening() async {
    final oldController = controller;
    if (!mounted) return;
    setState(() {
      controller = null;
      _openingError = null;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      oldController?.dispose();
      if (mounted) unawaited(_restoreProgress());
    });
  }
  final ReadingProgressStore _progressStore = const ReadingProgressStore();
  int? _visiblePage;
  int? _totalPages;

  Future<void> _recordPdfPageCount(int total) async {
    try {
      await _progressStore.recordPdfTotal(widget.book.path, total);
    } catch (_) {
      // Missing optional metadata never blocks PDF reading.
    }
  }

  void _bookmarkMessage(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _addBookmark() async {
    final current = controller;
    if (current == null || current.pagesCount == null || current.page < 1) {
      _bookmarkMessage('Wait until the PDF has loaded, then try again.');
      return;
    }
    final page = current.page;
    try {
      final added = await _bookmarkStore.add(
        bookPath: widget.book.path,
        location: page.toString(),
        label: 'Page $page',
      );
      _bookmarkMessage(added ? 'Bookmark saved' : 'Already bookmarked here');
    } catch (_) {
      _bookmarkMessage('Could not save bookmark');
    }
  }

  Future<void> _showBookmarks() async {
    final activeController = controller;
    if (activeController == null) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => ReaderBookmarksSheet(
        bookPath: widget.book.path,
        onGoToBookmark: (bookmark) {
          final page = int.tryParse(bookmark.location);
          final total = activeController.pagesCount;
          if (page == null || page < 1 || (total != null && page > total)) {
            _bookmarkMessage('This PDF bookmark is no longer valid');
            return;
          }
          try {
            activeController.jumpToPage(page);
          } catch (_) {
            _bookmarkMessage('Could not open this bookmark');
          }
        },
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _restoreProgress();
  }

  Future<void> _restoreProgress() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedPage = prefs.getInt(_pdfProgressKey(widget.book)) ?? 1;
      final pdfController = PdfControllerPinch(
        document: PdfDocument.openFile(widget.book.path),
        initialPage: savedPage < 1 ? 1 : savedPage,
      );
      if (!mounted) {
        pdfController.dispose();
        return;
      }
      setState(() {
        controller = pdfController;
        _openingError = null;
        _visiblePage = savedPage < 1 ? 1 : savedPage;
        final storedTotal = prefs.getInt(
          ReadingProgressStore.pdfTotalKey(widget.book.path),
        );
        _totalPages = storedTotal != null && storedTotal > 0
            ? storedTotal
            : null;
      });
    } catch (_) {
      if (mounted) {
        setState(() => _openingError =
            'Selura could not prepare this PDF. Your existing library '
            'and reading history are still saved.');
      }
    }
  }

  Future<void> _savePage(int page) async {
    if (page < 1) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_pdfProgressKey(widget.book), page);
  }

  @override
  void dispose() {
    final activeController = controller;
    if (activeController != null) {
      final page = activeController.page;
      if (page >= 1) {
        SharedPreferences.getInstance().then(
          (prefs) => prefs.setInt(_pdfProgressKey(widget.book), page),
        );
      }
      activeController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final activeController = controller;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.book.title),
        actions: [
          IconButton(
            tooltip: 'Add bookmark',
            onPressed: activeController == null ? null : _addBookmark,
            icon: const Icon(Icons.bookmark_add_outlined),
          ),
          IconButton(
            tooltip: 'View bookmarks',
            onPressed: activeController == null ? null : _showBookmarks,
            icon: const Icon(Icons.bookmarks_outlined),
          ),
        ],
      ),
      bottomNavigationBar: activeController == null
          ? null
          : SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 6, 20, 12),
                child: _BookProgressIndicator(
                  progress: ReadingProgressSummary.pdf(
                    page: _visiblePage,
                    totalPages: _totalPages,
                  ),
                ),
              ),
            ),
      body: _openingError != null
          ? SeluraLoadError(
              title: 'Unable to open PDF',
              message: _openingError!,
              onRetry: _retryOpening,
            )
          : activeController == null
              ? const SeluraLoadingView(
                  title: 'Opening your document',
                  subtitle: 'Restoring the last page you read',
                )
              : PdfViewPinch(
              controller: activeController,
              builders: pdfx.PdfViewPinchBuilders<pdfx.DefaultBuilderOptions>(
                options: const pdfx.DefaultBuilderOptions(),
                documentLoaderBuilder: (_) => const SeluraLoadingView(
                  title: 'Rendering PDF pages',
                  subtitle: 'Preparing the document for smooth scrolling',
                ),
                pageLoaderBuilder: (_) => const Center(
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                errorBuilder: (_, error) => SeluraLoadError(
                  title: 'Could not display PDF',
                  message: 'The document may be damaged or unsupported.',
                  onRetry: _retryOpening,
                ),
              ),
              onDocumentLoaded: (document) {
                final total = document.pagesCount;
                if (total > 0) {
                  WidgetsBinding.instance.addPostFrameCallback((_) {
                    if (mounted && _totalPages != total) {
                      setState(() => _totalPages = total);
                    }
                  });
                }
                unawaited(_recordPdfPageCount(total));
              },
              onPageChanged: (page) {
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (mounted && _visiblePage != page) {
                    setState(() => _visiblePage = page);
                  }
                });
                _savePage(page);
              },
            ),
    );
  }
}
