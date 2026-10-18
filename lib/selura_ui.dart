import 'package:flutter/material.dart';

/// Branded loading views replace the transient empty library and bare
/// indeterminate spinners while app data or book pages are being opened.
class SeluraLoadingView extends StatefulWidget {
  const SeluraLoadingView({
    super.key,
    this.title = 'Opening your library',
    this.subtitle = 'Your next chapter is almost ready',
    this.compact = false,
  });

  final String title;
  final String subtitle;
  final bool compact;

  @override
  State<SeluraLoadingView> createState() => _SeluraLoadingViewState();
}

class _SeluraLoadingViewState extends State<SeluraLoadingView>
    with SingleTickerProviderStateMixin {
  late final AnimationController _motion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1500),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final reduceMotion = MediaQuery.disableAnimationsOf(context);

    return Semantics(
      liveRegion: true,
      label: '${widget.title}. ${widget.subtitle}',
      child: Center(
        child: Padding(
          padding: EdgeInsets.all(widget.compact ? 18 : 36),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedBuilder(
                animation: _motion,
                builder: (context, child) => Transform.scale(
                  scale: reduceMotion ? 1 : 0.97 + _motion.value * 0.06,
                  child: child,
                ),
                child: Container(
                  width: widget.compact ? 68 : 90,
                  height: widget.compact ? 68 : 90,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        colors.primary,
                        colors.tertiary,
                      ],
                    ),
                    borderRadius: BorderRadius.circular(
                      widget.compact ? 21 : 28,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: colors.primary.withValues(alpha: 0.15),
                        blurRadius: 26,
                        spreadRadius: 2,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.auto_stories_rounded,
                    size: widget.compact ? 34 : 45,
                    color: colors.onPrimary,
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                widget.title,
                textAlign: TextAlign.center,
                style: (widget.compact
                        ? theme.textTheme.titleMedium
                        : theme.textTheme.headlineSmall)
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              Text(
                widget.subtitle,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 22),
              SizedBox(
                width: 126,
                child: LinearProgressIndicator(
                  minHeight: 3,
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class SeluraLoadError extends StatelessWidget {
  const SeluraLoadError({
    super.key,
    required this.title,
    required this.message,
    this.onRetry,
  });

  final String title;
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 74,
              height: 74,
              decoration: BoxDecoration(
                color: theme.colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(24),
              ),
              child: Icon(
                Icons.menu_book_outlined,
                color: theme.colorScheme.onErrorContainer,
                size: 36,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              title,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w800,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: theme.textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Try again'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// A restrained, editorial library introduction with real collection counts.
class SeluraLibraryBanner extends StatelessWidget {
  const SeluraLibraryBanner({
    super.key,
    required this.bookCount,
    required this.favoriteCount,
    required this.onImport,
  });

  final int bookCount;
  final int favoriteCount;
  final VoidCallback? onImport;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final light = theme.brightness == Brightness.light;
    final ink = light ? const Color(0xFF29243A) : const Color(0xFFF1EAF9);
    final muted = ink.withValues(alpha: 0.68);

    return Container(
      key: const Key('selura-premium-library-banner'),
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(22, 22, 20, 21),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(27),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: light
              ? const [Color(0xFFF0E9FB), Color(0xFFF8F1E8)]
              : const [Color(0xFF30273E), Color(0xFF26232D)],
        ),
        border: Border.all(
          color: colors.outlineVariant.withValues(alpha: 0.28),
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            right: -24,
            top: -29,
            child: Icon(
              Icons.auto_stories_rounded,
              color: ink.withValues(alpha: 0.055),
              size: 145,
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                      color: ink.withValues(alpha: 0.09),
                      borderRadius: BorderRadius.circular(9),
                    ),
                    child: Icon(
                      Icons.bookmark_border_rounded,
                      color: ink,
                      size: 17,
                    ),
                  ),
                  const SizedBox(width: 9),
                  Text(
                    'YOUR PRIVATE LIBRARY',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: ink,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.65,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'A little space for\nbig stories.',
                style: theme.textTheme.headlineSmall?.copyWith(
                  color: ink,
                  height: 1.11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.9,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Every chapter, entirely yours. Even offline.',
                style: theme.textTheme.bodySmall?.copyWith(color: muted),
              ),
              const SizedBox(height: 19),
              Row(
                children: [
                  _ShelfMetric(
                    value: bookCount.toString(),
                    label: bookCount == 1 ? 'BOOK' : 'BOOKS',
                    ink: ink,
                  ),
                  const SizedBox(width: 13),
                  _ShelfMetric(
                    value: favoriteCount.toString(),
                    label: 'FAVORITES',
                    ink: ink,
                  ),
                  const Spacer(),
                  IconButton.filled(
                    key: const Key('selura-banner-import'),
                    tooltip: 'Import EPUB or PDF',
                    onPressed: onImport,
                    style: IconButton.styleFrom(
                      backgroundColor: ink,
                      foregroundColor: light
                          ? const Color(0xFFFFFFFF)
                          : const Color(0xFF1B1922),
                    ),
                    icon: const Icon(Icons.add_rounded),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ShelfMetric extends StatelessWidget {
  const _ShelfMetric({
    required this.value,
    required this.label,
    required this.ink,
  });

  final String value;
  final String label;
  final Color ink;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: ink,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: ink.withValues(alpha: 0.68),
              fontWeight: FontWeight.w700,
              fontSize: 9,
              letterSpacing: 0.65,
            ),
          ),
        ],
      );
}
