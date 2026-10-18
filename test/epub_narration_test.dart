import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:selura_reader/epub_narration.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _FakeNarrationEngine implements NarrationEngine {
  final List<String> spoken = <String>[];
  final List<Completer<void>> pending = <Completer<void>>[];
  final List<double> speeds = <double>[];
  int stops = 0;
  bool blockSpeech = false;
  NarrationVoice? voice;

  @override
  Future<void> initialize() async {}

  @override
  Future<void> setRate(double rate) async => speeds.add(rate);

  @override
  Future<void> selectVoice(NarrationVoice next) async => voice = next;

  @override
  Future<List<NarrationVoice>> installedVoices() async => [
        const NarrationVoice(name: 'Local English', locale: 'en-US'),
      ];

  @override
  Future<void> speak(String text) async {
    spoken.add(text);
    if (blockSpeech) {
      final gate = Completer<void>();
      pending.add(gate);
      await gate.future;
    }
  }

  @override
  Future<void> stop() async {
    stops++;
    for (final gate in pending) {
      if (!gate.isCompleted) gate.complete();
    }
  }
}

Future<void> _pumpMicrotasks() async {
  await Future<void>.delayed(const Duration(milliseconds: 1));
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  test('extracts readable EPUB text without HTML, scripts or duplicated list text',
      () {
    const html = '''
<html><head><title>Ignored</title><style>hidden { display:none; }</style></head>
<body><h1>Chapter 1</h1><p>Hello <strong>beautiful</strong> world.</p>
<ul><li><p>One nested item.</p></li></ul>
<script>alert('not spoken')</script><p>Second paragraph.</p></body></html>
''';
    final blocks = NarrationText.blocksFromHtml(html);
    expect(blocks, [
      'Chapter 1',
      'Hello beautiful world.',
      'One nested item.',
      'Second paragraph.',
    ]);
  });

  test('splits very long EPUB chapters below Android speech size limits', () {
    final html = '<body><p>${List.filled(800, 'This is a sentence.').join(' ')}</p></body>';
    final segments = NarrationText.chapterUtterances(html);
    expect(segments.length, greaterThan(10));
    expect(segments.every(
      (segment) => segment.isNotEmpty &&
          segment.length <= NarrationText.maxUtteranceCharacters,
    ), isTrue);
    expect(segments.join(' '), contains('This is a sentence.'));
  });

  test('supports extremely long unbroken words and empty chapters', () {
    final giant = List.filled(2200, 'x').join();
    final segments = NarrationText.chapterUtterances('<p>$giant</p>');
    expect(segments.length, 3);
    expect(segments.map((text) => text.length), [900, 900, 400]);
    expect(NarrationText.chapterUtterances('<body><img src="x"/></body>'), isEmpty);
  });

  test('begins, pauses, resumes and stops real narration segments', () async {
    final engine = _FakeNarrationEngine()..blockSpeech = true;
    final player = EpubNarrationController(engine: engine);
    await player.readChapter(
      '<body><p>${List.filled(110, 'We read together.').join(' ')}</p></body>',
      title: 'A long chapter',
    );
    await _pumpMicrotasks();

    expect(player.status, NarrationStatus.playing);
    expect(engine.spoken, hasLength(1));
    expect(player.totalParts, greaterThan(1));

    await player.pause();
    expect(player.status, NarrationStatus.paused);
    final positionWhenPaused = player.spokenParts;
    player.resume();
    await _pumpMicrotasks();
    expect(player.status, NarrationStatus.playing);
    expect(player.spokenParts, positionWhenPaused);
    expect(engine.spoken, hasLength(2));

    await player.stop();
    await _pumpMicrotasks();
    expect(player.status, NarrationStatus.idle);
    expect(player.totalParts, greaterThan(1));
    // Stop retains the parsed chapter so playback can restart without
    // reparsing large XHTML; the current paragraph remains selected.
    expect(player.spokenParts, 0);
    expect(engine.stops, greaterThan(0));

    player.close();
  });

  test('stores narration speed and selected local voice', () async {
    final engine = _FakeNarrationEngine();
    final player = EpubNarrationController(engine: engine);
    await player.initialize();
    expect(player.status, NarrationStatus.idle);
    expect(player.voices, hasLength(1));

    await player.setSpeed(NarrationSpeed.fast);
    await player.setVoice(player.voices.single);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getInt(EpubNarrationController.speedKey),
        NarrationSpeed.fast.index);
    expect(prefs.getString(EpubNarrationController.voiceKey),
        'en-US::Local English');
    expect(engine.speeds.last, NarrationSpeed.fast.engineRate);
    expect(engine.voice?.name, 'Local English');

    player.close();
  });

  test('loading an empty chapter shows useful error without speaking', () async {
    final engine = _FakeNarrationEngine();
    final player = EpubNarrationController(engine: engine);
    await player.readChapter('<body><img src="cover.png"/></body>');
    expect(player.status, NarrationStatus.error);
    expect(player.errorMessage, contains('no readable text'));
    expect(engine.spoken, isEmpty);
    player.close();
  });
  test('paragraph plan preserves individual speech boundaries and offsets', () {
    const html = '''
      <html><body><h2>Chapter</h2><p>First paragraph.</p>
      <p>Second paragraph has two sentences. Keep reading.</p>
      <p>Final paragraph.</p></body></html>
    ''';
    final plan = NarrationText.chapterPlan(html);
    expect(plan.paragraphs, hasLength(4));
    expect(plan.paragraphs[2], contains('Second paragraph'));
    expect(plan.paragraphStarts.length, 4);
    for (var index = 0; index < plan.paragraphs.length; index++) {
      final first = plan.segmentForParagraph(index);
      final last = index == plan.paragraphs.length - 1
          ? plan.utterances.length
          : plan.segmentForParagraph(index + 1);
      expect(first, lessThan(last));
      for (var part = first; part < last; part++) {
        expect(plan.segmentParagraphs[part], index);
        expect(plan.utterances[part], isNotEmpty);
        expect(plan.utterances[part].length,
            lessThanOrEqualTo(NarrationText.maxUtteranceCharacters));
      }
    }
    expect(() => plan.segmentForParagraph(-1), throwsRangeError);
    expect(() => plan.segmentForParagraph(4), throwsRangeError);
  });

  test('seeking to a chosen paragraph skips prior speech text', () async {
    final engine = _FakeNarrationEngine()..blockSpeech = true;
    final player = EpubNarrationController(engine: engine);
    await player.prepareChapter(
      '<p>Start here.</p><p>Jump straight to this passage.</p>'
      '<p>And finish here.</p>',
      title: 'Chapter 2',
    );
    expect(player.status, NarrationStatus.idle);
    expect(player.paragraphs, hasLength(3));
    expect(engine.spoken, isEmpty);

    await player.playFromParagraph(1);
    await _pumpMicrotasks();
    expect(player.currentParagraph, 1);
    expect(engine.spoken, ['Jump straight to this passage.']);

    await player.skipParagraph(1);
    await _pumpMicrotasks();
    expect(player.currentParagraph, 2);
    expect(engine.spoken.last, 'And finish here.');

    await player.pause();
    player.resume();
    await _pumpMicrotasks();
    expect(engine.spoken.last, 'And finish here.');

    await player.stop();
    expect(player.paragraphs, hasLength(3));
    expect(player.currentParagraph, 2);

    // Stopped narration still has its cached plan.
    await player.playFromParagraph(0);
    await _pumpMicrotasks();
    expect(engine.spoken.last, 'Start here.');
    player.close();
  });

  test('invalid paragraph seeks are safely ignored', () async {
    final engine = _FakeNarrationEngine();
    final player = EpubNarrationController(engine: engine);
    await player.prepareChapter('<p>Only paragraph.</p>');
    await player.playFromParagraph(-1);
    await player.playFromParagraph(99);
    await player.skipParagraph(-1);
    await player.skipParagraph(1);
    expect(engine.spoken, isEmpty);
    expect(player.currentParagraph, 0);
    player.close();
  });

  test('long paragraphs remain seekable and resume inside their chunk', () async {
    final engine = _FakeNarrationEngine()..blockSpeech = true;
    final player = EpubNarrationController(engine: engine);
    final longParagraph = List.filled(120, 'Read this sentence.').join(' ');
    await player.prepareChapter(
      '<p>Introduction.</p><p>$longParagraph</p><p>The end.</p>',
    );
    expect(player.paragraphs.length, 3);
    await player.playFromParagraph(1);
    await _pumpMicrotasks();
    expect(player.currentParagraph, 1);
    expect(engine.spoken.first, startsWith('Read this sentence.'));
    expect(engine.spoken.first.length,
        lessThanOrEqualTo(NarrationText.maxUtteranceCharacters));
    await player.pause();
    player.resume();
    await _pumpMicrotasks();
    expect(engine.spoken.last, engine.spoken.first);
    player.close();
  });

}
