import 'package:flutter/material.dart';

/// Visual filters are backed by the existing local library; no books are moved
/// or deleted when a filter changes.
enum SeluraShelfFilter { all, epub, pdf, manga, favorites }

extension SeluraShelfFilterDetails on SeluraShelfFilter {
  String get label => switch (this) {
        SeluraShelfFilter.all => 'All books',
        SeluraShelfFilter.epub => 'EPUB',
        SeluraShelfFilter.pdf => 'PDF',
        SeluraShelfFilter.manga => 'Manga',
        SeluraShelfFilter.favorites => 'Favorites',
      };

  bool accepts({required String format, required bool favorite}) =>
      switch (this) {
        SeluraShelfFilter.all => true,
        SeluraShelfFilter.epub => format.toLowerCase() == 'epub',
        SeluraShelfFilter.pdf => format.toLowerCase() == 'pdf',
        SeluraShelfFilter.manga => format.toLowerCase() == 'cbz',
        SeluraShelfFilter.favorites => favorite,
      };
}

/// Horizontal filter controls remain accessible on narrow Android screens.
class SeluraShelfFilterBar extends StatelessWidget {
  const SeluraShelfFilterBar({
    super.key,
    required this.selected,
    required this.onSelected,
  });

  final SeluraShelfFilter selected;
  final ValueChanged<SeluraShelfFilter> onSelected;

  @override
  Widget build(BuildContext context) {
    final palette = Theme.of(context).colorScheme;
    return SingleChildScrollView(
      key: const Key('selura-shelf-filter-scroll'),
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (final filter in SeluraShelfFilter.values) ...[
            ChoiceChip(
              key: Key('selura-filter-${filter.name}'),
              label: Text(filter.label),
              selected: selected == filter,
              onSelected: (_) => onSelected(filter),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(13),
                side: BorderSide(
                  color: selected == filter
                      ? palette.primary.withValues(alpha: 0.30)
                      : palette.outlineVariant.withValues(alpha: 0.35),
                ),
              ),
              labelStyle: TextStyle(
                fontWeight: selected == filter
                    ? FontWeight.w700
                    : FontWeight.w500,
              ),
              showCheckmark: false,
              selectedColor: palette.primaryContainer,
            ),
            const SizedBox(width: 8),
          ],
        ],
      ),
    );
  }
}

class SeluraShelfHeading extends StatelessWidget {
  const SeluraShelfHeading({
    super.key,
    required this.title,
    required this.subtitle,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                subtitle,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

class SeluraShelfEmptyResults extends StatelessWidget {
  const SeluraShelfEmptyResults({
    super.key,
    required this.onReset,
  });

  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 25, vertical: 42),
      child: Column(
        children: [
          Container(
            width: 76,
            height: 76,
            decoration: BoxDecoration(
              color: colors.primaryContainer.withValues(alpha: 0.6),
              borderRadius: BorderRadius.circular(26),
            ),
            child: Icon(
              Icons.menu_book_outlined,
              size: 34,
              color: colors.onPrimaryContainer,
            ),
          ),
          const SizedBox(height: 17),
          Text(
            'No stories found',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 7),
          Text(
            'Try a different title or show all your books.',
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 20),
          OutlinedButton.icon(
            key: const Key('selura-clear-filters'),
            onPressed: onReset,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('Show all books'),
          ),
        ],
      ),
    );
  }
}
