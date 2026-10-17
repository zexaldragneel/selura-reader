import 'dart:convert';
import 'dart:io';

import 'package:epub_view/epub_view.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdfx/pdfx.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() => runApp(const SeluraApp());

class SeluraApp extends StatelessWidget {
  const SeluraApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Selura',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF8D75C9),
          ),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFFB7A2E9),
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        themeMode: ThemeMode.system,
        home: const LibraryPage(),
      );
}

class Book {
  final String path;
  final String title;
  final String type;

  const Book(this.path, this.title, this.type);

  Map<String, String> toJson() => {
        'path': path,
        'title': title,
        'type': type,
      };

  factory Book.fromJson(Map<String, dynamic> json) => Book(
        json['path'] as String,
        json['title'] as String,
        json['type'] as String,
      );
}

String _epubProgressKey(Book book) => 'reading_epub_cfi:${book.path}';
String _pdfProgressKey(Book book) => 'reading_pdf_page:${book.path}';

class LibraryPage extends StatefulWidget {
  const LibraryPage({super.key});

  @override
  State<LibraryPage> createState() => _LibraryPageState();
}

class _LibraryPageState extends State<LibraryPage> {
  List<Book> books = [];
  bool busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getStringList('books') ?? [];
    if (!mounted) return;
    setState(
      () => books = raw
          .map(
            (e) => Book.fromJson(
              jsonDecode(e) as Map<String, dynamic>,
            ),
          )
          .where((book) => File(book.path).existsSync())
          .toList(),
    );
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
      for (final file in files) {
        if (file.path == null) continue;
        final extension = file.extension?.toLowerCase() ?? '';
        if (extension != 'epub' && extension != 'pdf') continue;

        final dest =
            '${dir.path}/${DateTime.now().microsecondsSinceEpoch}_${books.length}.$extension';
        await File(file.path!).copy(dest);
        books.add(
          Book(
            dest,
            file.name.replaceFirst(
              RegExp(r'\.(epub|pdf)$', caseSensitive: false),
              '',
            ),
            extension,
          ),
        );
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(
        'books',
        books.map((b) => jsonEncode(b.toJson())).toList(),
      );
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Import failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Selura'),
          actions: [
            IconButton(
              tooltip: 'Import books',
              onPressed: busy ? null : _import,
              icon: const Icon(Icons.add),
            ),
          ],
        ),
        body: books.isEmpty
            ? Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.menu_book_rounded, size: 72),
                    const SizedBox(height: 12),
                    const Text('Your library is waiting'),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: busy ? null : _import,
                      icon: const Icon(Icons.upload_file),
                      label: const Text('Import EPUB or PDF'),
                    ),
                  ],
                ),
              )
            : ListView.builder(
                itemCount: books.length,
                itemBuilder: (context, index) {
                  final book = books[index];
                  return ListTile(
                    leading: Icon(
                      book.type == 'pdf'
                          ? Icons.picture_as_pdf
                          : Icons.auto_stories,
                    ),
                    title: Text(book.title),
                    subtitle: Text('${book.type.toUpperCase()} • Auto-resume'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => book.type == 'pdf'
                            ? PdfBookPage(book: book)
                            : EpubBookPage(book: book),
                      ),
                    ),
                  );
                },
              ),
        floatingActionButton: books.isEmpty
            ? null
            : FloatingActionButton(
                onPressed: busy ? null : _import,
                child: const Icon(Icons.add),
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

  @override
  void initState() {
    super.initState();
    _restoreProgress();
  }

  Future<void> _restoreProgress() async {
    final prefs = await SharedPreferences.getInstance();
    final savedCfi = prefs.getString(_epubProgressKey(widget.book));
    final epubController = EpubController(
      document: EpubDocument.openFile(File(widget.book.path)),
      epubCfi: savedCfi,
    );

    if (!mounted) {
      epubController.dispose();
      return;
    }
    setState(() => controller = epubController);
  }

  Future<void> _saveProgress() async {
    final cfi = controller?.generateEpubCfi();
    if (cfi == null || cfi.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_epubProgressKey(widget.book), cfi);
  }

  @override
  void dispose() {
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
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.book.title),
        actions: [
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
      body: activeController == null
          ? const Center(child: CircularProgressIndicator())
          : EpubView(
              controller: activeController,
              onChapterChanged: (_) {
                _saveProgress();
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

  @override
  void initState() {
    super.initState();
    _restoreProgress();
  }

  Future<void> _restoreProgress() async {
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
    setState(() => controller = pdfController);
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
      appBar: AppBar(title: Text(widget.book.title)),
      body: activeController == null
          ? const Center(child: CircularProgressIndicator())
          : PdfViewPinch(
              controller: activeController,
              onPageChanged: (page) {
                _savePage(page);
              },
            ),
    );
  }
}
