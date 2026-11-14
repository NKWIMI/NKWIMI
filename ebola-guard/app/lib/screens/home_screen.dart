import 'dart:math';

import 'package:flutter/material.dart';

import '../config.dart';
import '../l10n/l10n.dart';
import '../services/map_data.dart';
import '../services/phone.dart';
import '../theme.dart';
import '../widgets/language_picker.dart';
import '../widgets/profile_avatar.dart';
import 'chat_screen.dart';
import 'info_screen.dart';
import 'outbreak_map_screen.dart';
import 'profile_screen.dart';
import 'screening_screen.dart';
import 'voice_chat_screen.dart';

/// Home tab. [onOpenTab] switches the bottom navigation
/// (2 = Map, 3 = Learn, 4 = Assistant).
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, this.onOpenTab});

  final void Function(int tab)? onOpenTab;

  /// Loads the outbreak numbers. Replaced in tests.
  static Future<OutbreakMapData> Function() mapLoader =
      () => MapDataService().load();

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final Future<OutbreakMapData> _map = HomeScreen.mapLoader();
  final _search = TextEditingController();

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _go(Widget page) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));

  void _tab(int i, Widget fallback) {
    final open = widget.onOpenTab;
    if (open != null) {
      open(i);
    } else {
      _go(fallback);
    }
  }

  void _ask(String q) {
    if (q.trim().isEmpty) return;
    _search.clear();
    FocusScope.of(context).unfocus();
    _go(ChatScreen(initialQuestion: q.trim()));
  }

  @override
  Widget build(BuildContext context) {
    final tip = tr('tip_${Random(DateTime.now().day).nextInt(7) + 1}');

    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            // ---- top bar: logo, language, profile picture
            Row(children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.asset('assets/icon/icon.png',
                    width: 40,
                    height: 40,
                    errorBuilder: (context, error, stack) =>
                        const Icon(Icons.health_and_safety, color: Ui.teal, size: 36)),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(AppConfig.appName,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        fontSize: 18, fontWeight: FontWeight.w800, color: Ui.ink)),
              ),
              _LanguageChip(onTap: () => showLanguagePicker(context)),
              const SizedBox(width: 8),
              ProfileAvatar(size: 44, onTap: () => openProfile(context)),
            ]),
            const SizedBox(height: 22),
            Text(tr('home_hello'),
                style: const TextStyle(
                    fontSize: 28,
                    height: 1.15,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.5,
                    color: Ui.ink)),
            const SizedBox(height: 6),
            Text(tr('tagline'), style: const TextStyle(fontSize: 15, color: Ui.muted)),
            const SizedBox(height: 16),

            // ---- search = ask the assistant
            TextField(
              controller: _search,
              textInputAction: TextInputAction.search,
              onSubmitted: _ask,
              decoration: InputDecoration(
                hintText: tr('home_search_hint'),
                prefixIcon: const Icon(Icons.search_rounded, color: Ui.muted),
                suffixIcon: IconButton(
                  tooltip: tr('home_ask'),
                  icon: const Icon(Icons.arrow_forward_rounded, color: Ui.teal),
                  onPressed: () => _ask(_search.text),
                ),
                filled: true,
                fillColor: Colors.white,
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: const BorderSide(color: Ui.line),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: const BorderSide(color: Ui.line),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: const BorderSide(color: Ui.teal, width: 1.5),
                ),
              ),
            ),
            const SizedBox(height: 16),
            const BetaLanguageNote(),

            // ---- outbreak update
            FutureBuilder<OutbreakMapData>(
              future: _map,
              builder: (context, snap) => _OutbreakCard(
                data: snap.data,
                onTap: () => _tab(2, const OutbreakMapScreen()),
              ),
            ),
            const SizedBox(height: 14),

            // ---- main call to action
            _CheckCard(onStart: () => _go(const ScreeningScreen())),
            const SizedBox(height: 16),

            // ---- quick actions
            Row(children: [
              _Quick(
                  icon: Icons.mic_none_rounded,
                  color: Ui.purple,
                  label: tr('home_talk'),
                  onTap: () => _go(const VoiceChatScreen())),
              _Quick(
                  icon: Icons.chat_bubble_outline_rounded,
                  color: Ui.blue,
                  label: tr('home_ask'),
                  onTap: () => _tab(4, const ChatScreen())),
              _Quick(
                  icon: Icons.map_outlined,
                  color: Ui.teal,
                  label: tr('nav_map'),
                  onTap: () => _tab(2, const OutbreakMapScreen())),
              _Quick(
                  icon: Icons.call_rounded,
                  color: Ui.red,
                  label: tr('home_call'),
                  onTap: () => _showContacts(context)),
            ]),
            const SizedBox(height: 22),

            // ---- learn
            Row(children: [
              Expanded(
                child: Text(tr('home_protect'),
                    style: const TextStyle(
                        fontSize: 18, fontWeight: FontWeight.w800, color: Ui.ink)),
              ),
              TextButton(
                onPressed: () => _tab(3, const InfoScreen()),
                child: Text(tr('home_see_all')),
              ),
            ]),
            const SizedBox(height: 6),
            SizedBox(
              height: 150,
              child: ListView(
                scrollDirection: Axis.horizontal,
                clipBehavior: Clip.none,
                children: [
                  _LearnCard(
                      icon: Icons.shield_outlined,
                      color: Ui.teal,
                      title: tr('home_prevention'),
                      subtitle: tr('home_prevention_sub'),
                      onTap: () => _go(const InfoScreen())),
                  _LearnCard(
                      icon: Icons.psychology_alt_outlined,
                      color: Ui.purple,
                      title: tr('home_facts'),
                      subtitle: tr('home_facts_sub'),
                      onTap: () => _go(const InfoScreen(initialTab: 1))),
                  _LearnCard(
                      icon: Icons.play_circle_outline_rounded,
                      color: Ui.red,
                      title: tr('home_videos'),
                      subtitle: tr('home_videos_sub'),
                      onTap: () => _go(const InfoScreen(initialTab: 2))),
                  _LearnCard(
                      icon: Icons.public_rounded,
                      color: Ui.green,
                      title: tr('home_links'),
                      subtitle: tr('home_links_sub'),
                      onTap: () => _go(const InfoScreen(initialTab: 3))),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // ---- tip of the day
            Container(
              padding: const EdgeInsets.all(16),
              decoration: Ui.card(color: const Color(0xFFFFF6DB)),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.lightbulb_outline_rounded, color: Color(0xFFB07D00)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(tr('home_did_you_know'),
                            style: const TextStyle(
                                fontWeight: FontWeight.w800, color: Ui.ink)),
                        const SizedBox(height: 4),
                        Text(tip, style: const TextStyle(color: Ui.ink, height: 1.4)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _EmergencyCard(onTap: () => _showContacts(context)),
            const SizedBox(height: 20),
            Text(
              tr('not_medical_device'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: Ui.muted),
            ),
          ],
        ),
      ),
    );
  }

  void _showContacts(BuildContext context) {
    showModalBottomSheet<void>(
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
                child: Text(tr('contacts_intro'), textAlign: TextAlign.center),
              ),
              if (AppConfig.healthHotline.isNotEmpty)
                ListTile(
                  leading: const Icon(Icons.local_hospital_outlined),
                  title: Text(tr('hotline')),
                  subtitle: const Text(AppConfig.healthHotline),
                  trailing: const Icon(Icons.call),
                  onTap: () => callNumber(ctx, AppConfig.healthHotline),
                ),
              ListTile(
                leading: const Icon(Icons.emergency_outlined, color: Brand.danger),
                title: Text(tr('emergency_number')),
                subtitle: const Text(AppConfig.emergencyNumber),
                trailing: const Icon(Icons.call),
                onTap: () => callNumber(ctx, AppConfig.emergencyNumber),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}

class _LanguageChip extends StatelessWidget {
  const _LanguageChip({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: tr('language'),
      child: Material(
        color: Colors.white,
        shape: const StadiumBorder(side: BorderSide(color: Ui.line)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: Container(
            height: 44,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.language_rounded, size: 18, color: Ui.ink),
              const SizedBox(width: 6),
              Text(L10n.lang.value.toUpperCase(),
                  style: const TextStyle(fontWeight: FontWeight.w700, color: Ui.ink)),
            ]),
          ),
        ),
      ),
    );
  }
}

