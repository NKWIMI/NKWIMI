import 'package:flutter/material.dart';

import '../l10n/l10n.dart';
import '../models/chat_message.dart';
import '../services/phone.dart';

/// Safety alert shown above an answer when the user described their own
/// danger signs. Reuses the screening texts, already in every app language.
class AnswerAlert extends StatelessWidget {
  const AnswerAlert({super.key, required this.level});

  /// 'urgent' or 'emergency'.
  final String level;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final lines = level == 'emergency'
        ? [tr('urgent_a2'), tr('urgent_a3')]
        : [tr('urgent_a1'), tr('urgent_a2'), tr('urgent_a3')];
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(Icons.warning_amber_rounded,
                size: 18, color: scheme.onErrorContainer),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                tr('urgent_title'),
                style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: scheme.onErrorContainer),
              ),
            ),
          ]),
          for (final line in lines)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                '• $line',
                style: TextStyle(color: scheme.onErrorContainer, fontSize: 13),
              ),
            ),
        ],
      ),
    );
  }
}

/// Numbered list of the official documents an answer comes from.
/// The numbers match the [1], [2] markers in the answer; a tap opens the page.
class AnswerSources extends StatelessWidget {
  const AnswerSources({super.key, required this.sources});

  final List<ChatSource> sources;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final small = Theme.of(context).textTheme.bodySmall ?? const TextStyle(fontSize: 12);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Divider(height: 18, color: scheme.outlineVariant),
        Text(tr('chat_sources'),
            style: small.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 2),
        for (final s in sources)
          InkWell(
            onTap: () => openLink(context, s.url),
            borderRadius: BorderRadius.circular(6),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 20,
                    height: 20,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: scheme.primaryContainer,
                      borderRadius: BorderRadius.circular(5),
                    ),
                    child: Text(
                      '${s.n}',
                      style: small.copyWith(
                          fontWeight: FontWeight.w700,
                          color: scheme.onPrimaryContainer),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text.rich(
                      TextSpan(children: [
                        if (s.org.isNotEmpty)
                          TextSpan(
                              text: '${s.org} · ',
                              style: const TextStyle(fontWeight: FontWeight.w700)),
                        TextSpan(
                            text: s.title,
                            style: const TextStyle(
                                decoration: TextDecoration.underline)),
                        if (s.section != null)
                          TextSpan(
                              text: ' › ${s.section}',
                              style: TextStyle(color: scheme.onSurfaceVariant)),
                      ]),
                      style: small.copyWith(color: scheme.onSurface),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(Icons.open_in_new,
                      size: 14, color: scheme.onSurfaceVariant),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

/// The content of an assistant bubble: alert, answer text, sources.
class AnswerBody extends StatelessWidget {
  const AnswerBody({super.key, required this.message, this.textStyle});

  final ChatMessage message;
  final TextStyle? textStyle;

  @override
  Widget build(BuildContext context) {
    final alert = message.alertLevel;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (alert != null) AnswerAlert(level: alert),
        Text(message.text, style: textStyle),
        if (message.sources.isNotEmpty) AnswerSources(sources: message.sources),
      ],
    );
  }
}
