import 'package:flutter/material.dart';

import '../config.dart';
import '../l10n/l10n.dart';
import '../services/phone.dart';
import '../services/screening_engine.dart';
import '../theme.dart';
import 'chat_screen.dart';
import 'outbreak_map_screen.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.result});

  final ScreeningResult result;

  Color get _color => switch (result.level) {
        RiskLevel.urgent => RiskColors.urgent,
        RiskLevel.monitor => RiskColors.monitor,
        RiskLevel.seeDoctor => RiskColors.seeDoctor,
        RiskLevel.low => RiskColors.low,
      };

  IconData get _icon => switch (result.level) {
        RiskLevel.urgent => Icons.emergency,
        RiskLevel.monitor => Icons.thermostat,
        RiskLevel.seeDoctor => Icons.medical_services_outlined,
        RiskLevel.low => Icons.verified_outlined,
      };

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final urgent = result.level == RiskLevel.urgent;
    final callNumberValue = AppConfig.healthHotline.isNotEmpty
        ? AppConfig.healthHotline
        : AppConfig.emergencyNumber;

    return Scaffold(
      appBar: AppBar(title: Text(tr('res_title'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: _color.withValues(alpha: 0.12),
              border: Border.all(color: _color, width: 2),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Icon(_icon, color: _color, size: 32),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(result.title,
                        style: text.titleLarge?.copyWith(
                            color: _color, fontWeight: FontWeight.bold)),
                  ),
                ]),
                const SizedBox(height: 12),
                Text(result.summary),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text(tr('res_what_to_do'), style: text.titleMedium),
          const SizedBox(height: 8),
          for (final (i, a) in result.actions.indexed)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${i + 1}. ',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  Expanded(child: Text(a)),
                ],
              ),
            ),
          const SizedBox(height: 16),
          if (urgent || result.level == RiskLevel.monitor)
            FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: urgent ? RiskColors.urgent : null,
                minimumSize: const Size.fromHeight(52),
              ),
              onPressed: () => callNumber(context, callNumberValue),
              icon: const Icon(Icons.call),
              label: Text(tr('res_call', {'n': callNumberValue})),
            ),
          if (urgent) ...[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => const OutbreakMapScreen(startOnList: true),
              )),
              icon: const Icon(Icons.local_hospital_outlined),
              label: Text(tr('res_find_centre')),
            ),
          ],
          const SizedBox(height: 12),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(52)),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) =>
                  ChatScreen(screeningContext: result.toChatContext()),
            )),
            icon: const Icon(Icons.chat_bubble_outline),
            label: Text(tr('res_ask_ai')),
          ),
          const SizedBox(height: 24),
          Text(
            tr('res_footer'),
            style: text.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
