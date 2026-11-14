import 'package:flutter/material.dart';

import '../config.dart';
import '../l10n/l10n.dart';
import '../services/account_service.dart';
import '../services/phone.dart';
import '../theme.dart';
import '../widgets/language_picker.dart';
import '../widgets/profile_avatar.dart';
import 'sign_up_screen.dart';

/// Profile picture tapped: profile if there is one, otherwise sign-up.
void openProfile(BuildContext context) {
  Navigator.of(context).push(MaterialPageRoute(
    builder: (_) => AccountService.profile.value == null
        ? const SignUpScreen()
        : const ProfileScreen(),
  ));
}

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final Future<int> _checks = AccountService.checksDone();
  bool _busy = false;

  void _snack(String text) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(text)));

  Future<void> _changePhoto(UserProfile p) async {
    final choice = await choosePhoto(context, canRemove: p.photoPath != null);
    if (choice == null) return;
    await AccountService.setPhoto(choice.removed ? null : choice.path);
  }

  Future<void> _editName(UserProfile p) async {
    final controller = TextEditingController(text: p.firstName);
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('profile_edit_name')),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(labelText: tr('acc_first_name')),
          onSubmitted: (v) => Navigator.pop(ctx, v),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: Text(tr('cancel'))),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, controller.text),
              child: Text(tr('save'))),
        ],
      ),
    );
    controller.dispose();
    if (name == null || name.trim().isEmpty) return;
    await _run(() => AccountService.updateName(name));
  }

  Future<void> _logOut() async {
    await _run(AccountService.logOut);
    if (!mounted) return;
    Navigator.of(context).pop();
    _snack(tr('acc_logged_out'));
  }

  Future<void> _delete(UserProfile p) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        icon: const Icon(Icons.delete_outline_rounded, color: Ui.red),
        title: Text(tr('acc_delete_title')),
        content: Text(tr('acc_delete_body')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('cancel'))),
          FilledButton(
            style: FilledButton.styleFrom(
                backgroundColor: Ui.red, minimumSize: const Size(0, 44)),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(tr('acc_delete_confirm')),
          ),
        ],
      ),
    );
    if (yes != true) return;
    final ok = await _run(AccountService.deleteAccount);
    if (!ok || !mounted) return;
    Navigator.of(context).pop();
    _snack(tr('acc_deleted'));
  }

  /// Runs [action], shows errors. Returns true on success.
  Future<bool> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      return true;
    } on AccountException catch (e) {
      if (mounted) {
        final detail = e.messageKey == 'acc_err_generic' && e.detail != null
            ? ' (${e.detail})'
            : '';
        _snack(tr(e.messageKey) + detail);
      }
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<UserProfile?>(
      valueListenable: AccountService.profile,
      builder: (context, p, _) {
        if (p == null) {
          // Logged out or deleted while this page was open.
          return const Scaffold(body: SizedBox.shrink());
        }
        final since = MaterialLocalizations.of(context).formatMediumDate(p.createdAt);
        return Scaffold(
          appBar: AppBar(
            title: Text(tr('profile_title')),
            bottom: _busy
                ? const PreferredSize(
                    preferredSize: Size.fromHeight(3),
                    child: LinearProgressIndicator(minHeight: 3))
                : null,
          ),
          body: AbsorbPointer(
            absorbing: _busy,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
              children: [
                Center(
                  child: SizedBox(
                    width: 112,
                    height: 112,
                    child: Stack(clipBehavior: Clip.none, children: [
                      ProfileAvatar(size: 108, onTap: () => _changePhoto(p)),
                      Positioned(
                        right: 0,
                        bottom: 0,
                        child: CameraBadge(
                          onTap: () => _changePhoto(p),
                          tooltip: tr('profile_change_photo'),
                        ),
                      ),
                    ]),
                  ),
                ),
                const SizedBox(height: 12),
                Text(p.firstName,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        fontSize: 22, fontWeight: FontWeight.w800, color: Ui.ink)),
                if (p.email.isNotEmpty)
                  Text(p.email,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Ui.muted)),
                const SizedBox(height: 4),
                Text(tr('profile_member_since', {'d': since}),
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 13, color: Ui.muted)),
                const SizedBox(height: 10),
                Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE3F2EF),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(p.online ? Icons.cloud_done_outlined : Icons.phone_android_rounded,
                          size: 16, color: Ui.teal),
                      const SizedBox(width: 6),
                      Text(p.online ? tr('acc_type_online') : tr('acc_type_local'),
                          style: const TextStyle(
                              color: Ui.teal, fontWeight: FontWeight.w700, fontSize: 13)),
                    ]),
                  ),
                ),
                const SizedBox(height: 18),
                Row(children: [
                  Expanded(
                    child: FutureBuilder<int>(
                      future: _checks,
                      builder: (context, snap) => _Stat(
                          value: '${snap.data ?? 0}',
                          label: tr('profile_checks'),
                          color: Ui.teal),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _Stat(
                        value: L10n.current.name,
                        label: tr('profile_language'),
                        color: Ui.purple),
                  ),
                ]),
                _SectionLabel(tr('profile_settings')),
                _Group(children: [
                  _Row(
                      icon: Icons.language_rounded,
                      color: Ui.teal,
                      label: tr('language'),
                      value: L10n.current.name,
                      onTap: () => showLanguagePicker(context)),
                  _Row(
                      icon: Icons.edit_outlined,
                      color: Ui.blue,
                      label: tr('profile_edit_name'),
                      onTap: () => _editName(p)),
                  _Row(
                      icon: Icons.photo_camera_outlined,
                      color: Ui.purple,
                      label: tr('profile_change_photo'),
                      onTap: () => _changePhoto(p)),
                ]),
                _SectionLabel(tr('profile_privacy_section')),
                _Group(children: [
                  _Row(
                      icon: Icons.shield_outlined,
                      color: Ui.teal,
                      label: tr('disc_privacy'),
                      onTap: () => openLink(context, AppConfig.privacyPolicyUrl)),
                  if (p.online)
                    _Row(
                        icon: Icons.logout_rounded,
                        color: Ui.muted,
                        label: tr('acc_logout'),
                        chevron: false,
                        onTap: _logOut),
                  _Row(
                      icon: Icons.delete_outline_rounded,
                      color: Ui.red,
                      label: p.online ? tr('acc_delete') : tr('acc_delete_local'),
                      danger: true,
                      chevron: false,
                      onTap: () => _delete(p)),
                ]),
                const SizedBox(height: 16),
                Text(tr('acc_privacy_note'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 12, color: Ui.muted, height: 1.4)),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.value, required this.label, required this.color});
  final String value, label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: Ui.card(radius: 16),
        child: Column(children: [
          Text(value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: color)),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(fontSize: 12, color: Ui.muted)),
        ]),
      );
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 22, 4, 8),
        child: Text(text.toUpperCase(),
            style: const TextStyle(
                fontSize: 12,
                letterSpacing: 0.5,
                fontWeight: FontWeight.w700,
                color: Ui.muted)),
      );
}

