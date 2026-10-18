import 'package:flutter/material.dart';

/// Keeps the expensive EPUB/PDF renderer mounted when chrome is hidden.
class ReaderFrame extends StatelessWidget {
  const ReaderFrame({
    super.key,
    required this.focusMode,
    required this.onExitFocus,
    required this.appBar,
    required this.body,
    required this.backgroundColor,
    required this.foregroundColor,
    this.bottomBar,
  });

  final bool focusMode;
  final VoidCallback onExitFocus;
  final PreferredSizeWidget appBar;
  final Widget body;
  final Widget? bottomBar;
  final Color backgroundColor;
  final Color foregroundColor;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: backgroundColor,
        appBar: focusMode ? null : appBar,
        bottomNavigationBar: focusMode ? null : bottomBar,
        body: Stack(
          children: [
            Positioned.fill(
              child: SafeArea(
                top: focusMode,
                bottom: false,
                child: body,
              ),
            ),
            if (focusMode)
              Positioned(
                top: 12,
                right: 14,
                child: SafeArea(
                  bottom: false,
                  child: Material(
                    color: backgroundColor.withValues(alpha: 0.96),
                    elevation: 3,
                    borderRadius: BorderRadius.circular(99),
                    child: InkWell(
                      key: const Key('reader-focus-exit'),
                      onTap: onExitFocus,
                      borderRadius: BorderRadius.circular(99),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 10,
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.fullscreen_exit_rounded,
                              size: 19,
                              color: foregroundColor,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Show controls',
                              style: TextStyle(
                                color: foregroundColor,
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      );
}

/// A compact theme-matched footer for chapter/page status and quick actions.
class ReaderChromeFooter extends StatelessWidget {
  const ReaderChromeFooter({
    super.key,
    required this.category,
    required this.label,
    required this.leadingIcon,
    required this.backgroundColor,
    required this.foregroundColor,
    this.progressFraction,
    this.trailing,
  });

  final String category;
  final String label;
  final IconData leadingIcon;
  final Color backgroundColor;
  final Color foregroundColor;
  final double? progressFraction;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: backgroundColor,
          border: Border(
            top: BorderSide(
              color: foregroundColor.withValues(alpha: 0.11),
            ),
          ),
        ),
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 7, 14, 9),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Icon(
                      leadingIcon,
                      size: 20,
                      color: foregroundColor.withValues(alpha: 0.70),
                    ),
                    const SizedBox(width: 11),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            category,
                            style: TextStyle(
                              color: foregroundColor.withValues(alpha: 0.55),
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.1,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            label,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: foregroundColor,
                              fontWeight: FontWeight.w600,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (trailing != null) ...[
                      const SizedBox(width: 5),
                      trailing!,
                    ],
                  ],
                ),
                if (progressFraction != null) ...[
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(99),
                    child: LinearProgressIndicator(
                      value: progressFraction!.clamp(0.0, 1.0).toDouble(),
                      backgroundColor:
                          foregroundColor.withValues(alpha: 0.09),
                      color: Theme.of(context).colorScheme.primary,
                      minHeight: 3,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
}

/// The existing EPUB settings queue persists each quick typography change.
class ReaderFontSizeControls extends StatelessWidget {
  const ReaderFontSizeControls({
    super.key,
    required this.fontSize,
    required this.foregroundColor,
    required this.onChanged,
  });

  final double fontSize;
  final Color foregroundColor;
  final ValueChanged<double>? onChanged;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            key: const Key('reader-font-smaller'),
            tooltip: 'Smaller reading text',
            icon: const Icon(Icons.text_decrease_rounded, size: 19),
            color: foregroundColor,
            constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
            padding: EdgeInsets.zero,
            onPressed: fontSize <= 12 || onChanged == null
                ? null
                : () => onChanged!(
                    (fontSize - 1).clamp(12.0, 32.0).toDouble(),
                  ),
          ),
          Text(
            fontSize.round().toString(),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: foregroundColor.withValues(alpha: 0.85),
            ),
          ),
          IconButton(
            key: const Key('reader-font-larger'),
            tooltip: 'Larger reading text',
            icon: const Icon(Icons.text_increase_rounded, size: 19),
            color: foregroundColor,
            constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
            padding: EdgeInsets.zero,
            onPressed: fontSize >= 32 || onChanged == null
                ? null
                : () => onChanged!(
                    (fontSize + 1).clamp(12.0, 32.0).toDouble(),
                  ),
          ),
        ],
      );
}
