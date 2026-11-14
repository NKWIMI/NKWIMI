import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/chat_message.dart';
import '../l10n/l10n.dart';
import '../services/chat_service.dart';
import '../services/voice_service.dart';
import '../widgets/answer_extras.dart';
import '../widgets/emergency_banner.dart';
import 'voice_chat_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, this.screeningContext, this.service, this.initialQuestion});

  /// Question typed in the home search bar, sent right away.
  final String? initialQuestion;

  /// Optional summary of the user's screening result, sent to the AI so it
  /// can tailor its answers.
  final String? screeningContext;

  /// Injectable for tests.
  final ChatService? service;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late final ChatService _service = widget.service ?? ChatService();
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _sending = false;
  VoiceService? _voice; // created only when "Read aloud" is used

  @override
  void initState() {
    super.initState();
    _messages.add(ChatMessage(
      role: ChatRole.assistant,
      localOnly: true,
      text: tr(widget.screeningContext != null ? 'chat_greeting_ctx' : 'chat_greeting'),
    ));
    final q = widget.initialQuestion?.trim();
    if (q != null && q.isNotEmpty) {
      _input.text = q;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _send();
      });
    }
  }

  @override
  void dispose() {
    _voice?.dispose();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() {
      _messages.add(ChatMessage(role: ChatRole.user, text: text));
      _sending = true;
      _input.clear();
    });
    _scrollToEnd();

    try {
      final reply = await _service.ask(
        _messages,
        screeningContext: widget.screeningContext,
      );
      if (!mounted) return;
      setState(() => _messages.add(ChatMessage(
            role: ChatRole.assistant,
            text: reply.text,
            sources: reply.sources,
            alertLevel: reply.alertLevel,
          )));
    } on ChatException catch (e) {
      if (!mounted) return;
      // Remove the unanswered question so the history stays valid.
      setState(() => _messages.removeLast());
      _input.text = text;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _sending = false);
      _scrollToEnd();
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

  Future<void> _showMessageActions(ChatMessage m) async {
    final action = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(
            leading: const Icon(Icons.copy),
            title: Text(tr('copy')),
            onTap: () => Navigator.pop(ctx, 'copy'),
          ),
          if (m.role == ChatRole.assistant)
            ListTile(
              leading: const Icon(Icons.volume_up_outlined),
              title: Text(tr('chat_read_aloud')),
              onTap: () => Navigator.pop(ctx, 'speak'),
            ),
          if (m.role == ChatRole.assistant && !m.localOnly)
            ListTile(
              leading: const Icon(Icons.flag_outlined),
              title: Text(tr('chat_report')),
              subtitle: Text(tr('chat_report_sub')),
              onTap: () => Navigator.pop(ctx, 'report'),
            ),
        ])),
      ),
    );
    if (!mounted) return;
    if (action == 'copy') {
      await Clipboard.setData(ClipboardData(text: m.text));
    } else if (action == 'speak') {
      _voice ??= VoiceService();
      await _voice!.speak(m.text, localeId: VoiceService.defaultLocaleFor(L10n.lang.value));
    } else if (action == 'report') {
      try {
        await _service.report(assistantText: m.text, reason: 'user_flagged');
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(tr('chat_reported'))));
      } on ChatException catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('chat_title')),
        actions: [
          IconButton(
            tooltip: tr('chat_voice_mode'),
            icon: const Icon(Icons.record_voice_over_outlined),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) =>
                  VoiceChatScreen(screeningContext: widget.screeningContext),
            )),
          ),
        ],
      ),
      body: Column(
        children: [
          const EmergencyBanner(),
          Expanded(
            child: ListView.builder(
              controller: _scroll,
              padding: const EdgeInsets.all(12),
              itemCount: _messages.length + (_sending ? 1 : 0),
              itemBuilder: (context, i) {
                if (i == _messages.length) return const _TypingBubble();
                final m = _messages[i];
                return _Bubble(
                    message: m, onLongPress: () => _showMessageActions(m));
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
            child: Text(
              tr('chat_footer'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    controller: _input,
                    minLines: 1,
                    maxLines: 4,
                    maxLength: 1000,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _send(),
                    decoration: InputDecoration(
                      hintText: tr('chat_hint'),
                      counterText: '',
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: _sending ? null : _send,
                  icon: const Icon(Icons.send),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message, required this.onLongPress});

  final ChatMessage message;
  final VoidCallback onLongPress;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final mine = message.role == ChatRole.user;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onLongPress: onLongPress,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.82),
          decoration: BoxDecoration(
            color: mine ? scheme.primary : scheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(18),
          ),
          child: mine
              ? Text(message.text, style: TextStyle(color: scheme.onPrimary))
              : AnswerBody(
                  message: message,
                  textStyle: TextStyle(color: scheme.onSurface)),
        ),
      ),
    );
  }
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) => const Align(
        alignment: Alignment.centerLeft,
        child: Padding(
          padding: EdgeInsets.all(12),
          child: SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(strokeWidth: 2.5),
          ),
        ),
      );
}
