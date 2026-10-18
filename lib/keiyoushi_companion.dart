import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

/// Keiyoushi publishes Mihon/Tachiyomi extension APKs and a protobuf index.
/// Selura is a Flutter app and cannot execute those plugins without a separate
/// native extension host. This helper intentionally DOES NOT pretend to install
/// extensions into Selura, sideload APKs, or load untrusted code.
class KeiyoushiCompanion {
  static const repositoryUrl =
      'https://github.com/keiyoushi/extensions/raw/repo/index.pb';
  static const setupUrl = 'https://keiyoushi.github.io/add-repo';
  static const mihonUrl = 'https://mihon.app/download/';
  static const listingUrl = 'https://keiyoushi.github.io/extensions/';

  static bool trustedLink(Uri uri) =>
      uri.scheme == 'https' &&
      uri.userInfo.isEmpty &&
      uri.port == 443 &&
      (uri.toString() == setupUrl ||
          uri.toString() == mihonUrl ||
          uri.toString() == listingUrl);
}

/// A functional companion workflow for the existing Keiyoushi APK ecosystem.
/// The user's EPUB/PDF/CBZ books and Selura storage remain untouched.
class KeiyoushiCompanionPage extends StatelessWidget {
  const KeiyoushiCompanionPage({super.key});

  Future<void> _copy(BuildContext context) async {
    await Clipboard.setData(
      const ClipboardData(text: KeiyoushiCompanion.repositoryUrl),
    );
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Keiyoushi repository URL copied')),
      );
    }
  }

  Future<void> _open(BuildContext context, String link) async {
    final uri = Uri.parse(link);
    if (!KeiyoushiCompanion.trustedLink(uri)) return;
    try {
      if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text(
              'Could not open browser. You can copy the repository URL instead.',
            )),
          );
        }
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text(
            'Browser unavailable. You can copy the repository URL instead.',
          )),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Keiyoushi extensions')),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.hub_outlined,
                      size: 32, color: colors.primary),
                  const SizedBox(height: 10),
                  Text(
                    'Read Keiyoushi sources with Mihon',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Keiyoushi extensions are native Android plugins built '
                    'for Mihon-compatible readers. Selura cannot run them '
                    'directly yet. Use the compatible reader for those sources '
                    'while keeping your Selura books and reading progress.',
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'This is not an extension installer for Selura. '
                    'External APKs may run privileged code; only install '
                    'extensions that you trust.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text('Setup on your Android phone',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w800,
              )),
          const SizedBox(height: 10),
          const ListTile(
            leading: CircleAvatar(child: Text('1')),
            title: Text('Install Mihon'),
            subtitle: Text('Use the official Mihon site and follow its Android installation instructions.'),
          ),
          FilledButton.icon(
            key: const Key('keiyoushi-open-mihon'),
            onPressed: () => _open(
              context, KeiyoushiCompanion.mihonUrl,
            ),
            icon: const Icon(Icons.open_in_new_rounded),
            label: const Text('Open official Mihon download'),
          ),
          const SizedBox(height: 10),
          const ListTile(
            leading: CircleAvatar(child: Text('2')),
            title: Text('Add the Keiyoushi repository'),
            subtitle: Text(
              'Open the official setup link in your browser, or copy '
              'the repository URL into Mihon’s extension repository settings.',
            ),
          ),
          OutlinedButton.icon(
            key: const Key('keiyoushi-open-setup'),
            onPressed: () => _open(
              context, KeiyoushiCompanion.setupUrl,
            ),
            icon: const Icon(Icons.open_in_browser_rounded),
            label: const Text('Open Keiyoushi setup'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            key: const Key('keiyoushi-copy-repo'),
            onPressed: () => _copy(context),
            icon: const Icon(Icons.copy_rounded),
            label: const Text('Copy current repository URL'),
          ),
          const SizedBox(height: 8),
          SelectableText(
            KeiyoushiCompanion.repositoryUrl,
            style: theme.textTheme.bodySmall?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 16),
          const ListTile(
            leading: CircleAvatar(child: Text('3')),
            title: Text('Browse and install trusted sources in Mihon'),
            subtitle: Text(
              'Open Mihon → Browse → Extensions. The sources will appear '
              'in Mihon, not Selura.',
            ),
          ),
          TextButton.icon(
            key: const Key('keiyoushi-open-list'),
            onPressed: () => _open(
              context, KeiyoushiCompanion.listingUrl,
            ),
            icon: const Icon(Icons.list_alt_rounded),
            label: const Text('View Keiyoushi source listing'),
          ),
          const SizedBox(height: 20),
          Text(
            'Why is this separate?',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'The current Keiyoushi index is index.pb, not the old '
            'index.min.json. Reading or downloading a list does not make '
            'Mihon/Tachiyomi extensions executable in Selura. A secure '
            'Kotlin extension runtime and host API would be a separate '
            'native Android development milestone.',
          ),
          const SizedBox(height: 14),
        ],
      ),
    );
  }
}
