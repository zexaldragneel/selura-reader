import 'package:flutter/material.dart';

import 'epub_narration.dart';

/// Reader-only controls. Speech never leaves the phone's Android TTS service.
class EpubNarrationSheet extends StatefulWidget {
  const EpubNarrationSheet({
    super.key,
    required this.narration,
    required this.chapterHtml,
    required this.chapterTitle,
  });

  final EpubNarrationController narration;
  final String? chapterHtml;
  final String? chapterTitle;

  @override
  State<EpubNarrationSheet> createState() => _EpubNarrationSheetState();
}

class _EpubNarrationSheetState extends State<EpubNarrationSheet> {
  @override
  void initState() {
    super.initState();
    final html = widget.chapterHtml;
    if (html != null && html.trim().isNotEmpty) {
      widget.narration.prepareChapter(html, title: widget.chapterTitle);
    } else {
      widget.narration.initialize();
    }
  }

  Future<void> _chooseStartingParagraph() async {
    final player = widget.narration;
    if (player.paragraphs.isEmpty) return;
    final selected = await showModalBottomSheet<int>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        top: false,
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * 0.76,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                child: Row(
                  children: [
                    const Icon(Icons.format_list_numbered_rounded),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Start reading from…',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Close paragraph picker',
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: ListView.builder(
                  key: const Key('tts-paragraph-picker'),
                  itemCount: player.paragraphs.length,
                  itemBuilder: (context, index) {
                    final selectedNow = index == player.currentParagraph;
                    return ListTile(
                      key: Key('tts-paragraph-$index'),
                      leading: CircleAvatar(
                        radius: 18,
                        child: Text('${index + 1}'),
                      ),
                      title: Text(
                        player.paragraphs[index],
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                      selected: selectedNow,
                      trailing: selectedNow
                          ? const Icon(Icons.volume_up_rounded)
                          : const Icon(Icons.play_arrow_rounded),
                      onTap: () => Navigator.of(context).pop(index),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (selected != null && mounted) {
      await player.playFromParagraph(selected);
    }
  }

  Future<void> _chooseVoice() async {
    final voices = widget.narration.voices;
    if (voices.isEmpty) return;
    final selected = await showModalBottomSheet<NarrationVoice>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        top: false,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.58,
          ),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 20),
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 12,
                ),
                child: Text(
                  'Installed offline voices',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              for (final voice in voices)
                ListTile(
                  title: Text(
                    voice.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  subtitle: Text(voice.locale),
                  leading: const Icon(Icons.record_voice_over_rounded),
                  trailing: widget.narration.selectedVoice?.id == voice.id
                      ? const Icon(Icons.check_circle_rounded)
                      : null,
                  onTap: () => Navigator.of(context).pop(voice),
                ),
            ],
          ),
        ),
      ),
    );
    if (selected == null) return;
    await widget.narration.stop();
    await widget.narration.setVoice(selected);
  }

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme;
    return SafeArea(
      top: false,
      child: AnimatedBuilder(
        animation: widget.narration,
        builder: (context, _) {
          final player = widget.narration;
          final isPlaying = player.status == NarrationStatus.playing;
          final isPaused = player.status == NarrationStatus.paused;
          final busy = player.status == NarrationStatus.loading;
          final html = widget.chapterHtml;
          final hasChapter = html != null && html.trim().isNotEmpty;

          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 30),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Icon(Icons.graphic_eq_rounded, color: color.primary),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Listen to this chapter',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Close narration',
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        color.primaryContainer,
                        color.tertiaryContainer,
                      ],
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.headphones_rounded,
                        size: 36,
                        color: color.onPrimaryContainer,
                      ),
                      const SizedBox(height: 14),
                      Text(
                        widget.chapterTitle?.trim().isNotEmpty == true
                            ? widget.chapterTitle!
                            : 'Your current chapter',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: color.onPrimaryContainer,
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        switch (player.status) {
                          NarrationStatus.playing => 'Playing with Android voice',
                          NarrationStatus.paused => 'Paused',
                          NarrationStatus.finished => 'Chapter completed',
                          NarrationStatus.loading => 'Preparing offline voice…',
                          NarrationStatus.error => 'Narration unavailable',
                          NarrationStatus.idle => 'Ready to read aloud',
                        },
                        style: TextStyle(
                          color: color.onPrimaryContainer.withValues(
                            alpha: 0.8,
                          ),
                        ),
                      ),
                      if (player.totalParts > 0) ...[
                        const SizedBox(height: 16),
                        LinearProgressIndicator(
                          value: player.spokenParts / player.totalParts,
                          borderRadius: BorderRadius.circular(99),
                          minHeight: 5,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Audio segment ${player.spokenParts} / ${player.totalParts}',
                          style: TextStyle(
                            color: color.onPrimaryContainer,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (player.errorMessage != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    player.errorMessage!,
                    style: TextStyle(color: color.error),
                  ),
                ],
                const SizedBox(height: 18),
                OutlinedButton.icon(
                  key: const Key('tts-choose-paragraph'),
                  onPressed: !busy && player.paragraphs.isNotEmpty
                      ? _chooseStartingParagraph
                      : null,
                  icon: const Icon(Icons.format_list_numbered_rounded),
                  label: Text(
                    player.paragraphs.isEmpty
                        ? 'Preparing paragraphs…'
                        : 'Paragraph ${player.currentParagraph + 1} of '
                            '${player.paragraphs.length} · Choose start',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size.fromHeight(48),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton.outlined(
                      key: const Key('tts-previous-paragraph'),
                      tooltip: 'Previous paragraph',
                      onPressed: !busy &&
                              player.paragraphs.isNotEmpty &&
                              player.currentParagraph > 0
                          ? () => player.skipParagraph(-1)
                          : null,
                      icon: const Icon(Icons.skip_previous_rounded),
                      iconSize: 26,
                    ),
                    const SizedBox(width: 8),
                    IconButton.outlined(
                      tooltip: 'Stop narration',
                      onPressed: isPlaying || isPaused
                          ? () => player.stop()
                          : null,
                      icon: const Icon(Icons.stop_rounded),
                      iconSize: 27,
                    ),
                    const SizedBox(width: 22),
                    FilledButton.icon(
                      key: const Key('narration-play-pause'),
                      onPressed: busy || (!hasChapter && !isPaused)
                          ? null
                          : () {
                              if (isPlaying) {
                                player.pause();
                              } else if (isPaused) {
                                player.resume();
                              } else if (player.paragraphs.isNotEmpty) {
                                player.playFromParagraph(
                                  player.currentParagraph,
                                );
                              } else {
                                player.readChapter(
                                  html!,
                                  title: widget.chapterTitle,
                                );
                              }
                            },
                      icon: Icon(
                        isPlaying
                            ? Icons.pause_rounded
                            : Icons.play_arrow_rounded,
                        size: 28,
                      ),
                      label: Text(
                        isPlaying
                            ? 'Pause'
                            : isPaused
                                ? 'Resume'
                                : player.status == NarrationStatus.finished
                                    ? 'Read again'
                                    : 'Read aloud',
                      ),
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 16,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.outlined(
                      key: const Key('tts-next-paragraph'),
                      tooltip: 'Next paragraph',
                      onPressed: !busy &&
                              player.paragraphs.isNotEmpty &&
                              player.currentParagraph <
                                  player.paragraphs.length - 1
                          ? () => player.skipParagraph(1)
                          : null,
                      icon: const Icon(Icons.skip_next_rounded),
                      iconSize: 26,
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Text(
                  'Narration speed',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 7,
                  children: [
                    for (final speed in NarrationSpeed.values)
                      ChoiceChip(
                        key: Key('tts-speed-${speed.name}'),
                        label: Text(speed.label),
                        selected: player.speed == speed,
                        onSelected: busy
                            ? null
                            : (_) => player.setSpeed(speed),
                      ),
                  ],
                ),
                const SizedBox(height: 20),
                Text(
                  'Voice',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: player.voices.isEmpty ? null : _chooseVoice,
                  icon: const Icon(Icons.record_voice_over_rounded),
                  label: Text(
                    player.selectedVoice?.label ??
                        'Android system voice',
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Narration uses the voices installed on your phone. '
                  'For offline listening, install an offline voice in Android '
                  'Text-to-speech settings. Choose any chapter paragraph '
                  'or use previous/next to change the starting point. '
                  'Pause/resume restarts only an interrupted short segment. '
                  'Narration stops when you close the reader.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
