import 'package:shared_preferences/shared_preferences.dart';

/// A location summary, not an estimate of time spent reading.
///
/// Only PDF documents with a verified page count produce a position fraction.
/// EPUB CFIs identify an exact location but do not represent a book percentage.
class ReadingProgressSummary {
  const ReadingProgressSummary({
    required this.label,
    this.pageFraction,
  });

  final String label;
  final double? pageFraction;

  static const notStarted = ReadingProgressSummary(label: 'Not started');

  static ReadingProgressSummary pdf({int? page, int? totalPages}) {
    final validTotal = totalPages != null && totalPages > 0
        ? totalPages
        : null;
    final validPage = page != null && page > 0 ? page : null;
    if (validPage == null) {
      return validTotal == null
          ? notStarted
          : ReadingProgressSummary(label: 'Not started · $validTotal pages');
    }
    if (validTotal == null) {
      return ReadingProgressSummary(label: 'Page $validPage');
    }
    // A replacement PDF may be shorter than the stored page number.
    final shownPage = validPage.clamp(1, validTotal).toInt();
    return ReadingProgressSummary(
      label: 'Page $shownPage of $validTotal',
      pageFraction: shownPage / validTotal,
    );
  }

  static ReadingProgressSummary comic({int? page, int? totalPages}) {
    final summary = pdf(page: page, totalPages: totalPages);
    return summary;
  }

  static ReadingProgressSummary epub({
    String? cfi,
    int? chapterNumber,
    String? chapterTitle,
  }) {
    if (cfi == null || cfi.isEmpty) return notStarted;
    if (chapterNumber == null || chapterNumber < 1) {
      return const ReadingProgressSummary(label: 'Resume available');
    }

    final title = normalizedChapterTitle(chapterTitle);
    final chapterPrefix = 'Chapter $chapterNumber';
    return ReadingProgressSummary(
      label: title == null || title.toLowerCase() == chapterPrefix.toLowerCase()
          ? chapterPrefix
          : '$chapterPrefix · $title',
    );
  }

  static String? normalizedChapterTitle(String? raw) {
    if (raw == null) return null;
    final text = raw.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (text.isEmpty) return null;
    // Avoid unbounded metadata strings in the small bookshelf cards.
    final characters = text.runes.toList();
    if (characters.length <= 56) return text;
    return String.fromCharCodes(characters.take(55)) + '…';
  }
}

/// Preserves existing CFI and PDF page keys for seamless app upgrades.
/// New metadata is deliberately independent from the reader's resume keys.
class ReadingProgressStore {
  const ReadingProgressStore();

  static String epubCfiKey(String path) => 'reading_epub_cfi:$path';
  static String pdfPageKey(String path) => 'reading_pdf_page:$path';
  static String pdfTotalKey(String path) => 'reading_pdf_total_pages:$path';
  static String comicPageKey(String path) => 'reading_comic_page:$path';
  static String comicTotalKey(String path) => 'reading_comic_total:$path';
  static String epubChapterKey(String path) => 'reading_epub_chapter_number:$path';
  static String epubTitleKey(String path) => 'reading_epub_chapter_title:$path';

  ReadingProgressSummary read(
    SharedPreferences prefs, {
    required String path,
    required String type,
  }) {
    if (type == 'cbz') {
      return ReadingProgressSummary.comic(
        page: prefs.getInt(comicPageKey(path)),
        totalPages: prefs.getInt(comicTotalKey(path)),
      );
    }
    if (type == 'pdf') {
      return ReadingProgressSummary.pdf(
        page: prefs.getInt(pdfPageKey(path)),
        totalPages: prefs.getInt(pdfTotalKey(path)),
      );
    }
    return ReadingProgressSummary.epub(
      cfi: prefs.getString(epubCfiKey(path)),
      chapterNumber: prefs.getInt(epubChapterKey(path)),
      chapterTitle: prefs.getString(epubTitleKey(path)),
    );
  }

  Future<bool> recordComicTotal(String path, int totalPages) async {
    if (totalPages < 1) return false;
    final prefs = await SharedPreferences.getInstance();
    return prefs.setInt(comicTotalKey(path), totalPages);
  }

  Future<bool> recordPdfTotal(String path, int totalPages) async {
    if (totalPages < 1) return false;
    final prefs = await SharedPreferences.getInstance();
    return prefs.setInt(pdfTotalKey(path), totalPages);
  }

  Future<void> recordEpubChapter(
    String path, {
    required int chapterNumber,
    String? chapterTitle,
  }) async {
    if (chapterNumber < 1) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(epubChapterKey(path), chapterNumber);
    final title = ReadingProgressSummary.normalizedChapterTitle(chapterTitle);
    if (title == null) {
      await prefs.remove(epubTitleKey(path));
    } else {
      await prefs.setString(epubTitleKey(path), title);
    }
  }
}
