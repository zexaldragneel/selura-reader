import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/keiyoushi_companion.dart';

void main() {
  test('Keiyoushi uses current protobuf repo, not the retired JSON index', () {
    expect(KeiyoushiCompanion.repositoryUrl, endsWith('/index.pb'));
    expect(KeiyoushiCompanion.repositoryUrl,
        startsWith('https://github.com/keiyoushi/extensions/'));
    expect(
      KeiyoushiCompanion.trustedLink(
        Uri.parse(KeiyoushiCompanion.setupUrl),
      ),
      isTrue,
    );
    expect(
      KeiyoushiCompanion.trustedLink(
        Uri.parse(KeiyoushiCompanion.mihonUrl),
      ),
      isTrue,
    );
    expect(
      KeiyoushiCompanion.trustedLink(
        Uri.parse(KeiyoushiCompanion.listingUrl),
      ),
      isTrue,
    );
    expect(
      KeiyoushiCompanion.trustedLink(
        Uri.parse('https://keiyoushi.github.io.evil.com/add-repo'),
      ),
      isFalse,
    );
    expect(
      KeiyoushiCompanion.trustedLink(
        Uri.parse('http://keiyoushi.github.io/add-repo'),
      ),
      isFalse,
    );
    expect(
      KeiyoushiCompanion.trustedLink(
        Uri.parse('https://mihon.app/download/?external=1'),
      ),
      isFalse,
    );
  });

  testWidgets('companion explains runtime limitation and Android setup',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: KeiyoushiCompanionPage(),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Keiyoushi extensions'), findsOneWidget);
    expect(find.text('Read Keiyoushi sources with Mihon'), findsOneWidget);
    expect(find.textContaining('cannot run them directly'), findsOneWidget);
    expect(find.byKey(const Key('keiyoushi-open-mihon')), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('keiyoushi-copy-repo')),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.byKey(const Key('keiyoushi-open-setup')), findsOneWidget);
    expect(find.byKey(const Key('keiyoushi-copy-repo')), findsOneWidget);
  });
}
