import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// EPUB reader preferences shared by all books, stored only on the device.
/// PDF pages retain their original fixed layout and are intentionally unchanged.
enum EpubReadingTheme { light, sepia, dark }

enum EpubReaderFont { system, serif, sans, monospace }

extension EpubReaderFontLabel on EpubReaderFont {
  String get label => switch (this) {
        EpubReaderFont.system => 'System',
        EpubReaderFont.serif => 'Serif',
        EpubReaderFont.sans => 'Sans',
        EpubReaderFont.monospace => 'Mono',
      };

  String? get family => switch (this) {
        EpubReaderFont.system => null,
        EpubReaderFont.serif => 'serif',
        EpubReaderFont.sans => 'sans-serif',
        EpubReaderFont.monospace => 'monospace',
      };
}

class EpubReaderPalette {
  const EpubReaderPalette({
    required this.background,
    required this.foreground,
    required this.accent,
    required this.chapterBackground,
  });

  final Color background;
  final Color foreground;
  final Color accent;
  final Color chapterBackground;
}

extension EpubReadingThemeDetails on EpubReadingTheme {
  String get label => switch (this) {
        EpubReadingTheme.light => 'Light',
        EpubReadingTheme.sepia => 'Sepia',
        EpubReadingTheme.dark => 'Dark',
      };

  EpubReaderPalette get palette => switch (this) {
        EpubReadingTheme.light => const EpubReaderPalette(
            background: Color(0xFFFFFCF7),
            foreground: Color(0xFF28232A),
            accent: Color(0xFF7155A8),
            chapterBackground: Color(0xFFEFE9F2),
          ),
        EpubReadingTheme.sepia => const EpubReaderPalette(
            background: Color(0xFFF3E5C8),
            foreground: Color(0xFF4B3728),
            accent: Color(0xFF7B5630),
            chapterBackground: Color(0xFFE8D5B1),
          ),
        EpubReadingTheme.dark => const EpubReaderPalette(
            background: Color(0xFF19191F),
            foreground: Color(0xFFECE8E3),
            accent: Color(0xFFC7B0FA),
            chapterBackground: Color(0xFF2C2934),
          ),
      };
}

@immutable
class EpubReadingSettings {
  const EpubReadingSettings({
    this.fontSize = 16,
    this.lineHeight = 1.25,
    this.horizontalMargin = 16,
    this.theme = EpubReadingTheme.light,
    this.font = EpubReaderFont.system,
  });

  static const storageKey = 'selura_epub_reading_settings_v1';

  final double fontSize;
  final double lineHeight;
  final double horizontalMargin;
  final EpubReadingTheme theme;
  final EpubReaderFont font;

  EpubReadingSettings copyWith({
    double? fontSize,
    double? lineHeight,
    double? horizontalMargin,
    EpubReadingTheme? theme,
    EpubReaderFont? font,
  }) =>
      EpubReadingSettings(
        fontSize: fontSize ?? this.fontSize,
        lineHeight: lineHeight ?? this.lineHeight,
        horizontalMargin: horizontalMargin ?? this.horizontalMargin,
        theme: theme ?? this.theme,
        font: font ?? this.font,
      );

  Map<String, Object> toJson() => {
        'fontSize': fontSize,
        'lineHeight': lineHeight,
        'horizontalMargin': horizontalMargin,
        'theme': theme.name,
        'font': font.name,
      };

  static double _number(Object? raw, double fallback, double min, double max) {
    if (raw is! num || !raw.isFinite) return fallback;
    return raw.toDouble().clamp(min, max).toDouble();
  }

  factory EpubReadingSettings.fromJson(Map<String, dynamic> json) {
    return EpubReadingSettings(
      fontSize: _number(json['fontSize'], 16, 12, 32),
      lineHeight: _number(json['lineHeight'], 1.25, 1.1, 2.0),
      horizontalMargin: _number(json['horizontalMargin'], 16, 8, 40),
      theme: EpubReadingTheme.values.firstWhere(
        (value) => value.name == json['theme'],
        orElse: () => EpubReadingTheme.light,
      ),
      font: EpubReaderFont.values.firstWhere(
        (value) => value.name == json['font'],
        orElse: () => EpubReaderFont.system,
      ),
    );
  }

