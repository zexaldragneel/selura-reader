import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/bookshelf_design.dart';
import 'package:selura_reader/selura_ui.dart';

void main() {
  test('shelf filters match the actual local book attributes', () {
    expect(
      SeluraShelfFilter.all.accepts(format: 'epub', favorite: false),
      isTrue,
    );
    expect(
      SeluraShelfFilter.epub.accepts(format: 'EPUB', favorite: false),
      isTrue,
    );
    expect(
      SeluraShelfFilter.epub.accepts(format: 'pdf', favorite: true),
      isFalse,
    );
    expect(
      SeluraShelfFilter.pdf.accepts(format: 'pdf', favorite: false),
      isTrue,
    );
    expect(
      SeluraShelfFilter.favorites.accepts(format: 'pdf', favorite: true),
      isTrue,
    );
    expect(
      SeluraShelfFilter.favorites.accepts(format: 'epub', favorite: false),
      isFalse,
    );
  });

  testWidgets('filter chips change selection and are scrollable on phones',
      (tester) async {
    tester.view.physicalSize = const Size(320, 740);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    SeluraShelfFilter selected = SeluraShelfFilter.all;
    await tester.pumpWidget(MaterialApp(
      home: StatefulBuilder(
        builder: (context, setState) => Scaffold(
          body: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: SeluraShelfFilterBar(
              selected: selected,
              onSelected: (value) => setState(() => selected = value),
            ),
          ),
        ),
      ),
    ));

    await tester.tap(find.byKey(const Key('selura-filter-epub')));
    await tester.pump();
    expect(selected, SeluraShelfFilter.epub);
    expect(tester.widget<ChoiceChip>(
      find.byKey(const Key('selura-filter-epub')),
    ).selected, isTrue);

    final favorites = find.byKey(const Key('selura-filter-favorites'));
    await tester.ensureVisible(favorites);
    await tester.pumpAndSettle();
    await tester.tap(favorites);
    await tester.pump();
    expect(selected, SeluraShelfFilter.favorites);
    expect(tester.takeException(), isNull);
  });

  testWidgets('empty search state clears the current filters', (tester) async {
    var resets = 0;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: SeluraShelfEmptyResults(onReset: () => resets++),
      ),
    ));
    expect(find.text('No stories found'), findsOneWidget);
    await tester.tap(find.byKey(const Key('selura-clear-filters')));
    expect(resets, 1);
  });

  testWidgets('premium library banner uses real counts and an active import',
      (tester) async {
    var imports = 0;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Center(
          child: SizedBox(
            width: 350,
            child: SeluraLibraryBanner(
              bookCount: 12,
              favoriteCount: 3,
              onImport: () => imports++,
            ),
          ),
        ),
      ),
    ));
    expect(find.byKey(const Key('selura-premium-library-banner')),
        findsOneWidget);
    expect(find.text('12'), findsOneWidget);
    expect(find.text('3'), findsOneWidget);
    await tester.tap(find.byKey(const Key('selura-banner-import')));
    expect(imports, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('premium banner fits a narrow Android screen in dark mode',
      (tester) async {
    tester.view.physicalSize = const Size(320, 740);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const MaterialApp(
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(brightness: Brightness.dark),
      home: Scaffold(
        body: Padding(
          padding: EdgeInsets.all(12),
          child: SeluraLibraryBanner(
            bookCount: 7,
            favoriteCount: 2,
            onImport: null,
          ),
        ),
      ),
    ));
    expect(find.text('A little space for\nbig stories.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
