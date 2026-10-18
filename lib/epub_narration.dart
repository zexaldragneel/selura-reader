import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:html/dom.dart' as dom;
import 'package:html/parser.dart' as html_parser;
import 'package:shared_preferences/shared_preferences.dart';

/// A short utterance avoids Android TextToSpeech's maximum text length.
class NarrationText {
  static const int maxUtteranceCharacters = 900;
  static final RegExp _whitespace = RegExp(r'\s+');
  static final RegExp _sentenceBreak = RegExp(r'(?<=[.!?。！？])\s+');

  static String normalize(String text) =>
      text.replaceAll(_whitespace, ' ').trim();

  /// Extracts readable body text only. Never sends an EPUB to an external API.
  static List<String> blocksFromHtml(String html) {
    final document = html_parser.parse(html);
    for (final node in document.querySelectorAll(
      'script, style, nav, aside, svg, noscript',
    )) {
      node.remove();
    }
    final body = document.body;
    if (body == null) return <String>[];

    final accepted = <dom.Element>{};
    final blocks = <String>[];
    for (final element in body.querySelectorAll(
      'h1, h2, h3, h4, h5, h6, p, li, blockquote, pre',
    )) {
      // Example: <li><p>Text</p></li> must not be spoken twice.
      var parent = element.parentNode;
      var alreadyNested = false;
      while (parent != null) {
        if (parent is dom.Element && accepted.contains(parent)) {
          alreadyNested = true;
          break;
        }
        parent = parent.parentNode;
      }
      if (alreadyNested) continue;
      final text = normalize(element.text);
      if (text.isEmpty) continue;
      accepted.add(element);
      blocks.add(text);
    }
    if (blocks.isNotEmpty) return blocks;
    final fallback = normalize(body.text);
    return fallback.isEmpty ? <String>[] : <String>[fallback];
  }

  static List<String> chapterUtterances(String html, {
    int maxCharacters = maxUtteranceCharacters,
  }) => _chunkBlocks(
        blocksFromHtml(html),
        maxCharacters: maxCharacters,
      );

  /// Segment boundaries stay within each paragraph, allowing exact
  /// paragraph starts and accessible previous/next paragraph controls.
  static NarrationChapterPlan chapterPlan(String html) {
    final paragraphs = blocksFromHtml(html);
    final starts = <int>[];
    final utterances = <String>[];
    final segmentParagraphs = <int>[];

    for (var index = 0; index < paragraphs.length; index++) {
      starts.add(utterances.length);
      final chunks = _chunkBlocks(<String>[paragraphs[index]]);
      utterances.addAll(chunks);
      segmentParagraphs.addAll(List<int>.filled(chunks.length, index));
    }
    return NarrationChapterPlan(
      paragraphs: paragraphs,
      utterances: utterances,
      paragraphStarts: starts,
      segmentParagraphs: segmentParagraphs,
    );
  }

  static List<String> _chunkBlocks(
    List<String> blocks, {
    int maxCharacters = maxUtteranceCharacters,
  }) {
    if (maxCharacters < 80) {
      throw ArgumentError.value(maxCharacters, 'maxCharacters');
    }
    final utterances = <String>[];
    final buffer = StringBuffer();

    void flush() {
      if (buffer.isEmpty) return;
      utterances.add(buffer.toString());
      buffer.clear();
    }

    void addShort(String phrase) {
      if (phrase.isEmpty) return;
      if (buffer.length + phrase.length + (buffer.isEmpty ? 0 : 1) >
          maxCharacters) {
        flush();
      }
      if (buffer.isNotEmpty) buffer.write(' ');
      buffer.write(phrase);
    }

    for (final block in blocks) {
      final sentences = block.split(_sentenceBreak);
      for (final sentence in sentences) {
        final normalized = normalize(sentence);
        if (normalized.isEmpty) continue;
        if (normalized.length <= maxCharacters) {
          addShort(normalized);
          continue;
        }
        // Oversized sentences/words are split to fit Android TTS limits.
        final words = normalized.split(' ');
        var section = '';
        for (final word in words) {
          if (word.length > maxCharacters) {
            if (section.isNotEmpty) {
              addShort(section);
              section = '';
            }
            for (var index = 0; index < word.length; index += maxCharacters) {
              addShort(word.substring(
                index,
                index + maxCharacters > word.length
                    ? word.length
                    : index + maxCharacters,
              ));
            }
            continue;
          }
          if (section.isEmpty) {
            section = word;
          } else if (section.length + 1 + word.length <= maxCharacters) {
            section = '$section $word';
          } else {
            addShort(section);
            section = word;
          }
        }
        if (section.isNotEmpty) addShort(section);
      }
    }
    flush();
    return utterances;
  }
}

