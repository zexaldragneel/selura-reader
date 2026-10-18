import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'file_picker.dart';
import 'manga_online_ui.dart';
import 'manga_sources.dart';
import 'mihon_backup.dart';

/// Dedicated in-app Mihon library: imported source records are not EPUB/PDF
/// files and must never be routed through the offline document renderers.
class MihonLibraryPage extends StatefulWidget {
  const MihonLibraryPage({super.key, this.initialLibrary});
  final MihonLibraryData? initialLibrary;

  @override
  State<MihonLibraryPage> createState() => _MihonLibraryPageState();
}

class _MihonLibraryPageState extends State<MihonLibraryPage> {
  final MihonBackupStore _store = const MihonBackupStore();
  final TextEditingController _search = TextEditingController();
  MihonLibraryData? _library;
  String? _error;
  String _query = '';
  int? _category;
  bool _restoring = false;

  @override
  void initState() {
    super.initState();
    if (widget.initialLibrary != null) {
      _library = widget.initialLibrary;
    } else {
      unawaited(_load());
    }
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final library = await _store.load();
      if (mounted) setState(() {
        _library = library;
        _error = null;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  void _notify(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), duration: const Duration(seconds: 6)),
    );
  }

  Future<void> _restore() async {
    if (_restoring) return;
    // Accept any extension: older Mihon/Tachiyomi backups and files renamed
    // by Android document providers may not retain the .tachibk suffix.
    final selected = await FilePicker.pickFile(type: FileType.any);
    if (selected == null) return;
    if (selected.path == null) {
      _notify('Android could not give Selura access to that backup file.');
      return;
    }
    setState(() => _restoring = true);
    try {
      final incoming = await _store.preview(File(selected.path!));
      if (!mounted) return;
      final accept = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Restore Mihon backup?'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Manga titles: ' + incoming.manga.length.toString()),
                Text('Chapters: ' + incoming.chapterCount.toString()),
                Text('Read chapters: ' + incoming.readChapters.toString()),
                Text('Categories: ' + incoming.categories.length.toString()),
                const SizedBox(height: 14),
                const Text(
                  'This restores library entries, categories, chapter '
                  'read/bookmark flags, history and page positions. '
                  'Mihon backups do NOT contain downloaded chapter images '
                  'or executable extensions. Only titles from a supported '
                  'Selura source can open online chapters here.',
                ),
                const SizedBox(height: 10),
                const Text(
                  'Your EPUB, PDF and CBZ books are not altered. '
                  'Matching Mihon manga are updated rather than duplicated. '
                  'Keep the original backup file.',
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              key: const Key('mihon-confirm-restore'),
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Restore library'),
            ),
          ],
        ),
      );
      if (accept != true) return;
      final result = await _store.restore(incoming);
      if (!mounted) return;
      await _load();
      _notify('Mihon library restored: ' + result.added.toString() +
          ' new titles, ' + result.updated.toString() +
          ' existing titles updated.');
    } catch (error) {
      _notify('Could not restore Mihon backup: ' + error.toString());
    } finally {
      if (mounted) setState(() => _restoring = false);
    }
  }

  List<MihonManga> get _visible {
    final library = _library;
    if (library == null) return [];
    final query = _query.trim().toLowerCase();
    return library.manga.where((m) =>
      (_category == null || m.categoryIds.contains(_category)) &&
      (query.isEmpty ||
        m.title.toLowerCase().contains(query) ||
        m.author.toLowerCase().contains(query) ||
        m.sourceName.toLowerCase().contains(query)))
      .toList()
      ..sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final lib = _library;
    final shown = _visible;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mihon library'),
        actions: [
          IconButton(
            key: const Key('mihon-restore-backup'),
            tooltip: 'Restore Mihon backup',
            onPressed: _restoring ? null : _restore,
            icon: const Icon(Icons.settings_backup_restore_rounded),
          ),
        ],
      ),
      body: _error != null
          ? Center(child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(_error!, textAlign: TextAlign.center),
                TextButton(onPressed: _load, child: const Text('Try again')),
              ]),
            ))
          : lib == null
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  key: const Key('mihon-restored-list'),
                  padding: const EdgeInsets.all(16),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(22),
                        color: colors.primaryContainer.withValues(alpha: .48),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Your Mihon collection',
                            style: theme.textTheme.headlineSmall?.copyWith(
                              fontWeight: FontWeight.w800,
                            )),
                          const SizedBox(height: 7),
                          Text(lib.manga.length.toString() +
                              ' manga · ' + lib.chapterCount.toString() +
                              ' chapters · ' + lib.readChapters.toString() +
                              ' read'),
                          const SizedBox(height: 7),
                          Text(
                            'Backups preserve your collection and progress. '
                            'Chapter images are fetched separately from '
                            'supported manga sources.',
                            style: theme.textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    FilledButton.icon(
                      key: const Key('mihon-import-button'),
                      onPressed: _restoring ? null : _restore,
                      icon: const Icon(Icons.file_upload_outlined),
                      label: Text(_restoring ?
                        'Validating backup…' : 'Restore Mihon .tachibk backup'),
                    ),
                    if (_restoring) ...[
                      const SizedBox(height: 10),
                      const LinearProgressIndicator(),
                    ],
                    if (lib.manga.isEmpty) ...[
                      const SizedBox(height: 24),
                      const Icon(Icons.auto_stories_outlined, size: 58),
                      const SizedBox(height: 12),
                      const Text(
                        'No Mihon manga imported yet. Open Mihon, '
                        'create a backup, and choose its .tachibk file here.',
                        textAlign: TextAlign.center,
                      ),
                    ] else ...[
                      const SizedBox(height: 17),
                      TextField(
                        key: const Key('mihon-search'),
                        controller: _search,
                        onChanged: (value) =>
                            setState(() => _query = value),
                        decoration: InputDecoration(
                          prefixIcon: const Icon(Icons.search_rounded),
                          hintText: 'Search restored titles or sources',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                      ),
                      if (lib.categories.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        SizedBox(
                          height: 48,
                          child: ListView(
                            scrollDirection: Axis.horizontal,
                            children: [
                              Padding(
                                padding: const EdgeInsets.only(right: 8),
                                child: ChoiceChip(
                                  key: const Key('mihon-all-categories'),
                                  label: const Text('All categories'),
                                  selected: _category == null,
                                  onSelected: (_) =>
                                      setState(() => _category = null),
                                ),
                              ),
                              for (final category in lib.categories)
                                Padding(
                                  padding: const EdgeInsets.only(right: 8),
                                  child: ChoiceChip(
                                    key: Key('mihon-category-' +
                                        category.id.toString()),
                                    label: Text(category.name),
                                    selected: _category == category.id,
                                    onSelected: (_) => setState(
                                      () => _category = category.id,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ],
                      const SizedBox(height: 10),
                      Text(shown.length.toString() + ' matching manga',
                        style: theme.textTheme.bodySmall),
                      const SizedBox(height: 10),
                      for (final manga in shown)
                        Card(
                          child: ListTile(
                            key: Key('mihon-title-' + manga.key),
                            leading: const Icon(Icons.menu_book_rounded),
                            title: Text(manga.title,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis),
                            subtitle: Text(
                              manga.sourceName + ' · ' +
                              manga.readCount.toString() + '/' +
                              manga.chapters.length.toString() + ' read',
                              maxLines: 2,
                            ),
                            trailing: const Icon(Icons.chevron_right_rounded),
                            onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute<void>(
                                builder: (_) => MihonMangaDetailsPage(manga: manga),
                              ),
                            ),
                          ),
                        ),
                      if (shown.isEmpty) const Padding(
                        padding: EdgeInsets.all(25),
                        child: Text('No manga match your search or category.',
                          textAlign: TextAlign.center),
                      ),
                    ],
                  ],
                ),
    );
  }
}

/// Only explicitly recognizable MangaDex identifiers are routed into Selura's
/// existing supported MangaDex reader. Unknown sources keep imported metadata.
String? mihonMangaDexId(MihonManga manga) {
  if (!manga.sourceName.toLowerCase().contains('mangadex')) return null;
  final match = RegExp(
    r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
    r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
  ).firstMatch(manga.url);
  return match?.group(0);
}

class MihonMangaDetailsPage extends StatelessWidget {
  const MihonMangaDetailsPage({super.key, required this.manga});
  final MihonManga manga;

  Future<void> _readOnline(BuildContext context, String mangaDexId) async {
    // Mihon source IDs do not automatically install any extension into Selura.
    // Only MangaDex has a reviewed in-Selura chapter and image implementation.
    final resume = manga.resumeChapter;
    final chapterId = resume == null ? null : RegExp(
      r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
      r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
    ).firstMatch(resume.url)?.group(0);
    if (chapterId != null && resume != null) {
      final prefs = await SharedPreferences.getInstance();
      final key = 'selura_mangadex_page:' + chapterId;
      if (!prefs.containsKey(key)) {
        await prefs.setInt(key, resume.lastPageRead + 1);
      }
      final resumeKey = 'selura_mangadex_resume:' + mangaDexId;
      if (!prefs.containsKey(resumeKey)) {
        await prefs.setString(resumeKey, chapterId);
      }
    }
    if (!context.mounted) return;
    await Navigator.push(
      context,
      MaterialPageRoute<void>(
        builder: (_) => MangaDetailPage(
          client: MangaDexClient(),
          manga: OnlineManga(
            id: mangaDexId,
            title: manga.title,
            description: manga.description,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final id = mihonMangaDexId(manga);
    final resumed = manga.resumeChapter;
    return Scaffold(
      appBar: AppBar(title: Text(manga.title,
        maxLines: 1, overflow: TextOverflow.ellipsis)),
      body: ListView(
        padding: const EdgeInsets.all(17),
        children: [
          Text(manga.title,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w800)),
          const SizedBox(height: 5),
          Text('Source: ' + manga.sourceName),
          if (manga.author.isNotEmpty) Text('Author: ' + manga.author),
          const SizedBox(height: 7),
          Text(manga.chapters.length.toString() + ' chapters · ' +
              manga.readCount.toString() + ' read · ' +
              manga.bookmarkedCount.toString() + ' bookmarked'),
          if (resumed != null) Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Previously reading: ' + resumed.name +
              ' · page ' + resumed.lastPageRead.toString(),
            ),
          ),
          const SizedBox(height: 13),
          if (id != null)
            FilledButton.icon(
              key: const Key('mihon-read-with-mangadex'),
              onPressed: () => _readOnline(context, id),
              icon: const Icon(Icons.chrome_reader_mode_outlined),
              label: const Text('Read with MangaDex in Selura'),
            )
          else
            const Card(
              child: Padding(
                padding: EdgeInsets.all(14),
                child: Text(
                  'Mihon backed up this manga from another source. '
                  'Your chapter history is restored below, but Selura '
                  'cannot fetch its pages until a compatible source '
                  'adapter or extension runtime is available.',
                ),
              ),
            ),
          if (manga.description.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(manga.description, maxLines: 8,
              overflow: TextOverflow.ellipsis),
          ],
          const SizedBox(height: 19),
          Text('Restored chapters', style: theme.textTheme.titleLarge),
          const SizedBox(height: 8),
          if (manga.chapters.isEmpty)
            const Text('This backup did not include saved chapter metadata.'),
          for (final chapter in manga.chapters)
            Card(
              child: ListTile(
                leading: Icon(
                  chapter.read
                      ? Icons.check_circle_rounded
                      : chapter.bookmarked
                        ? Icons.bookmark_rounded
                        : Icons.radio_button_unchecked_rounded,
                ),
                title: Text(chapter.name, maxLines: 2,
                  overflow: TextOverflow.ellipsis),
                subtitle: Text(
                  (chapter.read ? 'Read' : 'Unread') +
                  (chapter.bookmarked ? ' · Bookmarked' : '') +
                  (chapter.lastPageRead > 0
                    ? ' · Last page ' + chapter.lastPageRead.toString() : '') +
                  (chapter.lastRead > 0 ? ' · History saved' : ''),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
