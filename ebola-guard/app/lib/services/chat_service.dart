import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../config.dart';
import '../l10n/l10n.dart';
import '../models/chat_message.dart';

class ChatException implements Exception {
  ChatException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Talks to your backend, never directly to the AI provider, so your API key
/// is never shipped inside the app.
class ChatService {
  ChatService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<String> send(
    List<ChatMessage> history, {
    String? screeningContext,
    String? mode, // 'voice' = short answers meant to be read aloud
  }) async {
    final payload = {
      'messages': [
        for (final m in history)
          if (!m.localOnly) m.toJson(),
      ],
      if (screeningContext != null) 'screeningContext': screeningContext,
      if (mode != null) 'mode': mode,
      'language': L10n.current.englishName,
    };

    final http.Response res;
    try {
      res = await _client
          .post(
            Uri.parse('${AppConfig.backendUrl}/api/chat'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 60));
    } on TimeoutException {
      throw ChatException(tr('err_timeout'));
    } catch (_) {
      throw ChatException(kDebugMode
          ? 'Cannot reach the assistant server at ${AppConfig.backendUrl}. '
              'Is the backend running (npm start)?'
          : tr('err_offline'));
    }

    final body = _decode(res);
    if (res.statusCode != 200) {
      throw ChatException(
        body['error'] as String? ?? tr('err_generic', {'n': '${res.statusCode}'}),
      );
    }
    final reply = body['reply'];
    if (reply is! String || reply.isEmpty) {
      throw ChatException(tr('err_empty'));
    }
    return reply;
  }

  /// Lets users flag a bad or harmful AI answer (required by Google Play's
  /// AI-generated content policy).
  Future<void> report({
    required String assistantText,
    required String reason,
  }) async {
    try {
      await _client
          .post(
            Uri.parse('${AppConfig.backendUrl}/api/report'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'message': assistantText, 'reason': reason}),
          )
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw ChatException(tr('err_report'));
    }
  }

  Map<String, dynamic> _decode(http.Response res) {
    try {
      final decoded = jsonDecode(utf8.decode(res.bodyBytes));
      return decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
    } catch (_) {
      return <String, dynamic>{};
    }
  }
}
