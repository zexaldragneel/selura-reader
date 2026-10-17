import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// An offline, per-book reading location. EPUB locations are CFIs; PDF
/// locations are one-based page numbers serialized as strings.
class ReaderBookmark {
  const ReaderBookmark({
    required this.id,
    required this.location,
    required this.label,
    required this.createdAt,
  });

  final String id;
  final String location;
  final String label;
  final int createdAt;

  Map<String, Object> toJson() => {
        'id': id,
        'location': location,
        'label': label,
        'createdAt': createdAt,
      };

  factory ReaderBookmark.fromJson(Map<String, dynamic> json) {
    final id = json['id'] as String;
    final location = json['location'] as String;
    final label = json['label'] as String;
    final createdAt = json['createdAt'] as int;
    if (id.isEmpty || location.isEmpty || createdAt < 0) {
      throw const FormatException('Invalid bookmark');
    }
    return ReaderBookmark(
      id: id,
      location: location,
      label: label,
      createdAt: createdAt,
    );
  }
}

class BookmarkStore {
  const BookmarkStore();

  static const int maxPerBook = 500;

  String _key(String bookPath) => 'selura_bookmarks_v1:$bookPath';

  Future<List<ReaderBookmark>> load(String bookPath) async {
    final prefs = await SharedPreferences.getInstance();
    final rows = prefs.getStringList(_key(bookPath)) ?? <String>[];
    final bookmarks = <ReaderBookmark>[];
    for (final row in rows) {
      try {
        final data = jsonDecode(row);
        if (data is Map<String, dynamic>) {
          bookmarks.add(ReaderBookmark.fromJson(data));
        }
      } catch (_) {
        // A corrupt record should not hide healthy bookmarks or affect reading.
      }
    }
    bookmarks.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return bookmarks;
  }

  /// Returns false for duplicate locations. Never replaces an existing
  /// bookmark silently. Throws StateError at the local storage limit.
  Future<bool> add({
    required String bookPath,
    required String location,
    required String label,
  }) async {
    if (location.isEmpty) return false;
    final bookmarks = await load(bookPath);
    if (bookmarks.any((item) => item.location == location)) return false;
    if (bookmarks.length >= maxPerBook) {
      throw StateError('Maximum number of bookmarks reached');
    }
    final now = DateTime.now().microsecondsSinceEpoch;
    final newBookmark = ReaderBookmark(
      id: '$now-${bookmarks.length}',
      location: location,
      label: label,
      createdAt: now,
    );
    final prefs = await SharedPreferences.getInstance();
    bookmarks.insert(0, newBookmark);
    return prefs.setStringList(
      _key(bookPath),
      bookmarks.map((bookmark) => jsonEncode(bookmark.toJson())).toList(),
    );
  }

  Future<bool> delete({
    required String bookPath,
    required String bookmarkId,
  }) async {
    final bookmarks = await load(bookPath);
    final remaining = bookmarks.where((item) => item.id != bookmarkId).toList();
    if (remaining.length == bookmarks.length) return false;
    final prefs = await SharedPreferences.getInstance();
    return prefs.setStringList(
      _key(bookPath),
      remaining.map((bookmark) => jsonEncode(bookmark.toJson())).toList(),
    );
  }
}

/// Shared bottom sheet for EPUB and PDF. The caller owns page navigation.
class ReaderBookmarksSheet extends StatefulWidget {
  const ReaderBookmarksSheet({
    super.key,
    required this.bookPath,
    required this.onGoToBookmark,
  });

  final String bookPath;
  final ValueChanged<ReaderBookmark> onGoToBookmark;

  @override
  State<ReaderBookmarksSheet> createState() => _ReaderBookmarksSheetState();
}

class _ReaderBookmarksSheetState extends State<ReaderBookmarksSheet> {
  final BookmarkStore _store = const BookmarkStore();
  List<ReaderBookmark> _bookmarks = <ReaderBookmark>[];
  bool _loading = true;
  bool _deleting = false;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    final bookmarks = await _store.load(widget.bookPath);
    if (!mounted) return;
    setState(() {
      _bookmarks = bookmarks;
      _loading = false;
    });
  }

  Future<void> _delete(ReaderBookmark bookmark) async {
    if (_deleting) return;
    setState(() => _deleting = true);
    try {
      await _store.delete(
        bookPath: widget.bookPath,
        bookmarkId: bookmark.id,
      );
      await _refresh();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not remove bookmark')),
        );
      }
    } finally {
      if (mounted) setState(() => _deleting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.bookmarks_rounded, color: scheme.primary),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Bookmarks',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                IconButton(
                  tooltip: 'Close bookmarks',
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close_rounded),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ConstrainedBox(
              constraints: BoxConstraints(
                maxHeight: MediaQuery.sizeOf(context).height * 0.58,
                minHeight: 136,
              ),
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _bookmarks.isEmpty
                      ? Center(
                          child: Text(
                            'No bookmarks yet. Tap the bookmark-add icon while reading.',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        )
                      : ListView.builder(
                          shrinkWrap: true,
                          itemCount: _bookmarks.length,
                          itemBuilder: (context, index) {
                            final bookmark = _bookmarks[index];
                            return ListTile(
                              leading: const Icon(Icons.bookmark_rounded),
                              title: Text(bookmark.label),
                              subtitle: Text(
                                MaterialLocalizations.of(context).formatMediumDate(
                                  DateTime.fromMicrosecondsSinceEpoch(bookmark.createdAt),
                                ),
                              ),
                              onTap: () {
                                Navigator.pop(context);
                                widget.onGoToBookmark(bookmark);
                              },
                              trailing: IconButton(
                                tooltip: 'Delete bookmark',
                                icon: const Icon(Icons.delete_outline_rounded),
                                onPressed: _deleting ? null : () => _delete(bookmark),
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