@immutable
class NarrationChapterPlan {
  const NarrationChapterPlan({
    required this.paragraphs,
    required this.utterances,
    required this.paragraphStarts,
    required this.segmentParagraphs,
  });

  final List<String> paragraphs;
  final List<String> utterances;
  final List<int> paragraphStarts;
  final List<int> segmentParagraphs;

  bool get isEmpty => utterances.isEmpty;

  int segmentForParagraph(int index) {
    if (paragraphs.isEmpty || index < 0 || index >= paragraphs.length) {
      throw RangeError.index(index, paragraphs, 'paragraph');
    }
    return paragraphStarts[index];
  }
}

enum NarrationStatus { idle, loading, playing, paused, finished, error }

enum NarrationSpeed {
  slow(0.75, '0.75×'),
  normal(1.0, '1×'),
  fast(1.25, '1.25×'),
  faster(1.5, '1.5×');

  const NarrationSpeed(this.multiplier, this.label);
  final double multiplier;
  final String label;

  // flutter_tts maps a rate of 0.5 to normal Android speech speed.
  double get engineRate => multiplier * 0.5;
}

class NarrationVoice {
  const NarrationVoice({required this.name, required this.locale});

  final String name;
  final String locale;

  String get id => '$locale::$name';
  String get label => '$name ($locale)';
}

/// Deliberately injectable so sequence/pause/stop logic is testable without
/// a phone or a platform channel.
abstract class NarrationEngine {
  Future<void> initialize();
  Future<void> setRate(double rate);
  Future<void> selectVoice(NarrationVoice voice);
  Future<List<NarrationVoice>> installedVoices();
  Future<void> speak(String text);
  Future<void> stop();
}

class AndroidNarrationEngine implements NarrationEngine {
  AndroidNarrationEngine() : _tts = FlutterTts();

  final FlutterTts _tts;

  @override
  Future<void> initialize() async {
    // Resolve speak only when an utterance finishes, allowing bounded,
    // consecutive chunks with functional pause/resume/stop.
    await _tts.awaitSpeakCompletion(true);
  }

  @override
  Future<void> setRate(double rate) async {
    await _tts.setSpeechRate(rate);
  }

  @override
  Future<void> selectVoice(NarrationVoice voice) async {
    await _tts.setVoice({'name': voice.name, 'locale': voice.locale});
  }

  @override
  Future<List<NarrationVoice>> installedVoices() async {
    final raw = await _tts.getVoices;
    if (raw is! List) return <NarrationVoice>[];
    final voices = <NarrationVoice>[];
    final seen = <String>{};
    for (final value in raw) {
      if (value is! Map) continue;
      final name = value['name']?.toString();
      final locale = value['locale']?.toString();
      final network = value['network_required']?.toString().toLowerCase();
      if (name == null || name.isEmpty || locale == null || locale.isEmpty ||
          network == 'true') {
        continue;
      }
      final voice = NarrationVoice(name: name, locale: locale);
      if (seen.add(voice.id)) voices.add(voice);
    }
    voices.sort((a, b) => a.label.compareTo(b.label));
    return voices;
  }

  @override
  Future<void> speak(String text) async {
    final result = await _tts.speak(text, focus: true);
    if (result == 0) throw StateError('Android speech engine rejected text');
  }

  @override
  Future<void> stop() async {
    await _tts.stop();
  }
}