class _OutbreakCard extends StatelessWidget {
  const _OutbreakCard({required this.data, required this.onTap});
  final OutbreakMapData? data;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final d = data;
    final active = d?.areas.where((a) => a.status == AreaStatus.active).length ?? 0;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Ink(
          padding: const EdgeInsets.all(16),
          decoration: Ui.card(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: const BoxDecoration(color: Ui.red, shape: BoxShape.circle),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(tr('home_outbreak_title'),
                      style: const TextStyle(
                          fontWeight: FontWeight.w800, fontSize: 16, color: Ui.ink)),
                ),
                if (d != null && d.updated.isNotEmpty)
                  Text(tr('home_outbreak_updated', {'d': d.updated}),
                      style: const TextStyle(fontSize: 12, color: Ui.muted)),
              ]),
              const SizedBox(height: 8),
              if (d == null)
                Container(
                  height: 14,
                  width: 180,
                  decoration: BoxDecoration(
                    color: const Color(0xFFEEF1F4),
                    borderRadius: BorderRadius.circular(7),
                  ),
                )
              else ...[
                if (d.summary.isNotEmpty)
                  Text(d.summary,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Ui.ink, height: 1.4)),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  _Pill(
                      text: tr('home_outbreak_areas', {'n': '$active'}),
                      color: Ui.red),
                  _Pill(
                      text: tr('home_outbreak_centres', {'n': '${d.centres.length}'}),
                      color: Ui.teal),
                ]),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, required this.color});
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(text,
            style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 13)),
      );
}

