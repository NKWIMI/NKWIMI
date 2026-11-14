import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

class VoiceLanguage {
  const VoiceLanguage(this.id, this.name);

  /// Speech-recognition locale id, e.g. "en_US", "fr_FR", "sw_KE".
  final String id;
  final String name;
}

/// Wraps speech-to-text (listening) and text-to-speech (speaking).
/// Both use the phone's built-in engines, so they are free and need no key.
class VoiceService {
  final SpeechToText _stt = SpeechToText();
  final FlutterTts _tts = FlutterTts();
  bool _ready = false;

  /// Languages shown first in the picker (most relevant to Ebola-affected
  /// regions). Others the phone supports are listed after.
  static const preferredPrefixes = ['en', 'fr', 'sw', 'ln', 'lg', 'pt', 'ar'];

  bool get isListening => _stt.isListening;

  /// Asks for microphone permission the first time. Returns false if the
  /// user refuses or the phone has no speech recognition.
  Future<bool> init({
    void Function(String status)? onStatus,
    void Function(String error)? onError,
  }) async {
    if (_ready) return true;
    _ready = await _stt.initialize(
      onStatus: (s) => onStatus?.call(s),
      onError: (e) => onError?.call(e.errorMsg),
    );
    await _tts.awaitSpeakCompletion(true);
    await _tts.setSpeechRate(0.45);
    return _ready;
  }

  Future<List<VoiceLanguage>> languages() async {
    final locales = await _stt.locales();
    final list = [for (final l in locales) VoiceLanguage(l.localeId, l.name)];
    int rank(VoiceLanguage l) {
      final i = preferredPrefixes.indexWhere((p) => l.id.startsWith(p));
      return i == -1 ? 99 : i;
    }

    list.sort((a, b) {
      final r = rank(a).compareTo(rank(b));
      return r != 0 ? r : a.name.compareTo(b.name);
    });
    return list;
  }

  Future<String?> systemLocaleId() async => (await _stt.systemLocale())?.localeId;

  /// Best speech-recognition locale for the app language [code]
  /// (e.g. 'sw' → sw_KE). Returns null if the phone has none, so the caller
  /// can fall back. Lingala, Kikongo and Tshiluba are rarely supported yet.
  Future<VoiceLanguage?> bestLanguageFor(String code) async {
    final all = await languages();
    for (final l in all) {
      if (l.id == code || l.id.startsWith('${code}_') || l.id.startsWith('$code-')) return l;
    }
    return null;
  }

  /// Text-to-speech locale used for "Read aloud" in the text chat.
  static String defaultLocaleFor(String code) => switch (code) {
        'en' => 'en_US',
        'sw' => 'sw_KE',
        _ => 'fr_FR', // French voice for French and the beta languages
      };

  Future<void> listen({
    required String? localeId,
    required void Function(String text, bool isFinal) onResult,
  }) async {
    await _tts.stop();
    await _stt.listen(
      onResult: (SpeechRecognitionResult r) =>
          onResult(r.recognizedWords, r.finalResult),
      localeId: localeId,
      listenFor: const Duration(seconds: 45),
      pauseFor: const Duration(seconds: 3),
    );
  }

  Future<void> stopListening() => _stt.stop();

  Future<void> speak(String text, {String? localeId}) async {
    if (localeId != null) {
      // Speech recognition uses en_US, text-to-speech uses en-US.
      await _tts.setLanguage(localeId.replaceAll('_', '-'));
    }
    await _tts.speak(cleanForSpeech(text));
  }

  Future<void> stopSpeaking() async {
    await _tts.stop();
  }

  void dispose() {
    _stt.cancel();
    _tts.stop();
  }

  /// Removes markdown symbols so they are not read aloud.
  static String cleanForSpeech(String text) => text
      .replaceAll(RegExp(r'[*#_`>|]'), '')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
}
