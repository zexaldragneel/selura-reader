import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/reader_navigation.dart';

void main() {
  testWidgets('reader route immediately hides the underlying bookshelf',
      (tester) async {
    final route = seluraReaderRoute(
      child: const Scaffold(
        body: Center(child: Text('Preparing this book')),
      ),
    );
    expect(route.opaque, isTrue);
    expect(route.transitionDuration, Duration.zero);
    expect(route.reverseTransitionDuration, Duration.zero);

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: Column(
              children: [
                const Text('My Library'),
                TextButton(
                  onPressed: () => Navigator.of(context).push(route),
                  child: const Text('Open EPUB'),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open EPUB'));
    await tester.pump();

    // No half-faded route should leave library text visible during book load.
    expect(find.text('Preparing this book'), findsOneWidget);
    expect(find.text('My Library'), findsNothing);

    await tester.pumpAndSettle();
    expect(find.text('Preparing this book'), findsOneWidget);
  });
}
