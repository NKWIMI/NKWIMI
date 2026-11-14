import 'package:flutter/material.dart';

import '../config.dart';
import '../l10n/l10n.dart';
import '../services/phone.dart';

/// Always-visible strip with the hotline / emergency call button.
class EmergencyBanner extends StatelessWidget {
  const EmergencyBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: scheme.errorContainer,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        child: Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: scheme.onErrorContainer),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                tr('banner'),
                style: TextStyle(color: scheme.onErrorContainer, fontSize: 13),
              ),
            ),
            TextButton(
              onPressed: () => callNumber(
                context,
                AppConfig.healthHotline.isNotEmpty
                    ? AppConfig.healthHotline
                    : AppConfig.emergencyNumber,
              ),
              child: Text(tr('call_caps')),
            ),
          ],
        ),
      ),
    );
  }
}