class _CheckCard extends StatelessWidget {
  const _CheckCard({required this.onStart});
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: Brand.headerGradient,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(tr('home_cta_title'),
              style: const TextStyle(
                  color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          Text(tr('home_cta_body'),
              style: const TextStyle(color: Color(0xE6FFFFFF), height: 1.4)),
          const SizedBox(height: 16),
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: Ui.teal,
            ),
            onPressed: onStart,
            icon: const Icon(Icons.play_arrow_rounded),
            label: Text(tr('home_cta_button')),
          ),
        ],
      ),
    );
  }
}

class _Quick extends StatelessWidget {
  const _Quick({
    required this.icon,
    required this.color,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final Color color;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Column(children: [
            Container(
              width: 56,
              height: 56,
              decoration: Ui.card(radius: 18),
              child: Icon(icon, color: color, size: 26),
            ),
            const SizedBox(height: 6),
            Text(label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w600, color: Ui.ink)),
          ]),
        ),
      ),
    );
  }
}

class _LearnCard extends StatelessWidget {
  const _LearnCard({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });
  final IconData icon;
  final Color color;
  final String title, subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 12),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: onTap,
          child: Ink(
            width: 150,
            padding: const EdgeInsets.all(14),
            decoration: Ui.card(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, color: color),
                ),
                const Spacer(),
                Text(title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontWeight: FontWeight.w800, fontSize: 15, color: Ui.ink)),
                const SizedBox(height: 2),
                Text(subtitle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12, color: Ui.muted)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _EmergencyCard extends StatelessWidget {
  const _EmergencyCard({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Ink(
          padding: const EdgeInsets.all(16),
          decoration: Ui.card(color: const Color(0xFFFDECEC)),
          child: Row(children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Ui.red.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.emergency_outlined, color: Ui.red),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(tr('home_emergency'),
                      style: const TextStyle(
                          fontWeight: FontWeight.w800, fontSize: 16, color: Ui.ink)),
                  Text(tr('home_emergency_sub'), style: const TextStyle(color: Ui.ink)),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: Ui.muted),
          ]),
        ),
      ),
    );
  }
}