  static Future<EpubReadingSettings> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(storageKey);
      if (raw == null) return const EpubReadingSettings();
      final json = jsonDecode(raw);
      if (json is Map<String, dynamic>) {
        return EpubReadingSettings.fromJson(json);
      }
    } catch (_) {
      // Corrupt settings must not prevent the book from opening.
    }
    return const EpubReadingSettings();
  }

  Future<bool> save() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.setString(storageKey, jsonEncode(toJson()));
  }

  TextStyle get textStyle => TextStyle(
        fontSize: fontSize,
        height: lineHeight,
        fontFamily: font.family,
        color: theme.palette.foreground,
      );
}

/// A modal with live preview. The containing reader rebuilds its EPUB
/// chapter widgets without recreating the EPUB controller.
class EpubReaderSettingsSheet extends StatefulWidget {
  const EpubReaderSettingsSheet({
    super.key,
    required this.settings,
    required this.onChanged,
  });

  final EpubReadingSettings settings;
  final ValueChanged<EpubReadingSettings> onChanged;

  @override
  State<EpubReaderSettingsSheet> createState() =>
      _EpubReaderSettingsSheetState();
}

class _EpubReaderSettingsSheetState
    extends State<EpubReaderSettingsSheet> {
  late EpubReadingSettings _settings;

  @override
  void initState() {
    super.initState();
    _settings = widget.settings;
  }

  void _change(EpubReadingSettings value) {
    setState(() => _settings = value);
    widget.onChanged(value);
  }

  @override
  Widget build(BuildContext context) {
    final palette = _settings.theme.palette;
    return SafeArea(
      top: false,
      child: FractionallySizedBox(
        heightFactor: 0.84,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 30),
          children: [
            Row(
              children: [
                const Icon(Icons.tune_rounded),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Reading appearance',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                TextButton(
                  onPressed: () => _change(const EpubReadingSettings()),
                  child: const Text('Reset'),
                ),
                IconButton(
                  tooltip: 'Close reading settings',
                  icon: const Icon(Icons.close_rounded),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
              decoration: BoxDecoration(
                color: palette.background,
                border: Border.all(color: palette.foreground.withValues(alpha: 0.15)),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                'The best stories are the ones that stay with you.\n'
                'Customize your reading comfort.',
                textAlign: TextAlign.start,
                style: _settings.textStyle,
              ),
            ),
            const SizedBox(height: 20),
            Text('Reading theme', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 10,
              runSpacing: 8,
              children: [
                for (final value in EpubReadingTheme.values)
                  ChoiceChip(
                    key: Key('reader-theme-${value.name}'),
                    label: Text(value.label),
                    selected: _settings.theme == value,
                    onSelected: (_) => _change(_settings.copyWith(theme: value)),
                  ),
              ],
            ),
            const SizedBox(height: 20),
            Text('Font family', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 10,
              runSpacing: 8,
              children: [
                for (final value in EpubReaderFont.values)
                  ChoiceChip(
                    key: Key('reader-font-${value.name}'),
                    label: Text(value.label),
                    selected: _settings.font == value,
                    onSelected: (_) => _change(_settings.copyWith(font: value)),
                  ),
              ],
            ),
            const SizedBox(height: 14),
            _settingSlider(
              context: context,
              name: 'Font size',
              value: _settings.fontSize,
              label: '${_settings.fontSize.round()} sp',
              min: 12,
              max: 32,
              divisions: 20,
              onChanged: (value) =>
                  _change(_settings.copyWith(fontSize: value)),
            ),
            _settingSlider(
              context: context,
              name: 'Line spacing',
              value: _settings.lineHeight,
              label: _settings.lineHeight.toStringAsFixed(1),
              min: 1.1,
              max: 2.0,
              divisions: 9,
              onChanged: (value) =>
                  _change(_settings.copyWith(lineHeight: value)),
            ),
            _settingSlider(
              context: context,
              name: 'Side margins',
              value: _settings.horizontalMargin,
              label: '${_settings.horizontalMargin.round()} px',
              min: 8,
              max: 40,
              divisions: 8,
              onChanged: (value) =>
                  _change(_settings.copyWith(horizontalMargin: value)),
            ),
            Text(
              'Preferences are saved on this device and apply to all EPUB books. '
              'PDF page layouts are unchanged.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  Widget _settingSlider({
    required BuildContext context,
    required String name,
    required double value,
    required String label,
    required double min,
    required double max,
    required int divisions,
    required ValueChanged<double> onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(name, style: Theme.of(context).textTheme.titleMedium),
            ),
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
        Slider(
          key: Key('reader-slider-${name.toLowerCase().replaceAll(' ', '-')}'),
          value: value.clamp(min, max).toDouble(),
          min: min,
          max: max,
          divisions: divisions,
          label: label,
          onChanged: onChanged,
        ),
      ],
    );
  }
}
