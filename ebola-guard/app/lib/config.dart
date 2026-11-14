/// App-wide settings. Values can be overridden at build time, e.g.
///   flutter run --dart-define=BACKEND_URL=https://api.example.com
class AppConfig {
  static const appName = 'Ebola Guard';

  /// Your backend (see /backend). 10.0.2.2 = your computer, seen from the
  /// Android emulator. Use an HTTPS URL for release builds.
  static const backendUrl = String.fromEnvironment(
    'BACKEND_URL',
    defaultValue: 'http://10.0.2.2:8080',
  );

  /// Official national/regional Ebola or health hotline for your target
  /// country. Fill this in from your Ministry of Health before release.
  static const healthHotline =
      String.fromEnvironment('HEALTH_HOTLINE', defaultValue: '');
  static const healthHotlineLabel = String.fromEnvironment(
    'HEALTH_HOTLINE_LABEL',
    defaultValue: 'Health department hotline',
  );

  /// General emergency number for your target country.
  static const emergencyNumber =
      String.fromEnvironment('EMERGENCY_NUMBER', defaultValue: '112');

  /// OPTIONAL online accounts (free Supabase project, see
  /// docs/accounts-setup.md). Leave empty: profiles stay on the phone.
  static const supabaseUrl =
      String.fromEnvironment('SUPABASE_URL', defaultValue: '');
  static const supabaseAnonKey =
      String.fromEnvironment('SUPABASE_ANON_KEY', defaultValue: '');

  /// Public URL of your privacy policy (required by both app stores).
  static const privacyPolicyUrl = String.fromEnvironment(
    'PRIVACY_POLICY_URL',
    defaultValue: 'https://example.com/privacy',
  );
}

const kDisclaimerKey = 'disclaimer_accepted_v1';