/// Playback state belongs to one open EPUB, never the global bookshelf.
/// It stops speech when leaving the reader; no network or cloud accounts.
class EpubNarrationController extends ChangeNotifier {
  EpubNarrationController({NarrationEngine? engine})
      : _engine = engine ?? AndroidNarrationEngine();

  static const speedKey = 'selura_narration_speed_v1';
  static const voiceKey = 'selura_narration_voice_v1';

  final NarrationEngine _engine;
  Future<void>? _initFuture;
  bool _ready = false;
  bool _closed = false;
  int _session = 0;
  int _index = 0;
  List<String> _utterances = <String>[];
  NarrationChapterPlan? _plan;
  int _selectedParagraph = 0;

  NarrationStatus status = NarrationStatus.idle;
  NarrationSpeed speed = NarrationSpeed.normal;
  NarrationVoice? selectedVoice;
  List<NarrationVoice> voices = <NarrationVoice>[];
  String? errorMessage;
  String chapterName = 'Current chapter';

  int get spokenParts => _index;
  int get totalParts => _utterances.length;
  List<String> get paragraphs => _plan?.paragraphs ?? const <String>[];
  int get currentParagraph {
    final plan = _plan;
    if (plan == null || plan.isEmpty) return 0;
    if (status == NarrationStatus.playing ||
        status == NarrationStatus.paused ||
        status == NarrationStatus.finished) {
      final segment = _index >= plan.segmentParagraphs.length
          ? plan.segmentParagraphs.length - 1
          : _index;
      return plan.segmentParagraphs[segment];
    }
    return _selectedParagraph;
  }

  void _emit() {
    if (!_closed) notifyListeners();
  }

  Future<void> initialize() => _initFuture ??= _initialize();

  Future<void> _initialize() async {
    if (_ready || _closed) return;
    status = NarrationStatus.loading;
    _emit();
    try {
      final prefs = await SharedPreferences.getInstance();
      final storedSpeed = prefs.getInt(speedKey);
      if (storedSpeed != null &&
          storedSpeed >= 0 &&
          storedSpeed < NarrationSpeed.values.length) {
        speed = NarrationSpeed.values[storedSpeed];
      }
      await _engine.initialize();
      await _engine.setRate(speed.engineRate);
      try {
        voices = await _engine.installedVoices();
      } catch (_) {
        // Some Android TTS engines cannot enumerate voices.
        voices = <NarrationVoice>[];
      }
      final storedVoice = prefs.getString(voiceKey);
      if (storedVoice != null) {
        for (final voice in voices) {
          if (voice.id == storedVoice) {
            await _engine.selectVoice(voice);
            selectedVoice = voice;
            break;
          }
        }
      }
      _ready = true;
      if (_closed) return;
      status = NarrationStatus.idle;
      errorMessage = null;
    } catch (_) {
      status = NarrationStatus.error;
      errorMessage = 'No Android text-to-speech voice is available. '
          'Check Text-to-speech output in your phone settings.';
    }
    _emit();
  }

  /// Decode the active chapter in an isolate once; reselecting a paragraph
  /// uses the resulting local speech plan without parsing XHTML again.
  Future<void> prepareChapter(String html, {String? title}) async {
    if (_closed) return;
    await initialize();
    if (!_ready || _closed) return;

    final generation = ++_session;
    status = NarrationStatus.loading;
    errorMessage = null;
    _emit();

    try {
      await _engine.stop();
      final plan = await compute(NarrationText.chapterPlan, html);
      if (_closed || generation != _session) return;
      _plan = plan;
      _utterances = plan.utterances;
      chapterName = title?.trim().isNotEmpty == true
          ? title!.trim()
          : 'Current chapter';
      _selectedParagraph = 0;
      _index = 0;
      if (plan.isEmpty) {
        status = NarrationStatus.error;
        errorMessage = 'This chapter has no readable text.';
      } else {
        status = NarrationStatus.idle;
      }
    } catch (_) {
      if (_closed || generation != _session) return;
      status = NarrationStatus.error;
      errorMessage = 'Selura could not prepare this chapter for narration.';
    }
    _emit();
  }

