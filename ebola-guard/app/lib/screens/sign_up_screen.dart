import 'package:flutter/material.dart';

import '../config.dart';
import '../l10n/l10n.dart';
import '../services/account_service.dart';
import '../services/phone.dart';
import '../theme.dart';
import '../widgets/profile_avatar.dart';
import 'profile_screen.dart';

/// Optional account: create one (with a profile picture) or log in.
/// "Skip" always returns to the app – nothing requires an account.
class SignUpScreen extends StatefulWidget {
  const SignUpScreen({super.key, this.startWithLogin = false});

  final bool startWithLogin;

  @override
  State<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends State<SignUpScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  late bool _login = widget.startWithLogin && AccountService.onlineAccounts;
  bool _agreed = false;
  bool _busy = false;
  bool _hidePassword = true;
  String? _photo; // picked here, saved with the account
  bool _done = false;

  bool get _online => AccountService.onlineAccounts;

  @override
  void initState() {
    super.initState();
    _name.addListener(() => setState(() {})); // live initials in the avatar
  }

  @override
  void dispose() {
    if (!_done) AccountService.discardPhoto(_photo);
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _snack(String text) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(text)));

  Future<void> _pickPhoto() async {
    final choice = await choosePhoto(context, canRemove: _photo != null);
    if (choice == null || !mounted) return;
    final old = _photo;
    setState(() => _photo = choice.path);
    if (old != null && old != choice.path) AccountService.discardPhoto(old);
  }

  String? _validateEmail(String? v) {
    final s = (v ?? '').trim();
    if (s.isEmpty) return _online ? tr('acc_required') : null;
    return RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(s) ? null : tr('acc_bad_email');
  }

  Future<void> _submit() async {
    if (_busy) return;
    if (!(_form.currentState?.validate() ?? false)) return;
    if (!_login && !_agreed) {
      _snack(tr('acc_must_agree'));
      return;
    }
    setState(() => _busy = true);
    try {
      if (!_online) {
        await AccountService.createLocalProfile(
            firstName: _name.text, email: _email.text, photoPath: _photo);
        _finish();
      } else if (_login) {
        await AccountService.logIn(email: _email.text, password: _password.text);
        _finish();
      } else {
        final signedIn = await AccountService.signUp(
          firstName: _name.text,
          email: _email.text,
          password: _password.text,
          photoPath: _photo,
        );
        if (signedIn) {
          _finish();
        } else {
          _done = true; // keep the picture for the first log-in
          if (!mounted) return;
          await showDialog<void>(
            context: context,
            builder: (ctx) => AlertDialog(
              title: Text(tr('acc_confirm_title')),
              content: Text(tr('acc_confirm_body', {'e': _email.text.trim()})),
              actions: [
                FilledButton(
                    onPressed: () => Navigator.pop(ctx), child: Text(tr('ok'))),
              ],
            ),
          );
          if (mounted) setState(() => _login = true);
        }
      }
    } on AccountException catch (e) {
      if (!mounted) return;
      final detail = e.messageKey == 'acc_err_generic' && e.detail != null
          ? ' (${e.detail})'
          : '';
      _snack(tr(e.messageKey) + detail);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _finish() {
    _done = true;
    if (!mounted) return;
    final name = AccountService.profile.value?.firstName ?? '';
    Navigator.of(context)
        .pushReplacement(MaterialPageRoute(builder: (_) => const ProfileScreen()));
    _snack(tr('acc_welcome', {'n': name}));
  }

  Future<void> _forgot() async {
    final err = _validateEmail(_email.text);
    if (_email.text.trim().isEmpty || err != null) {
      _snack(tr('acc_bad_email'));
      return;
    }
    try {
      await AccountService.sendPasswordReset(_email.text);
    } on AccountException catch (_) {
      // Same message either way: we never reveal whether an e-mail exists.
    }
    if (mounted) _snack(tr('acc_reset_sent'));
  }

  InputDecoration _field(String label, {String? hint, Widget? suffix}) => InputDecoration(
        labelText: label,
        hintText: hint,
        suffixIcon: suffix,
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Ui.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Ui.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Ui.teal, width: 1.5),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final initials = UserProfile(firstName: _name.text, createdAt: DateTime.now()).initials;
    return Scaffold(
      appBar: AppBar(
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).maybePop(),
            child: Text(tr('acc_skip')),
          ),
        ],
      ),
      body: SafeArea(
        top: false,
        child: Form(
          key: _form,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
            children: [
              if (!_login)
                Center(
                  child: SizedBox(
                    width: 104,
                    height: 104,
                    child: Stack(clipBehavior: Clip.none, children: [
                      ProfileAvatar(
                        size: 96,
                        useProfile: false,
                        photoPath: _photo,
                        initials: _name.text.trim().isEmpty ? null : initials,
                        onTap: _pickPhoto,
                      ),
                      Positioned(
                        right: 0,
                        bottom: 0,
                        child: CameraBadge(
                            onTap: _pickPhoto, tooltip: tr('profile_add_photo')),
                      ),
                    ]),
                  ),
                ),
              const SizedBox(height: 14),
              Text(
                _login ? tr('acc_login_title') : tr('acc_signup_title'),
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.5,
                    color: Ui.ink),
              ),
              const SizedBox(height: 6),
              Text(
                _login ? tr('acc_login_sub') : tr('acc_signup_sub'),
                textAlign: TextAlign.center,
                style: const TextStyle(color: Ui.muted, height: 1.4),
              ),
              if (!_online) ...[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE3F2EF),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Icon(Icons.phone_android_rounded, color: Ui.teal, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(tr('acc_local_note'),
                          style: const TextStyle(color: Ui.ink, fontSize: 13)),
                    ),
                  ]),
                ),
              ],
              const SizedBox(height: 18),
              if (!_login) ...[
                TextFormField(
                  controller: _name,
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.next,
                  autofillHints: const [AutofillHints.givenName],
                  decoration: _field(tr('acc_first_name'), hint: tr('acc_first_name_hint')),
                  validator: (v) =>
                      (v ?? '').trim().isEmpty ? tr('acc_required') : null,
                ),
                const SizedBox(height: 12),
              ],
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                autocorrect: false,
                textInputAction: _online ? TextInputAction.next : TextInputAction.done,
                autofillHints: const [AutofillHints.email],
                decoration: _field(_online ? tr('acc_email') : tr('acc_email_optional'),
                    hint: 'you@example.com'),
                validator: _validateEmail,
              ),
              if (_online) ...[
                const SizedBox(height: 12),
                TextFormField(
                  controller: _password,
                  obscureText: _hidePassword,
                  autocorrect: false,
                  enableSuggestions: false,
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _submit(),
                  autofillHints: [
                    _login ? AutofillHints.password : AutofillHints.newPassword
                  ],
                  decoration: _field(
                    tr('acc_password'),
                    hint: _login ? null : tr('acc_password_hint'),
                    suffix: IconButton(
                      tooltip: tr('acc_show_password'),
                      icon: Icon(_hidePassword
                          ? Icons.visibility_outlined
                          : Icons.visibility_off_outlined),
                      onPressed: () => setState(() => _hidePassword = !_hidePassword),
                    ),
                  ),
                  validator: (v) {
                    final s = v ?? '';
                    if (s.isEmpty) return tr('acc_required');
                    if (!_login && s.length < 8) return tr('acc_short_password');
                    return null;
                  },
                ),
              ],
              if (_login)
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(onPressed: _forgot, child: Text(tr('acc_forgot'))),
                ),
              if (!_login) ...[
                const SizedBox(height: 8),
                CheckboxListTile(
                  value: _agreed,
                  onChanged: (v) => setState(() => _agreed = v ?? false),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                  title: Text(tr('acc_agree'), style: const TextStyle(color: Ui.ink)),
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => openLink(context, AppConfig.privacyPolicyUrl),
                    icon: const Icon(Icons.open_in_new_rounded, size: 18),
                    label: Text(tr('disc_privacy')),
                  ),
                ),
              ],
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _busy ? null : _submit,
                child: _busy
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(strokeWidth: 2.5))
                    : Text(_login ? tr('acc_login_button') : tr('acc_create_button')),
              ),
              if (_online) ...[
                const SizedBox(height: 8),
                TextButton(
                  onPressed: _busy ? null : () => setState(() => _login = !_login),
                  child: Text(_login ? tr('acc_no_account') : tr('acc_have_account')),
                ),
              ],
              const SizedBox(height: 12),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.lock_outline_rounded, size: 16, color: Ui.muted),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(tr('acc_privacy_note'),
                      style: const TextStyle(fontSize: 12, color: Ui.muted, height: 1.4)),
                ),
              ]),
            ],
          ),
        ),
      ),
    );
  }
}
