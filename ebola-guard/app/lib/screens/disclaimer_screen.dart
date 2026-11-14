import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config.dart';
import '../l10n/l10n.dart';
import '../main.dart';
import '../services/phone.dart';
import '../widgets/language_picker.dart';
import 'main_shell.dart';

/// Shown on first launch: choose a language, read the key points, accept.
class DisclaimerScreen extends StatefulWidget {
  const DisclaimerScreen({super.key});

  @override
  State<DisclaimerScreen> createState() => _DisclaimerScreenState();
}

class _DisclaimerScreenState extends State<DisclaimerScreen> {
  bool _agreed = false;

  Future<void> _continue() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(kDisclaimerKey, true);
    AppState.disclaimerAccepted = true;
    if (!L10n.chosen) await L10n.set(L10n.lang.value); // remember the choice
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const MainShell()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const Align(alignment: Alignment.centerRight, child: LanguageButton()),
            Center(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(22),
                child: Image.asset('assets/icon/icon.png',
                    width: 88,
                    height: 88,
                    errorBuilder: (context, error, stack) => Icon(
                        Icons.health_and_safety,
                        size: 64,
                        color: Theme.of(context).colorScheme.primary)),
              ),
            ),
            const SizedBox(height: 16),
            Text(tr('disc_title'),
                style: text.headlineSmall, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            const BetaLanguageNote(),
            for (var i = 1; i <= 4; i++) _Point(tr('disc_$i')),
            TextButton(
              onPressed: () => openLink(context, AppConfig.privacyPolicyUrl),
              child: Text(tr('disc_privacy')),
            ),
            CheckboxListTile(
              value: _agreed,
              onChanged: (v) => setState(() => _agreed = v ?? false),
              title: Text(tr('disc_agree')),
              controlAffinity: ListTileControlAffinity.leading,
              contentPadding: EdgeInsets.zero,
            ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _agreed ? _continue : null,
              child: Text(tr('disc_continue')),
            ),
          ],
        ),
      ),
    );
  }
}

class _Point extends StatelessWidget {
  const _Point(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(top: 2),
              child: Icon(Icons.check_circle_outline, size: 20),
            ),
            const SizedBox(width: 10),
            Expanded(child: Text(text)),
          ],
        ),
      );
}