class _Group extends StatelessWidget {
  const _Group({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Container(
        clipBehavior: Clip.antiAlias,
        decoration: Ui.card(radius: 18),
        child: Material(
          color: Colors.transparent,
          child: Column(children: [
            for (var i = 0; i < children.length; i++) ...[
              if (i > 0) const Divider(height: 1, indent: 62, color: Color(0xFFEEF1F4)),
              children[i],
            ],
          ]),
        ),
      );
}

class _Row extends StatelessWidget {
  const _Row({
    required this.icon,
    required this.color,
    required this.label,
    required this.onTap,
    this.value,
    this.danger = false,
    this.chevron = true,
  });
  final IconData icon;
  final Color color;
  final String label;
  final String? value;
  final VoidCallback onTap;
  final bool danger, chevron;

  @override
  Widget build(BuildContext context) => ListTile(
        onTap: onTap,
        minTileHeight: 56,
        leading: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: color, size: 20),
        ),
        title: Text(label,
            style: TextStyle(
                fontWeight: FontWeight.w600, color: danger ? Ui.red : Ui.ink)),
        trailing: Row(mainAxisSize: MainAxisSize.min, children: [
          if (value != null)
            Text(value!, style: const TextStyle(color: Ui.muted, fontSize: 14)),
          if (chevron) const Icon(Icons.chevron_right_rounded, color: Ui.muted),
        ]),
      );
}
