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

    for (final block in blocksFromHtml(html)) {
      final sentences = block.split(_sentenceBreak);
      for (final sentence in sentences) {
        final normalized = normalize(sentence);
        if (normalized.isEmpty) continue;
        if (normalized.length <= maxCharacters) {
          addShort(normalized);
          continue;
        }
        // Extremely long sentences and unbroken words are hard-split safely.
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

  NarrationStatus status = NarrationStatus.idle;
  NarrationSpeed speed = NarrationSpeed.normal;
  NarrationVoice? selectedVoice;
  List<NarrationVoice> voices = <NarrationVoice>[];
  String? errorMessage;
  String chapterName = 'Current chapter';

  int get spokenParts => _index;
  int get totalParts => _utterances.length;

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

  Future<void> readChapter(String html, {String? title}) async {
    if (_closed) return;
    await initialize();
    if (!_ready || _closed) return;
    await stop();
    // Parsing very large XHTML chapters happens in a worker isolate so it
    // cannot freeze page scrolling or the loading/player controls.
    final chunks = await compute(NarrationText.chapterUtterances, html);
    if (_closed) return;
    _utterances = chunks;
    chapterName = title?.trim().isNotEmpty == true
        ? title!.trim()
        : 'Current chapter';
    _index = 0;
    if (_utterances.isEmpty) {
      status = NarrationStatus.error;
      errorMessage = 'This chapter has no readable text.';
      _emit();
      return;
    }
    unawaited(_playLoop());
  }

  Future<void> _playLoop() async {
    if (_closed || !_ready || _utterances.isEmpty) return;
    final session = ++_session;
    status = NarrationStatus.playing;
    errorMessage = null;
    _emit();
    try {
      while (!_closed && session == _session && _index < _utterances.length) {
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
      // A failed stop should not block the user's next control action.
    }
  }

  void resume() {
    if (status != NarrationStatus.paused || _closed) return;
    // Android TTS doesn't support native pause consistently. We restart
    // the interrupted short segment rather than losing the chapter position.
    unawaited(_playLoop());
  }

  Future<void> stop() async {
    if (_closed) return;
    ++_session;
    status = NarrationStatus.idle;
    _utterances = <String>[];
    _index = 0;
    _emit();
    try {
      await _engine.stop();
    } catch (_) {
      // The phone may not have an installed TTS provider.
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
