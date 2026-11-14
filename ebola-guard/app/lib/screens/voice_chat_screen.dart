import 'package:flutter/material.dart';

import '../l10n/l10n.dart';
import '../models/chat_message.dart';
import '../services/chat_service.dart';
import '../services/voice_service.dart';
import '../widgets/emergency_banner.dart';

enum _VoiceState { idle, listening, thinking, speaking }

/// Hands-free conversation: tap the microphone, speak, and the assistant
/// answers out loud in the same language.
class VoiceChatScreen extends StatefulWidget {
  const VoiceChatScreen({super.key, this.screeningContext});

  final String? screeningContext;

  @override
  State<VoiceChatScreen> createState() => _VoiceChatScreenState();
}

class _VoiceChatScreenState extends State<VoiceChatScreen> {
  final _voice = VoiceService();
  final _chat = ChatService();
  final _scroll = ScrollController();
  final List<ChatMessage> _messages = [];

  _VoiceState _state = _VoiceState.idle;
  bool _available = false;
  bool _initialising = true;
  String _liveText = '';
  String? _localeId;
  String _localeName = tr('voice_phone_lang');

  @override
  void initState() {
    super.initState();
    _setup();
  }

  Future<void> _setup() async {
    final ok = await _voice.init(
      onStatus: (status) {
        // Recognition stopped without a final result (e.g. silence).
        if ((status == 'done' || status == 'notListening') &&
            _state == _VoiceState.listening &&
            mounted) {
          Future.delayed(const Duration(milliseconds: 400), () {
            if (mounted && _state == _VoiceState.listening) {
              setState(() => _state = _VoiceState.idle);
            }
          });
        }
      },
      onError: (error) {
        if (!mounted) return;
        setState(() => _state = _VoiceState.idle);
        if (error != 'error_no_match' && error != 'error_speech_timeout') {
          _snack(tr('voice_error', {'e': error}));
        } else {
          _snack(tr('voice_not_heard'));
        }
      },
    );
    String? locale;
    String? localeName;
    var missing = false;
    if (ok) {
      // Listen in the app language if the phone supports it.
      final match = await _voice.bestLanguageFor(L10n.lang.value);
      if (match != null) {
        locale = match.id;
        localeName = match.name;
      } else if (L10n.current.beta) {
        // Lingala, Kikongo, Tshiluba: usually not supported yet → French.
        final fr = await _voice.bestLanguageFor('fr');
        locale = fr?.id;
        localeName = fr?.name;
        missing = true;
      } else {
        locale = await _voice.systemLocaleId();
      }
    }
    if (!mounted) return;
    setState(() {
      _available = ok;
      _initialising = false;
      _localeId = locale;
      if (localeName != null) _localeName = localeName;
    });
    if (missing) _snack(tr('voice_lang_missing'));
  }

