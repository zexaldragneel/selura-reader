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

class SeluraLibraryBanner extends StatelessWidget {
  const SeluraLibraryBanner({
    super.key,
    required this.bookCount,
    required this.onImport,
  });

  final int bookCount;
  final VoidCallback? onImport;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textColor = colors.onPrimaryContainer;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(22, 22, 16, 19),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            colors.primaryContainer,
            colors.tertiaryContainer,
          ],
        ),
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            right: -10,
            top: -26,
            child: Icon(
              Icons.auto_stories_rounded,
              size: 120,
              color: textColor.withValues(alpha: 0.08),
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.offline_bolt_rounded, size: 16, color: textColor),
                  const SizedBox(width: 6),
                  Text(
                    'YOUR OFFLINE SHELF',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: textColor,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.9,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 13),
              Text(
                'Stories worth\ngetting lost in.',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w900,
                      height: 1.15,
                      color: textColor,
                    ),
              ),
              const SizedBox(height: 12),
              Text(
                '$bookCount ${bookCount == 1 ? 'book' : 'books'} in your pocket',
                style: TextStyle(color: textColor.withValues(alpha: 0.82)),
              ),
              const SizedBox(height: 15),
              FilledButton.tonalIcon(
                onPressed: onImport,
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('Add a book'),
                style: FilledButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
