import 'package:flutter/material.dart';

import '../l10n/l10n.dart';

/// Opens a bottom sheet listing all app languages.
Future<void> showLanguagePicker(BuildContext context) async {
  final picked = await showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (ctx) => SafeArea(
      child: SingleChildScrollView(
        child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 8),
            child: Text(tr('choose_language'),
                style: Theme.of(ctx).textTheme.titleMedium),
          ),
          for (final l in appLanguages)
            ListTile(
              title: Text(l.name),
              subtitle: l.beta ? const Text('beta') : null,
              trailing: l.code == L10n.lang.value
                  ? Icon(Icons.check, color: Theme.of(ctx).colorScheme.primary)
                  : null,
              onTap: () => Navigator.pop(ctx, l.code),
            ),
          const SizedBox(height: 8),
        ],
      ),
      ),
    ),
  );
  if (picked != null) await L10n.set(picked);
}

/// Compact button showing the current language, e.g. "🌐 Lingála".
class LanguageButton extends StatelessWidget {
  const LanguageButton({super.key, this.onDark = false});

  /// Use white text (for the coloured home header).
  final bool onDark;

  @override
  Widget build(BuildContext context) {
    final color = onDark ? Colors.white : Theme.of(context).colorScheme.primary;
    return TextButton.icon(
      onPressed: () => showLanguagePicker(context),
      icon: Icon(Icons.translate, color: color, size: 20),
      label: Text(L10n.current.name, style: TextStyle(color: color)),
    );
  }
}

/// Yellow note shown while a beta (unreviewed) language is selected.
class BetaLanguageNote extends StatelessWidget {
  const BetaLanguageNote({super.key});

  @override
  Widget build(BuildContext context) {
    if (!L10n.current.beta) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF8E1),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline, color: Color(0xFFF57F17), size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(tr('beta_note'),
                style: const TextStyle(color: Colors.black87, fontSize: 13)),
          ),
        ],
      ),
    );
  }
}
