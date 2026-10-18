import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/reading_progress.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const store = ReadingProgressStore();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  test('PDF page counts are precise, bounded and never guessed', () {
    final summary = ReadingProgressSummary.pdf(page: 12, totalPages: 240);
    expect(summary.label, 'Page 12 of 240');
    expect(summary.pageFraction, closeTo(0.05, 0.00001));

    expect(ReadingProgressSummary.pdf(page: 7).label, 'Page 7');
    expect(ReadingProgressSummary.pdf(page: 7).pageFraction, isNull);
    expect(
      ReadingProgressSummary.pdf(totalPages: 100).label,
      'Not started · 100 pages',
    );
    expect(ReadingProgressSummary.pdf(page: 900, totalPages: 10).label,
        'Page 10 of 10');
    expect(ReadingProgressSummary.pdf(page: 900, totalPages: 10).pageFraction,
        1.0);
    expect(ReadingProgressSummary.pdf(page: 0, totalPages: 0).label,
        'Not started');
  });

  test('legacy PDF resume keys remain compatible and isolated', () async {
    const pdf = '/local/old.pdf';
    SharedPreferences.setMockInitialValues({
      ReadingProgressStore.pdfPageKey(pdf): 18,
      ReadingProgressStore.epubCfiKey('/local/old.epub'): 'epubcfi(/6/4)',
    });

    final prefs = await SharedPreferences.getInstance();
    var summary = store.read(prefs, path: pdf, type: 'pdf');
    expect(summary.label, 'Page 18');
    expect(summary.pageFraction, isNull);

    expect(await store.recordPdfTotal(pdf, 120), isTrue);
    summary = store.read(prefs, path: pdf, type: 'pdf');
    expect(summary.label, 'Page 18 of 120');
    expect(summary.pageFraction, closeTo(0.15, 0.00001));
    expect(prefs.getInt(ReadingProgressStore.pdfPageKey(pdf)), 18);
    expect(await store.recordPdfTotal(pdf, 0), isFalse);
    expect(prefs.getInt(ReadingProgressStore.pdfTotalKey(pdf)), 120);
  });

  test('EPUB displays chapter metadata only with a saved CFI', () async {
    const book = '/local/book.epub';
    final prefs = await SharedPreferences.getInstance();

    await store.recordEpubChapter(
      book,
      chapterNumber: 3,
      chapterTitle: '  The   Beginning  ',
    );
    expect(store.read(prefs, path: book, type: 'epub').label, 'Not started');

    await prefs.setString(
      ReadingProgressStore.epubCfiKey(book), 'epubcfi(/6/6!/4/2:0)',
    );
    expect(
      store.read(prefs, path: book, type: 'epub').label,
      'Chapter 3 · The Beginning',
    );
    expect(store.read(prefs, path: book, type: 'epub').pageFraction, isNull);
    expect(
      prefs.getString(ReadingProgressStore.epubCfiKey(book)),
      'epubcfi(/6/6!/4/2:0)',
    );
  });

  test('old EPUB positions and missing chapter metadata are safe', () async {
    const book = '/books/old.epub';
    SharedPreferences.setMockInitialValues({
      ReadingProgressStore.epubCfiKey(book): 'epubcfi(/6/2)',
    });
    final prefs = await SharedPreferences.getInstance();
    expect(
      store.read(prefs, path: book, type: 'epub').label,
      'Resume available',
    );
    await store.recordEpubChapter(book, chapterNumber: 7);
    expect(store.read(prefs, path: book, type: 'epub').label, 'Chapter 7');
    await store.recordEpubChapter(
      book, chapterNumber: 7, chapterTitle: 'Chapter 7',
    );
    expect(store.read(prefs, path: book, type: 'epub').label, 'Chapter 7');
  });

  test('invalid chapter numbers cannot replace valid saved metadata', () async {
    const book = '/books/checked.epub';
    final prefs = await SharedPreferences.getInstance();
    await store.recordEpubChapter(
      book, chapterNumber: 2, chapterTitle: 'Middle',
    );
    await store.recordEpubChapter(
      book, chapterNumber: 0, chapterTitle: 'Invalid',
    );
    expect(prefs.getInt(ReadingProgressStore.epubChapterKey(book)), 2);
    expect(prefs.getString(ReadingProgressStore.epubTitleKey(book)), 'Middle');
  });

  test('chapter titles trim whitespace and bound extremely long metadata', () {
    expect(
      ReadingProgressSummary.normalizedChapterTitle('  Name \t\n Here  '),
      'Name Here',
    );
    expect(ReadingProgressSummary.normalizedChapterTitle('   '), isNull);
    final longTitle = 'X' * 120;
    final shortened = ReadingProgressSummary.normalizedChapterTitle(longTitle);
    expect(shortened, isNotNull);
    expect(shortened!.runes.length, 56);
    expect(shortened.endsWith('…'), isTrue);
  });
}
