import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:epub_view/epub_view.dart' hide Image;
import 'package:file_picker/file_picker.dart';
import 'package:flutter_file_dialog/flutter_file_dialog.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdfx/pdfx.dart' hide DefaultBuilderOptions;
import 'package:pdfx/pdfx.dart' as pdfx;
import 'package:shared_preferences/shared_preferences.dart';

import 'bookmarks.dart';
import 'cover_cache.dart';
import 'cover_decode.dart';
import 'library_backup.dart';
import 'reader_settings.dart';
import 'reading_progress.dart';
import 'reader_navigation.dart';
import 'reader_chrome.dart';
import 'epub_narration.dart';
import 'epub_narration_sheet.dart';
import 'selura_ui.dart';
import 'bookshelf_design.dart';

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
        dark ? const Color(0xFF181720) : const Color(0xFFF8F6F1),
    appBarTheme: AppBarTheme(
      elevation: 0,
      backgroundColor:
          dark ? const Color(0xFF181720) : const Color(0xFFF8F6F1),
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
enum _LibraryAction { backup, restore }

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
  String busyTitle = 'Adding your book';
  String busySubtitle = 'Copying your file into your offline library';
  bool loadingLibrary = true;
  String? libraryLoadError;
  bool gridView = true;
  String query = '';
  _LibrarySort sort = _LibrarySort.recent;
  SeluraShelfFilter shelfFilter = SeluraShelfFilter.all;

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
    if (busy) return;
    setState(() {
      busy = true;
      busyTitle = 'Adding your book';
      busySubtitle = 'Copying your file into your offline library';
    });
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


  void _libraryMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _exportLibraryBackup() async {
    if (busy || loadingLibrary) return;
    setState(() {
      busy = true;
      busyTitle = 'Preparing your backup';
      busySubtitle = 'Packing your books and reading positions offline';
    });
    File? temporaryZip;
    try {
      final prefs = await SharedPreferences.getInstance();
      final temp = await getTemporaryDirectory();
      final name = 'Selura-library-' +
          DateTime.now().millisecondsSinceEpoch.toString() + '.zip';
      temporaryZip = File(temp.path + '/' + name);
      await const SeluraBackupService().export(
        books: books.map((book) => BackupBook(
          path: book.path,
          title: book.title,
          type: book.type,
          favorite: book.favorite,
          lastOpened: book.lastOpened,
        )).toList(),
        prefs: prefs,
        output: temporaryZip,
      );
      if (!mounted) return;
      final saved = await FlutterFileDialog.saveFile(
        params: SaveFileDialogParams(
          sourceFilePath: temporaryZip.path,
          fileName: name,
          mimeTypesFilter: const ['application/zip'],
        ),
      );
      _libraryMessage(saved == null
          ? 'Backup cancelled. Your library is unchanged.'
          : 'Backup saved. Keep the ZIP outside Selura for safekeeping.');
    } catch (error) {
      _libraryMessage('Could not create backup: ' + error.toString());
    } finally {
      try {
        if (temporaryZip != null && await temporaryZip.exists()) {
          await temporaryZip.delete();
        }
      } catch (_) {
        // Temporary cleanup cannot affect library files.
      }
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _restoreLibraryBackup() async {
    if (busy || loadingLibrary) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Restore Selura library'),
        content: const Text(
          'Select a Selura ZIP backup. New books and their reading positions '
          'will be restored without removing or replacing your existing '
          'books, bookmarks or preferences. Matching books are skipped. '
          'Keep your original backup until the restoration is verified.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Choose backup'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    final selected = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: ['zip'],
    );
    if (selected == null || !mounted) return;
    if (selected.path == null) {
      _libraryMessage('Could not access that ZIP file on this phone.');
      return;
    }
    setState(() {
      busy = true;
      busyTitle = 'Restoring your library';
      busySubtitle = 'Validating books and remapping saved positions';
    });
    try {
      final prefs = await SharedPreferences.getInstance();
      final documents = await getApplicationDocumentsDirectory();
      final result = await const SeluraBackupService().restore(
        backup: File(selected.path!),
        documents: documents,
        prefs: prefs,
      );
      if (!mounted) return;
      await _load();
      _libraryMessage('Restored ' + result.imported.toString() +
          ' books; skipped ' + result.skipped.toString() +
          ' already in your library.');
    } catch (error) {
      _libraryMessage('Restore cancelled: ' + error.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void _selectLibraryAction(_LibraryAction action) {
    switch (action) {
      case _LibraryAction.backup:
        unawaited(_exportLibraryBackup());
        break;
      case _LibraryAction.restore:
        unawaited(_restoreLibraryBackup());
        break;
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
      seluraReaderRoute(
        child: book.type == 'pdf'
            ? PdfBookPage(book: book)
            : EpubBookPage(book: book),
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

  void _resetShelfFilters() {
    searchController.clear();
    setState(() {
      query = '';
      shelfFilter = SeluraShelfFilter.all;
    });
  }

  List<Book> get _visibleBooks {
    final normalized = query.trim().toLowerCase();
    final result = books
        .where(
          (book) =>
              shelfFilter.accepts(format: book.type, favorite: book.favorite) &&
              (normalized.isEmpty ||
                  book.title.toLowerCase().contains(normalized) ||
                  book.type.toLowerCase().contains(normalized)),
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
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Selura',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w900,
                letterSpacing: -0.8,
              ),
            ),
            Text(
              'THE READING ROOM',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                letterSpacing: 1.7,
                fontWeight: FontWeight.w700,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
                fontSize: 9,
              ),
            ),
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
          PopupMenuButton<_LibraryAction>(
            tooltip: 'Library backup and restore',
            enabled: !busy && !loadingLibrary,
            onSelected: _selectLibraryAction,
            itemBuilder: (_) => const [
              PopupMenuItem(
                value: _LibraryAction.backup,
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.archive_outlined),
                  title: Text('Back up library'),
                ),
              ),
              PopupMenuItem(
                value: _LibraryAction.restore,
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.settings_backup_restore_rounded),
                  title: Text('Restore backup'),
                ),
              ),
            ],
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
                        : CustomScrollView(
                        key: const PageStorageKey<String>('selura-library-scroll'),
                        slivers: [
                          SliverPadding(
                            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                            sliver: SliverToBoxAdapter(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SeluraLibraryBanner(
                                    bookCount: books.length,
                                    favoriteCount:
                                        books.where((book) => book.favorite).length,
                                    onImport: busy ? null : _import,
                                  ),
                                  if (continueReading.isNotEmpty) ...[
                                    const SizedBox(height: 27),
                                    const SeluraShelfHeading(
                                      title: 'Continue reading',
                                      subtitle: 'Return to a story you love',
                                    ),
                                    const SizedBox(height: 14),
                                    SizedBox(
                                      height: 190,
                                      child: ListView.separated(
                                        key: const Key('selura-continue-carousel'),
                                        scrollDirection: Axis.horizontal,
                                        itemCount: continueReading.length,
                                        separatorBuilder: (_, __) =>
                                            const SizedBox(width: 13),
                                        itemBuilder: (context, index) {
                                          final book = continueReading[index];
                                          return _ContinueCard(
                                            book: book,
                                            coverPath: coverPaths[book.path],
                                            progress: progressLabels[book.path] ??
                                                ReadingProgressSummary.notStarted,
                                            onTap: () => _openBook(book),
                                          );
                                        },
                                      ),
                                    ),
                                  ],
                                  const SizedBox(height: 28),
                                  SeluraShelfHeading(
                                    title: 'Your bookshelf',
                                    subtitle:
                                        '${visibleBooks.length} of ${books.length} books',
                                  ),
                                  const SizedBox(height: 15),
                                  TextField(
                                    key: const Key('selura-shelf-search'),
                                    controller: searchController,
                                    onChanged: (value) =>
                                        setState(() => query = value),
                                    textInputAction: TextInputAction.search,
                                    decoration: InputDecoration(
                                      hintText: 'Find a book or format',
                                      prefixIcon: const Icon(Icons.search_rounded),
                                      suffixIcon: query.isEmpty
                                          ? null
                                          : IconButton(
                                              tooltip: 'Clear search',
                                              onPressed: _clearSearch,
                                              icon: const Icon(Icons.close_rounded),
                                            ),
                                      filled: true,
                                      fillColor: Theme.of(context)
                                          .colorScheme.surfaceContainerLow,
                                      contentPadding:
                                          const EdgeInsets.symmetric(vertical: 14),
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(17),
                                        borderSide: BorderSide(
                                          color: Theme.of(context)
                                              .colorScheme.outlineVariant
                                              .withValues(alpha: 0.45),
                                        ),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(17),
                                        borderSide: BorderSide(
                                          color: Theme.of(context).colorScheme.primary,
                                          width: 1.6,
                                        ),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  SeluraShelfFilterBar(
                                    selected: shelfFilter,
                                    onSelected: (value) =>
                                        setState(() => shelfFilter = value),
                                  ),
                                  const SizedBox(height: 16),
                                ],
                              ),
                            ),
                          ),
                          if (visibleBooks.isEmpty)
                            SliverToBoxAdapter(
                              child: SeluraShelfEmptyResults(
                                onReset: _resetShelfFilters,
                              ),
                            )
                          else if (gridView)
                            SliverPadding(
                              padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
                              sliver: SliverGrid.builder(
                                itemCount: visibleBooks.length,
                                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount:
                                      MediaQuery.sizeOf(context).width >= 700 ? 4 : 2,
                                  crossAxisSpacing: 14,
                                  mainAxisSpacing: 18,
                                  childAspectRatio: 0.61,
                                ),
                                itemBuilder: (context, index) {
                                  final book = visibleBooks[index];
                                  return _GridBookCard(
                                    key: ValueKey(book.path),
                                    book: book,
                                    coverPath: coverPaths[book.path],
                                    progress: progressLabels[book.path] ??
                                        ReadingProgressSummary.notStarted,
                                    onTap: () => _openBook(book),
                                    onFavorite: () => _toggleFavorite(book),
                                  );
                                },
                              ),
                            )
                          else
                            SliverPadding(
                              padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
                              sliver: SliverList.separated(
                                itemCount: visibleBooks.length,
                                separatorBuilder: (_, __) =>
                                    const SizedBox(height: 10),
                                itemBuilder: (context, index) {
                                  final book = visibleBooks[index];
                                  return _ListBookCard(
                                    key: ValueKey(book.path),
                                    book: book,
                                    coverPath: coverPaths[book.path],
                                    progress: progressLabels[book.path] ??
                                        ReadingProgressSummary.notStarted,
                                    opened: _relativeOpened(book),
                                    onTap: () => _openBook(book),
                                    onFavorite: () => _toggleFavorite(book),
                                  );
                                },
                              ),
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
                child: SeluraLoadingView(
                  key: const Key('selura-import-loading'),
                  title: busyTitle,
                  subtitle: busySubtitle,
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
              label: const Text('Add book'),
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
            LayoutBuilder(
              builder: (context, constraints) {
                final density = MediaQuery.devicePixelRatioOf(context);
                return ClipRRect(
                  borderRadius: borderRadius,
                  child: Image.file(
                    File(coverPath!),
                    fit: BoxFit.cover,
                    cacheWidth: seluraCoverDecodePixels(
                      constraints.maxWidth, density,
                    ),
                    cacheHeight: seluraCoverDecodePixels(
                      constraints.maxHeight, density,
                    ),
                    filterQuality: FilterQuality.low,
                    errorBuilder: (context, error, stackTrace) => Center(
                      child: Icon(
                        Icons.auto_stories_rounded,
                        size: 46,
                        color: scheme.onPrimaryContainer,
                      ),
                    ),
                  ),
                );
              },
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
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return SizedBox(
      width: 336,
      child: Card(
        color: colors.surfaceContainerLow,
        clipBehavior: Clip.antiAlias,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(23),
          side: BorderSide(
            color: colors.outlineVariant.withValues(alpha: 0.35),
          ),
        ),
        child: InkWell(
          key: Key('selura-continue-${book.path}'),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                _BookCover(
                  book: book,
                  coverPath: coverPath,
                  width: 96,
                  height: 157,
                  borderRadius: BorderRadius.circular(13),
                ),
                const SizedBox(width: 15),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'PICK UP WHERE YOU LEFT OFF',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.labelSmall?.copyWith(
                          fontSize: 9,
                          color: colors.primary,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.45,
                        ),
                      ),
                      const SizedBox(height: 9),
                      Text(
                        book.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                          height: 1.15,
                        ),
                      ),
                      const SizedBox(height: 9),
                      _BookProgressIndicator(progress: progress),
                      const Spacer(),
                      Row(
                        children: [
                          Icon(
                            Icons.play_arrow_rounded,
                            size: 19,
                            color: colors.primary,
                          ),
                          const SizedBox(width: 5),
                          Text(
                            'Continue',
                            style: theme.textTheme.labelLarge?.copyWith(
                              color: colors.primary,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const Spacer(),
                          Icon(
                            Icons.arrow_forward_rounded,
                            color: colors.primary,
                            size: 18,
                          ),
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
}

class _GridBookCard extends StatelessWidget {
  final Book book;
  final String? coverPath;
  final ReadingProgressSummary progress;
  final VoidCallback onTap;
  final VoidCallback onFavorite;

  const _GridBookCard({
    super.key,
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
    super.key,
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

enum _EpubReaderTool { addBookmark, bookmarks, chapters }

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

  void _toggleFocusMode() => setState(() => _focusMode = !_focusMode);

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
  bool _focusMode = false;
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
    return ReaderFrame(
      focusMode: _focusMode,
      onExitFocus: _toggleFocusMode,
      backgroundColor: palette.background,
      foregroundColor: palette.foreground,
      appBar: AppBar(
        backgroundColor: palette.background,
        foregroundColor: palette.foreground,
        title: Text(
          widget.book.title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        actions: [
          IconButton(
            tooltip: 'Listen to chapter',
            onPressed: activeController == null ? null : _showNarration,
            icon: const Icon(Icons.headphones_rounded),
          ),
          IconButton(
            key: const Key('epub-focus-toggle'),
            tooltip: 'Enter focus mode',
            onPressed: _toggleFocusMode,
            icon: const Icon(Icons.fullscreen_rounded),
          ),
          IconButton(
            tooltip: 'Reading appearance',
            onPressed: _readingSettingsLoaded ? _showReadingSettings : null,
            icon: const Icon(Icons.text_fields_rounded),
          ),
          PopupMenuButton<_EpubReaderTool>(
            tooltip: 'More reading tools',
            icon: const Icon(Icons.more_vert_rounded),
            onSelected: (tool) {
              if (activeController == null) return;
              switch (tool) {
                case _EpubReaderTool.addBookmark:
                  unawaited(_addBookmark());
                  break;
                case _EpubReaderTool.bookmarks:
                  unawaited(_showBookmarks());
                  break;
                case _EpubReaderTool.chapters:
                  showModalBottomSheet<void>(
                    context: context,
                    showDragHandle: true,
                    builder: (_) => EpubViewTableOfContents(
                      controller: activeController,
                    ),
                  );
                  break;
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem(
                value: _EpubReaderTool.addBookmark,
                enabled: activeController != null,
                child: const Row(
                  children: [
                    Icon(Icons.bookmark_add_outlined),
                    SizedBox(width: 14),
                    Text('Add bookmark'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: _EpubReaderTool.bookmarks,
                enabled: activeController != null,
                child: const Row(
                  children: [
                    Icon(Icons.bookmarks_outlined),
                    SizedBox(width: 14),
                    Text('Saved bookmarks'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: _EpubReaderTool.chapters,
                enabled: activeController != null,
                child: const Row(
                  children: [
                    Icon(Icons.list_rounded),
                    SizedBox(width: 14),
                    Text('Chapters'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      bottomBar: _chapterStatus == null
          ? null
          : ReaderChromeFooter(
              category: 'CURRENT CHAPTER',
              label: _chapterStatus!,
              leadingIcon: Icons.auto_stories_rounded,
              backgroundColor: palette.background,
              foregroundColor: palette.foreground,
              trailing: ReaderFontSizeControls(
                fontSize: _readingSettings.fontSize,
                foregroundColor: palette.foreground,
                onChanged: _readingSettingsLoaded
                    ? (size) => _changeReadingSettings(
                          _readingSettings.copyWith(fontSize: size),
                        )
                    : null,
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
  bool _focusMode = false;
  void _toggleFocusMode() => setState(() => _focusMode = !_focusMode);

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
    return ReaderFrame(
      focusMode: _focusMode,
      onExitFocus: _toggleFocusMode,
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      foregroundColor: Theme.of(context).colorScheme.onSurface,
      appBar: AppBar(
        title: Text(widget.book.title),
        actions: [
          IconButton(
            key: const Key('pdf-focus-toggle'),
            tooltip: 'Enter focus mode',
            onPressed: _toggleFocusMode,
            icon: const Icon(Icons.fullscreen_rounded),
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
        ],
      ),
      bottomBar: activeController == null
          ? null
          : ReaderChromeFooter(
              category: 'READING POSITION',
              label: ReadingProgressSummary.pdf(
                page: _visiblePage,
                totalPages: _totalPages,
              ).label,
              progressFraction: ReadingProgressSummary.pdf(
                page: _visiblePage,
                totalPages: _totalPages,
              ).pageFraction,
              leadingIcon: Icons.picture_as_pdf_rounded,
              backgroundColor: Theme.of(context).scaffoldBackgroundColor,
              foregroundColor: Theme.of(context).colorScheme.onSurface,
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
