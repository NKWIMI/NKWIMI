enum ChatRole { user, assistant }

class ChatMessage {
  const ChatMessage({
    required this.role,
    required this.text,
    this.localOnly = false,
  });

  final ChatRole role;
  final String text;

  /// Messages shown in the UI but never sent to the AI (e.g. the greeting).
  final bool localOnly;

  Map<String, dynamic> toJson() => {
        'role': role.name,
        'content': text,
      };
}
