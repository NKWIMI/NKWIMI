import 'dart:ui' show PlatformDispatcher;

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'strings_en.dart';
import 'strings_fr.dart';
import 'strings_kg.dart';
import 'strings_ln.dart';
import 'strings_lua.dart';
import 'strings_sw.dart';

class AppLanguage {
  const AppLanguage({
    required this.code,
    required this.name,
    required this.englishName,
    required this.materialLocale,
    this.beta = false,
  });

  /// Our own code for the language (ISO 639).
  final String code;

  /// Name shown in the picker, in the language itself.
  final String name;

  /// Name sent to the AI so it answers in this language.
  final String englishName;

  /// Locale used for Flutter's built-in widgets (dates, "Back" tooltips…).
  /// Flutter has no Lingala, Kikongo or Tshiluba, so those use French.
  final String materialLocale;

  /// True = translation not yet reviewed by native speakers.
  final bool beta;
}

const appLanguages = <AppLanguage>[
  AppLanguage(code: 'en', name: 'English', englishName: 'English', materialLocale: 'en'),
  AppLanguage(code: 'fr', name: 'Français', englishName: 'French', materialLocale: 'fr'),
  AppLanguage(code: 'ln', name: 'Lingála', englishName: 'Lingala', materialLocale: 'fr', beta: true),
  AppLanguage(code: 'kg', name: 'Kikongo', englishName: 'Kikongo (Kikongo ya Leta)', materialLocale: 'fr', beta: true),
  AppLanguage(code: 'lua', name: 'Tshiluba', englishName: 'Tshiluba', materialLocale: 'fr', beta: true),
  AppLanguage(code: 'sw', name: 'Kiswahili', englishName: 'Swahili', materialLocale: 'sw'),
];

const Map<String, Map<String, String>> _tables = {
  'en': stringsEn,
  'fr': stringsFr,
  'ln': stringsLn,
  'kg': stringsKg,
  'lua': stringsLua,
  'sw': stringsSw,
};

class L10n {
  static const _prefKey = 'app_language';

  /// The current language code. Widgets listen to it to rebuild.
  static final ValueNotifier<String> lang = ValueNotifier('en');

  static AppLanguage get current =>
      appLanguages.firstWhere((l) => l.code == lang.value, orElse: () => appLanguages.first);

  /// Whether the user has picked a language yet (first launch shows a picker).
  static bool chosen = false;

  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_prefKey);
    if (saved != null && _tables.containsKey(saved)) {
      lang.value = saved;
      chosen = true;
      return;
    }
    // First launch: use the phone's language when we have it.
    final device = PlatformDispatcher.instance.locale.languageCode;
    lang.value = _tables.containsKey(device) ? device : 'en';
  }

  static Future<void> set(String code) async {
    if (!_tables.containsKey(code)) return;
    chosen = true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKey, code);
    lang.value = code;
  }
}

/// Translate [key] into the current language.
/// Missing text falls back to French (for the beta languages), then English.
String tr(String key, [Map<String, String>? args]) => trIn(L10n.lang.value, key, args);

/// Translate [key] into a specific language (e.g. English for the AI context).
String trIn(String code, String key, [Map<String, String>? args]) {
  final lang = appLanguages.firstWhere((l) => l.code == code, orElse: () => appLanguages.first);
  var s = _tables[code]?[key] ??
      (lang.beta ? stringsFr[key] : null) ??
      stringsEn[key] ??
      key;
  if (args != null) {
    args.forEach((k, v) => s = s.replaceAll('{$k}', v));
  }
  return s;
}

/// For tests: keys that a language is missing compared with English.
@visibleForTesting
List<String> missingKeys(String code) =>
    [for (final k in stringsEn.keys) if (!(_tables[code]?.containsKey(k) ?? false)) k];
