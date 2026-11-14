enum ChatRole { user, assistant }

/// An official document an answer was taken from (WHO, CDC...).
class ChatSource {
  const ChatSource({
    required this.n,
    required this.org,
    required this.title,
    required this.url,
    this.section,
  });

  /// The number used in the answer text: "[1]".
  final int n;
  final String org;
  final String title;
  final String url;

  /// Part of the document, e.g. "Early symptoms". May be null.
  final String? section;

  /// Reads one entry of the backend's "sources" list. Returns null if invalid.
  static ChatSource? fromJson(Object? json) {
    if (json is! Map) return null;
    final n = json['n'];
    final url = json['url'];
    final title = json['title'];
    if (n is! int || url is! String || url.isEmpty || title is! String) {
      return null;
    }
    final org = json['org'];
    final section = json['section'];
    return ChatSource(
      n: n,
      org: org is String ? org : '',
      title: title,
      url: url,
      section: section is String && section.isNotEmpty ? section : null,
    );
  }
}

class ChatMessage {
  const ChatMessage({
    required this.role,
    required this.text,
    this.localOnly = false,
    this.sources = const [],
    this.alertLevel,
  });

  final ChatRole role;
  final String text;

  /// Messages shown in the UI but never sent to the AI (e.g. the greeting).
  final bool localOnly;

  /// Official documents this answer cites (assistant messages only).
  final List<ChatSource> sources;

  /// 'urgent' or 'emergency' when the user described their own danger signs.
  final String? alertLevel;

  Map<String, dynamic> toJson() => {
        'role': role.name,
        'content': text,
      };
}