  @override
  void dispose() {
    _voice.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _snack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  Future<void> _onMicTap() async {
    switch (_state) {
      case _VoiceState.idle:
        setState(() {
          _state = _VoiceState.listening;
          _liveText = '';
        });
        await _voice.listen(
          localeId: _localeId,
          onResult: (text, isFinal) {
            if (!mounted) return;
            setState(() => _liveText = text);
            if (isFinal) _ask(text);
          },
        );
      case _VoiceState.listening:
        await _voice.stopListening(); // final result arrives via onResult
      case _VoiceState.speaking:
        await _voice.stopSpeaking();
        if (mounted) setState(() => _state = _VoiceState.idle);
      case _VoiceState.thinking:
        break;
    }
  }

  Future<void> _ask(String text) async {
    final question = text.trim();
    if (question.isEmpty) {
      setState(() => _state = _VoiceState.idle);
      return;
    }
    setState(() {
      _messages.add(ChatMessage(role: ChatRole.user, text: question));
      _liveText = '';
      _state = _VoiceState.thinking;
    });
    _scrollToEnd();

    try {
      final reply = await _chat.send(
        _messages,
        screeningContext: widget.screeningContext,
        mode: 'voice',
      );
      if (!mounted) return;
      setState(() {
        _messages.add(ChatMessage(role: ChatRole.assistant, text: reply));
        _state = _VoiceState.speaking;
      });
      _scrollToEnd();
      await _voice.speak(reply, localeId: _localeId);
    } on ChatException catch (e) {
      if (!mounted) return;
      setState(() => _messages.removeLast());
      _snack(e.message);
    } finally {
      if (mounted && _state != _VoiceState.listening) {
        setState(() => _state = _VoiceState.idle);
      }
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _pickLanguage() async {
    final langs = await _voice.languages();
    if (!mounted) return;
    final picked = await showModalBottomSheet<VoiceLanguage>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: SizedBox(
          height: MediaQuery.of(ctx).size.height * 0.7,
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(tr('voice_pick'),
                  style: const TextStyle(fontWeight: FontWeight.w600)),
            ),
            Expanded(
              child: ListView.builder(
                itemCount: langs.length,
                itemBuilder: (_, i) => ListTile(
                  title: Text(langs[i].name),
                  subtitle: Text(langs[i].id),
                  trailing: langs[i].id == _localeId
                      ? const Icon(Icons.check)
                      : null,
                  onTap: () => Navigator.pop(ctx, langs[i]),
                ),
              ),
            ),
          ]),
        ),
      ),
    );
    if (picked != null && mounted) {
      setState(() {
        _localeId = picked.id;
        _localeName = picked.name;
      });
    }
  }

  String get _statusText => switch (_state) {
        _VoiceState.idle => tr('voice_idle'),
        _VoiceState.listening => tr('voice_listening'),
        _VoiceState.thinking => tr('voice_thinking'),
        _VoiceState.speaking => tr('voice_speaking'),
      };

  IconData get _micIcon => switch (_state) {
        _VoiceState.idle => Icons.mic,
        _VoiceState.listening => Icons.stop,
        _VoiceState.thinking => Icons.hourglass_top,
        _VoiceState.speaking => Icons.volume_off,
      };

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('voice_title')),
        actions: [
          if (_available)
            TextButton.icon(
              onPressed: _state == _VoiceState.idle ? _pickLanguage : null,
              icon: const Icon(Icons.translate),
              label: Text(
                _localeName.length > 14
                    ? '${_localeName.substring(0, 14)}…'
                    : _localeName,
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          const EmergencyBanner(),
          Expanded(
            child: _initialising
                ? const Center(child: CircularProgressIndicator())
                : !_available
                    ? const _Unavailable()
                    : ListView(
                        controller: _scroll,
                        padding: const EdgeInsets.all(16),
                        children: [
                          if (_messages.isEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 24),
                              child: Text(
                                tr('voice_examples'),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          for (final m in _messages) _VoiceBubble(message: m),
                          if (_liveText.isNotEmpty)
                            Opacity(
                              opacity: 0.6,
                              child: _VoiceBubble(
                                message: ChatMessage(
                                    role: ChatRole.user, text: _liveText),
                              ),
                            ),
                        ],
                      ),
          ),
          if (_available)
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.only(bottom: 24, top: 8),
                child: Column(children: [
                  Text(_statusText),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: 96,
                    height: 96,
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                        shape: const CircleBorder(),
                        backgroundColor: _state == _VoiceState.listening
                            ? scheme.error
                            : scheme.primary,
                      ),
                      onPressed:
                          _state == _VoiceState.thinking ? null : _onMicTap,
                      child: _state == _VoiceState.thinking
                          ? const CircularProgressIndicator()
                          : Icon(_micIcon, size: 44),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(tr('voice_disclaimer'),
                      style: Theme.of(context).textTheme.bodySmall),
                ]),
              ),
            ),
        ],
      ),
    );
  }
}

class _VoiceBubble extends StatelessWidget {
  const _VoiceBubble({required this.message});
  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final mine = message.role == ChatRole.user;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints:
            BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
        decoration: BoxDecoration(
          color: mine ? scheme.primary : scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Text(message.text,
            style:
                TextStyle(color: mine ? scheme.onPrimary : scheme.onSurface)),
      ),
    );
  }
}

class _Unavailable extends StatelessWidget {
  const _Unavailable();

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: Text(tr('voice_unavailable'), textAlign: TextAlign.center),
        ),
      );
}
