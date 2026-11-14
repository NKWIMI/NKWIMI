import 'package:ebola_guard/l10n/l10n.dart';
import 'package:ebola_guard/l10n/strings_en.dart';
import 'package:ebola_guard/main.dart';
import 'dart:convert';

import 'package:ebola_guard/services/map_data.dart';
import 'package:ebola_guard/services/screening_engine.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:ebola_guard/services/voice_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'dart:async';

import 'package:ebola_guard/screens/home_screen.dart';
import 'package:ebola_guard/screens/sign_up_screen.dart';
import 'package:ebola_guard/services/account_service.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    L10n.lang.value = 'en';
    SharedPreferences.setMockInitialValues({});
    AccountService.profile.value = null;
    // No network in tests: the outbreak card just waits.
    HomeScreen.mapLoader = () => Completer<OutbreakMapData>().future;
  });

  group('ScreeningEngine', () {
    test('no answers -> low', () {
      expect(ScreeningEngine.evaluate({}).level, RiskLevel.low);
    });

    test('exposure only -> monitor', () {
      final r = ScreeningEngine.evaluate({'outbreak_area': true});
      expect(r.level, RiskLevel.monitor);
      expect(r.exposures, hasLength(1));
    });

    test('symptoms only -> see doctor', () {
      final r = ScreeningEngine.evaluate({'fever': true, 'headache': true});
      expect(r.level, RiskLevel.seeDoctor);
      expect(r.symptoms, hasLength(2));
    });

    test('bleeding without exposure -> see doctor today', () {
      final r = ScreeningEngine.evaluate({'bleeding': true});
      expect(r.level, RiskLevel.seeDoctor);
      expect(r.title, contains('today'));
    });

    test('exposure + symptom -> urgent, AI context in English', () {
      final r = ScreeningEngine.evaluate({'funeral': true, 'fever': true});
      expect(r.level, RiskLevel.urgent);
      expect(r.toChatContext(), contains('urgent'));
      expect(r.toChatContext(), contains('funeral'));
    });

    test('false answers are ignored', () {
      final r = ScreeningEngine.evaluate({'body_fluids': false, 'fever': false});
      expect(r.level, RiskLevel.low);
    });
  });

  group('Translations', () {
    test('French, Swahili and Lingala are complete', () {
      for (final code in ['fr', 'sw', 'ln']) {
        expect(missingKeys(code), isEmpty, reason: code);
      }
    });

    test('Kikongo and Tshiluba have every safety-critical text', () {
      const critical = ['q_', 'urgent_', 'monitor_', 'doctor_', 'low_', 'res_', 'disc_', 'scr_', 'chat_', 'voice_', 'err_', 'home_', 'map_call', 'map_directions'];
      for (final code in ['kg', 'lua']) {
        final missing = missingKeys(code).where((k) => critical.any(k.startsWith));
        expect(missing, isEmpty, reason: code);
      }
    });

    test('placeholders are kept in every language', () {
      final ph = RegExp(r'\{(\w+)\}');
      for (final l in appLanguages) {
        for (final key in stringsEn.keys) {
          final en = ph.allMatches(stringsEn[key]!).map((m) => m[1]).toSet();
          final other = ph.allMatches(trIn(l.code, key)).map((m) => m[1]).toSet();
          expect(other, en, reason: '${l.code}.$key');
        }
      }
    });

    test('screening result follows the app language', () {
      L10n.lang.value = 'fr';
      expect(ScreeningEngine.evaluate({}).title, 'Peu de risque pour le moment');
      L10n.lang.value = 'sw';
      expect(ScreeningEngine.evaluate({'outbreak_area': true}).title,
          'Fuatilia afya yako kwa siku 21');
    });

    test('beta languages fall back to French for untranslated lessons', () {
      expect(trIn('kg', 'l1_why'), trIn('fr', 'l1_why'));
    });

    test('arguments are filled in', () {
      expect(trIn('en', 'res_call', {'n': '117'}), 'Call 117');
    });
  });

  test('built-in map data loads and has areas and centres', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final raw = await rootBundle.loadString('assets/data/outbreak_map.json');
    final data = OutbreakMapData.fromJson(jsonDecode(raw) as Map<String, dynamic>, origin: 'built-in');
    expect(data.areas, isNotEmpty);
    expect(data.centres, isNotEmpty);
    expect(data.areas.first.note, isNotEmpty);
    L10n.lang.value = 'fr';
    expect(data.areas.first.note, contains('Épicentre'));
  });

  test('voice text is cleaned of markdown symbols', () {
    expect(VoiceService.cleanForSpeech('**Call** the  #hotline\n now'),
        'Call the hotline now');
  });

  testWidgets('home screen shows main actions', (tester) async {
    AppState.disclaimerAccepted = true;
    await tester.pumpWidget(const EbolaGuardApp());
    await tester.pumpAndSettle();
    expect(find.text('Start the check'), findsOneWidget);
    expect(find.text('Stay safe, stay informed'), findsOneWidget);
    expect(find.text('Assistant'), findsOneWidget); // bottom navigation
    expect(find.text('Map'), findsWidgets);
  });

  testWidgets('home screen in French', (tester) async {
    AppState.disclaimerAccepted = true;
    L10n.lang.value = 'fr';
    await tester.pumpWidget(const EbolaGuardApp());
    await tester.pumpAndSettle();
    expect(find.text('Commencer le test'), findsOneWidget);
  });

  group('Accounts', () {
    test('initials from the first name', () {
      expect(UserProfile(firstName: 'Grevi Nkwimi', createdAt: DateTime(2026)).initials, 'GN');
      expect(UserProfile(firstName: 'marie', createdAt: DateTime(2026)).initials, 'M');
      expect(UserProfile(firstName: '  ', createdAt: DateTime(2026)).initials, '?');
    });

    test('profile on the phone is saved and deleted', () async {
      await AccountService.createLocalProfile(firstName: ' Marie ', email: 'm@example.com');
      expect(AccountService.profile.value?.firstName, 'Marie');
      expect(AccountService.profile.value?.online, isFalse);

      AccountService.profile.value = null;
      await AccountService.load(); // survives an app restart
      expect(AccountService.profile.value?.email, 'm@example.com');

      await AccountService.deleteAccount();
      expect(AccountService.profile.value, isNull);
      await AccountService.load();
      expect(AccountService.profile.value, isNull);
    });

    test('online sign-up stores the session and the name', () async {
      AccountService.client = MockClient((req) async {
        expect(req.url.path, endsWith('/auth/v1/signup'));
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        expect(body['data'], {'first_name': 'Marie'});
        return http.Response(
            jsonEncode({
              'access_token': 'a',
              'refresh_token': 'r',
              'expires_in': 3600,
              'user': {
                'id': 'u1',
                'email': 'm@example.com',
                'created_at': '2026-11-13T00:00:00Z',
                'user_metadata': {'first_name': 'Marie'},
              },
            }),
            200);
      });
      final signedIn = await AccountService.signUp(
          firstName: 'Marie', email: 'm@example.com', password: 'longpassword');
      expect(signedIn, isTrue);
      expect(AccountService.profile.value?.online, isTrue);
      expect(AccountService.profile.value?.firstName, 'Marie');
    });

    test('sign-up waiting for e-mail confirmation', () async {
      AccountService.client = MockClient((req) async =>
          http.Response(jsonEncode({'id': 'u1', 'email': 'm@example.com'}), 200));
      final signedIn = await AccountService.signUp(
          firstName: 'Marie', email: 'm@example.com', password: 'longpassword');
      expect(signedIn, isFalse);
      expect(AccountService.profile.value, isNull);
    });

    test('server errors become clear messages', () async {
      Future<String> errorFor(int status, Map<String, dynamic> body) async {
        AccountService.client =
            MockClient((req) async => http.Response(jsonEncode(body), status));
        try {
          await AccountService.logIn(email: 'm@example.com', password: 'x');
        } on AccountException catch (e) {
          return e.messageKey;
        }
        return 'no error';
      }

      expect(await errorFor(400, {'error_code': 'invalid_credentials'}), 'acc_err_wrong_password');
      expect(await errorFor(422, {'error_code': 'user_already_exists'}), 'acc_err_exists');
      expect(await errorFor(429, {'msg': 'slow down'}), 'acc_err_rate');
      expect(await errorFor(500, {}), 'acc_err_generic');

      AccountService.client = MockClient((req) async => throw Exception('offline'));
      await expectLater(AccountService.logIn(email: 'a@b.co', password: 'x'),
          throwsA(isA<AccountException>()
              .having((e) => e.messageKey, 'key', 'acc_err_network')));
    });

    test('every new text exists in French, Swahili and Lingala', () {
      for (final key in ['acc_signup_title', 'acc_delete', 'profile_title', 'nav_home']) {
        for (final code in ['fr', 'sw', 'ln']) {
          expect(trIn(code, key), isNot(trIn('en', key)), reason: '$code $key');
        }
      }
    });

    testWidgets('sign-up screen works without online accounts', (tester) async {
      // A tall test screen so the whole form fits.
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(const MaterialApp(home: SignUpScreen()));
      await tester.pumpAndSettle();
      expect(find.text('Create your account'), findsOneWidget);
      expect(find.text(trIn('en', 'acc_local_note')), findsOneWidget);

      // Name is required.
      await tester.tap(find.text('Create account'));
      await tester.pumpAndSettle();
      expect(find.text('Required'), findsOneWidget);
    });
  });
}
