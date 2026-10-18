import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/reader_settings.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  test('new users receive the existing EPUB renderer defaults', () async {
    final settings = await EpubReadingSettings.load();
    expect(settings.fontSize, 16);
    expect(settings.lineHeight, 1.25);
    expect(settings.horizontalMargin, 16);
    expect(settings.font, EpubReaderFont.system);
    expect(settings.theme, EpubReadingTheme.light);
  });

  test('saves offline preferences and restores them across reads', () async {
    final requested = const EpubReadingSettings().copyWith(
      fontSize: 23,
      lineHeight: 1.6,
      horizontalMargin: 28,
      theme: EpubReadingTheme.sepia,
      font: EpubReaderFont.serif,
    );

    expect(await requested.save(), isTrue);
    final saved = await EpubReadingSettings.load();

    expect(saved.fontSize, 23);
    expect(saved.lineHeight, 1.6);
    expect(saved.horizontalMargin, 28);
    expect(saved.theme, EpubReadingTheme.sepia);
    expect(saved.font, EpubReaderFont.serif);
    expect(saved.textStyle.fontFamily, 'serif');
    expect(saved.textStyle.color, EpubReadingTheme.sepia.palette.foreground);
  });

  test('invalid values are clamped and unknown variants reset to defaults', () {
    final settings = EpubReadingSettings.fromJson({
      'fontSize': 900,
      'lineHeight': -4,
      'horizontalMargin': 999,
      'theme': 'unknown-mode',
      'font': 'unavailable-font',
    });

    expect(settings.fontSize, 32);
    expect(settings.lineHeight, 1.1);
    expect(settings.horizontalMargin, 40);
    expect(settings.theme, EpubReadingTheme.light);
    expect(settings.font, EpubReaderFont.system);
  });

  test('malformed stored preferences do not prevent opening EPUBs', () async {
    SharedPreferences.setMockInitialValues({
      EpubReadingSettings.storageKey: '{invalid-json',
    });
    final settings = await EpubReadingSettings.load();
    expect(settings.theme, EpubReadingTheme.light);
    expect(settings.fontSize, 16);
  });

  test('unsupported values and non-numeric fields use safe defaults', () async {
    SharedPreferences.setMockInitialValues({
      EpubReadingSettings.storageKey: jsonEncode({
        'fontSize': 'huge',
        'lineHeight': null,
        'horizontalMargin': -12,
        'theme': 'dark',
        'font': 'monospace',
      }),
    });
    final settings = await EpubReadingSettings.load();
    expect(settings.fontSize, 16);
    expect(settings.lineHeight, 1.25);
    expect(settings.horizontalMargin, 8);
    expect(settings.theme, EpubReadingTheme.dark);
    expect(settings.font, EpubReaderFont.monospace);
    expect(settings.textStyle.fontFamily, 'monospace');
  });

  testWidgets('theme and font chips provide working live settings controls',
      (tester) async {
    EpubReadingSettings current = const EpubReadingSettings();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: EpubReaderSettingsSheet(
            settings: current,
            onChanged: (next) => current = next,
          ),
        ),
      ),
    );

    await tester.tap(find.byKey(const Key('reader-theme-sepia')));
    await tester.pumpAndSettle();
    expect(current.theme, EpubReadingTheme.sepia);
    expect(
      tester.widget<ChoiceChip>(find.byKey(const Key('reader-theme-sepia')))
          .selected,
      isTrue,
    );

    await tester.ensureVisible(find.byKey(const Key('reader-font-serif')));
    await tester.tap(find.byKey(const Key('reader-font-serif')));
    await tester.pumpAndSettle();
    expect(current.font, EpubReaderFont.serif);

    final slider = find.byKey(const Key('reader-slider-font-size'));
    await tester.ensureVisible(slider);
    final startingSize = current.fontSize;
    await tester.drag(slider, const Offset(80, 0));
    await tester.pumpAndSettle();
    expect(current.fontSize, greaterThan(startingSize));
  });
}
