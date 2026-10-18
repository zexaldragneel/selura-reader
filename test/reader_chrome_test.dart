import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/reader_chrome.dart';

class _MountedReader extends StatefulWidget {
  const _MountedReader({required this.onInit, required this.onDispose});

  final VoidCallback onInit;
  final VoidCallback onDispose;

  @override
  State<_MountedReader> createState() => _MountedReaderState();
}

class _MountedReaderState extends State<_MountedReader> {
  @override
  void initState() {
    super.initState();
    widget.onInit();
  }

  @override
  void dispose() {
    widget.onDispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      const Center(child: Text('Book content'));
}

void main() {
  testWidgets('focus mode hides bars and keeps expensive reader mounted',
      (tester) async {
    var focus = false;
    var initialized = 0;
    var disposed = 0;
    await tester.pumpWidget(MaterialApp(
      home: StatefulBuilder(
        builder: (context, change) => ReaderFrame(
          focusMode: focus,
          onExitFocus: () => change(() => focus = false),
          backgroundColor: Colors.white,
          foregroundColor: Colors.black,
          appBar: AppBar(
            title: const Text('Reading toolbar'),
            actions: [
              IconButton(
                tooltip: 'Enter focus mode',
                onPressed: () => change(() => focus = true),
                icon: const Icon(Icons.fullscreen),
              ),
            ],
          ),
          bottomBar: const Text('Current chapter footer'),
          body: _MountedReader(
            onInit: () => initialized++,
            onDispose: () => disposed++,
          ),
        ),
      ),
    ));
    expect(initialized, 1);
    expect(find.text('Reading toolbar'), findsOneWidget);
    expect(find.text('Current chapter footer'), findsOneWidget);
    expect(find.text('Book content'), findsOneWidget);

    await tester.tap(find.byTooltip('Enter focus mode'));
    await tester.pump();
    expect(find.text('Reading toolbar'), findsNothing);
    expect(find.text('Current chapter footer'), findsNothing);
    expect(find.text('Book content'), findsOneWidget);
    expect(find.byKey(const Key('reader-focus-exit')), findsOneWidget);
    expect(initialized, 1);
    expect(disposed, 0);

    await tester.tap(find.byKey(const Key('reader-focus-exit')));
    await tester.pump();
    expect(find.text('Reading toolbar'), findsOneWidget);
    expect(find.text('Current chapter footer'), findsOneWidget);
    expect(initialized, 1);
    expect(disposed, 0);
  });

  testWidgets('EPUB quick typography increases and decreases exactly one step',
      (tester) async {
    var fontSize = 16.0;
    await tester.pumpWidget(MaterialApp(
      home: StatefulBuilder(
        builder: (context, change) => Scaffold(
          body: Center(
            child: SizedBox(
              width: 330,
              child: ReaderChromeFooter(
                category: 'CURRENT CHAPTER',
                label: 'Chapter 12 · A long chapter title',
                leadingIcon: Icons.auto_stories_rounded,
                backgroundColor: Colors.white,
                foregroundColor: Colors.black,
                trailing: ReaderFontSizeControls(
                  fontSize: fontSize,
                  foregroundColor: Colors.black,
                  onChanged: (next) => change(() => fontSize = next),
                ),
              ),
            ),
          ),
        ),
      ),
    ));
    expect(find.text('CURRENT CHAPTER'), findsOneWidget);
    expect(find.text('16'), findsOneWidget);
    await tester.tap(find.byKey(const Key('reader-font-larger')));
    await tester.pump();
    expect(fontSize, 17);
    await tester.tap(find.byKey(const Key('reader-font-smaller')));
    await tester.pump();
    expect(fontSize, 16);
  });

  testWidgets('quick typography disables past 12sp and 32sp',
      (tester) async {
    var fontSize = 12.0;
    await tester.pumpWidget(MaterialApp(
      home: StatefulBuilder(
        builder: (context, change) => Scaffold(
          body: ReaderFontSizeControls(
            fontSize: fontSize,
            foregroundColor: Colors.black,
            onChanged: (next) => change(() => fontSize = next),
          ),
        ),
      ),
    ));
    expect(
      tester.widget<IconButton>(
        find.byKey(const Key('reader-font-smaller')),
      ).onPressed,
      isNull,
    );
    for (var i = 0; i < 20; i++) {
      await tester.tap(find.byKey(const Key('reader-font-larger')));
      await tester.pump();
    }
    expect(fontSize, 32);
    expect(
      tester.widget<IconButton>(
        find.byKey(const Key('reader-font-larger')),
      ).onPressed,
      isNull,
    );
  });

  testWidgets('PDF status footer shows genuine page progress',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: ReaderChromeFooter(
          category: 'READING POSITION',
          label: 'Page 18 of 120',
          leadingIcon: Icons.picture_as_pdf_rounded,
          progressFraction: 0.15,
          backgroundColor: Colors.white,
          foregroundColor: Colors.black,
        ),
      ),
    ));
    expect(find.text('Page 18 of 120'), findsOneWidget);
    expect(
      tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      ).value,
      0.15,
    );
  });
}
