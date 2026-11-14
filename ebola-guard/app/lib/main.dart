import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'config.dart';
import 'l10n/l10n.dart';
import 'screens/disclaimer_screen.dart';
import 'screens/main_shell.dart';
import 'services/account_service.dart';
import 'theme.dart';

/// Small app-wide state that must survive a language change.
class AppState {
  static bool disclaimerAccepted = false;
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  AppState.disclaimerAccepted = prefs.getBool(kDisclaimerKey) ?? false;
  await L10n.load();
  await AccountService.load();
  runApp(const EbolaGuardApp());
}

class EbolaGuardApp extends StatelessWidget {
  const EbolaGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Rebuild the whole app when the language changes.
    return ValueListenableBuilder<String>(
      valueListenable: L10n.lang,
      builder: (context, code, _) => MaterialApp(
        key: ValueKey(code),
        title: AppConfig.appName,
        debugShowCheckedModeBanner: false,
        theme: buildTheme(Brightness.light),
        // The new design is light only (clear in bright sunlight).
        themeMode: ThemeMode.light,
        darkTheme: buildTheme(Brightness.dark),
        // Flutter's own widgets (Back buttons, text selection…) use French
        // for Lingala, Kikongo and Tshiluba, which Flutter doesn't include.
        locale: Locale(L10n.current.materialLocale),
        supportedLocales: const [Locale('en'), Locale('fr'), Locale('sw')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        home: AppState.disclaimerAccepted
            ? const MainShell()
            : const DisclaimerScreen(),
      ),
    );
  }
}