  /// Keeps the original one-tap chapter narration workflow compatible.
  Future<void> readChapter(String html, {String? title}) async {
    await prepareChapter(html, title: title);
    if (_closed || status != NarrationStatus.idle) return;
    await playFromParagraph(0);
  }

  Future<void> playFromParagraph(int paragraph) async {
    final plan = _plan;
    if (_closed || !_ready || plan == null || plan.isEmpty ||
        paragraph < 0 || paragraph >= plan.paragraphs.length) {
      return;
    }

    final generation = ++_session;
    _selectedParagraph = paragraph;
    _index = plan.segmentForParagraph(paragraph);
    status = NarrationStatus.loading;
    errorMessage = null;
    _emit();
    try {
      // Android TTS lacks reliable native seeking; a short current utterance
      // is interrupted and the selected paragraph starts from its beginning.
      await _engine.stop();
      if (_closed || generation != _session) return;
      unawaited(_playLoop());
    } catch (_) {
      if (_closed || generation != _session) return;
      status = NarrationStatus.error;
      errorMessage = 'Could not start narration from that paragraph.';
      _emit();
    }
  }

  Future<void> skipParagraph(int offset) async {
    final target = currentParagraph + offset;
    if (target < 0 || target >= paragraphs.length) return;
    await playFromParagraph(target);
  }

  Future<void> _playLoop() async {
    if (_closed || !_ready || _utterances.isEmpty) return;
    final session = ++_session;
    status = NarrationStatus.playing;
    errorMessage = null;
    _emit();
    try {
      while (!_closed && session == _session && _index < _utterances.length) {
        final plan = _plan;
        if (plan != null) {
          _selectedParagraph = plan.segmentParagraphs[_index];
          _emit();
        }
        await _engine.speak(_utterances[_index]);
        if (_closed || session != _session) return;
        _index += 1;
        _emit();
      }
      if (!_closed && session == _session) {
        status = NarrationStatus.finished;
        _emit();
      }
    } catch (_) {
      if (!_closed && session == _session) {
        status = NarrationStatus.error;
        errorMessage = 'Speech playback stopped. Check the Android voice '
            'engine or choose an installed offline voice.';
        _emit();
      }
    }
  }

  Future<void> pause() async {
    if (status != NarrationStatus.playing || _closed) return;
    ++_session;
    status = NarrationStatus.paused;
    _emit();
    try {
      await _engine.stop();
    } catch (_) {
      // Native engines can complete an utterance while the pause is requested.
    }
  }

  void resume() {
    if (status != NarrationStatus.paused || _closed) return;
    // Resume the interrupted bounded segment; does not restart the chapter.
    unawaited(_playLoop());
  }

  Future<void> stop() async {
    if (_closed) return;
    ++_session;
    status = NarrationStatus.idle;
    final plan = _plan;
    _index = plan != null && !plan.isEmpty
        ? plan.segmentForParagraph(_selectedParagraph)
        : 0;
    _emit();
    try {
      await _engine.stop();
    } catch (_) {
      // A missing phone TTS provider must not block book reading.
    }
  }

  Future<void> setSpeed(NarrationSpeed next) async {
    if (_closed) return;
    speed = next;
    _emit();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(speedKey, next.index);
      if (_ready) await _engine.setRate(next.engineRate);
    } catch (_) {
      errorMessage = 'Could not save narration speed.';
      _emit();
    }
  }

  Future<void> setVoice(NarrationVoice? voice) async {
    if (_closed) return;
    try {
      if (voice != null) {
        await _engine.selectVoice(voice);
      }
      selectedVoice = voice;
      final prefs = await SharedPreferences.getInstance();
      if (voice == null) {
        await prefs.remove(voiceKey);
      } else {
        await prefs.setString(voiceKey, voice.id);
      }
      _emit();
    } catch (_) {
      errorMessage = 'Could not select that Android voice.';
      _emit();
    }
  }

  /// Releases the native speech engine on page disposal.
  void close() {
    if (_closed) return;
    ++_session;
    _closed = true;
    unawaited(_engine.stop().catchError((Object _) {}));
    super.dispose();
  }
}
