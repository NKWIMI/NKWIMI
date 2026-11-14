import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config.dart';

/// The person using the app. Accounts are OPTIONAL: every safety feature
/// (check, map, hotline, lessons) works without one.
///
/// Privacy rule: an account only holds first name, e-mail and – on the phone
/// only – a profile picture. Check answers are never added to it.
class UserProfile {
  const UserProfile({
    required this.firstName,
    required this.createdAt,
    this.email = '',
    this.photoPath,
    this.online = false,
    this.userId,
  });

  final String firstName;
  final String email;

  /// Profile picture file on this phone (never uploaded).
  final String? photoPath;
  final DateTime createdAt;

  /// true = online account (Supabase), false = profile saved on this phone.
  final bool online;
  final String? userId;

  String get initials {
    final parts = firstName
        .trim()
        .split(RegExp(r'\s+'))
        .where((p) => p.isNotEmpty)
        .toList();
    if (parts.isEmpty) return '?';
    final first = parts.first.substring(0, 1);
    final second = parts.length > 1 ? parts[1].substring(0, 1) : '';
    return (first + second).toUpperCase();
  }

  UserProfile copyWith({String? firstName, String? photoPath, bool clearPhoto = false}) =>
      UserProfile(
        firstName: firstName ?? this.firstName,
        email: email,
        photoPath: clearPhoto ? null : (photoPath ?? this.photoPath),
        createdAt: createdAt,
        online: online,
        userId: userId,
      );

  Map<String, dynamic> toJson() => {
        'firstName': firstName,
        'email': email,
        'photoPath': photoPath,
        'createdAt': createdAt.toIso8601String(),
        'online': online,
        'userId': userId,
      };

  factory UserProfile.fromJson(Map<String, dynamic> j) => UserProfile(
        firstName: j['firstName'] as String? ?? '',
        email: j['email'] as String? ?? '',
        photoPath: j['photoPath'] as String?,
        createdAt: DateTime.tryParse(j['createdAt'] as String? ?? '') ?? DateTime.now(),
        online: j['online'] as bool? ?? false,
        userId: j['userId'] as String?,
      );
}

/// Error with a translation key (see strings_*.dart, keys "acc_err_…").
class AccountException implements Exception {
  AccountException(this.messageKey, [this.detail]);
  final String messageKey;
  final String? detail;

  @override
  String toString() => 'AccountException($messageKey, $detail)';
}

class AccountService {
  AccountService._();

  /// The signed-in person, or null. Widgets listen to it.
  static final ValueNotifier<UserProfile?> profile = ValueNotifier(null);

  /// Online accounts are on when SUPABASE_URL and SUPABASE_ANON_KEY are set
  /// in config/release.json (see docs/accounts-setup.md). Otherwise the
  /// profile is simply saved on this phone.
  static bool get onlineAccounts =>
      AppConfig.supabaseUrl.isNotEmpty && AppConfig.supabaseAnonKey.isNotEmpty;

  /// Replaceable in tests.
  @visibleForTesting
  static http.Client client = http.Client();

  static const _profileKey = 'user_profile_v1';
  static const _sessionKey = 'user_session_v1';
  static const _checksKey = 'checks_done';
  static const _pendingPhotoKey = 'pending_photo';
  static String _photoKey(String userId) => 'photo_$userId';

  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_profileKey);
    if (raw == null) return;
    try {
      profile.value = UserProfile.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      await prefs.remove(_profileKey);
    }
  }

  static Future<void> _save(UserProfile? p) async {
    final prefs = await SharedPreferences.getInstance();
    if (p == null) {
      await prefs.remove(_profileKey);
    } else {
      await prefs.setString(_profileKey, jsonEncode(p.toJson()));
      if (p.online && p.userId != null) {
        if (p.photoPath != null) {
          await prefs.setString(_photoKey(p.userId!), p.photoPath!);
        } else {
          await prefs.remove(_photoKey(p.userId!));
        }
      }
    }
    profile.value = p;
  }

  // ---------------------------------------------------------------- counters

  static Future<int> checksDone() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getInt(_checksKey) ?? 0;
    } catch (_) {
      return 0;
    }
  }

  static Future<void> recordCheck() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(_checksKey, (prefs.getInt(_checksKey) ?? 0) + 1);
    } catch (_) {}
  }

  // ------------------------------------------------------------------ photos

  /// Opens the camera or the gallery and copies the picture into the app's
  /// private folder. Returns the new file path, or null if cancelled.
  static Future<String?> pickPhoto(ImageSource source) async {
    final XFile? picked = await ImagePicker().pickImage(
      source: source,
      maxWidth: 600,
      maxHeight: 600,
      imageQuality: 85,
      preferredCameraDevice: CameraDevice.front,
    );
    if (picked == null) return null;
    final dir = await getApplicationDocumentsDirectory();
    final name = picked.name;
    final ext = name.contains('.') ? name.substring(name.lastIndexOf('.')) : '.jpg';
    final target = '${dir.path}/avatar_${DateTime.now().millisecondsSinceEpoch}$ext';
    await picked.saveTo(target);
    return target;
  }

  static Future<void> _deleteFile(String? path) async {
    if (path == null) return;
    try {
      final f = File(path);
      if (await f.exists()) await f.delete();
    } catch (_) {}
  }

  /// Deletes a picture chosen on the sign-up screen that was not used.
  static Future<void> discardPhoto(String? path) => _deleteFile(path);

  /// Sets (or with null, removes) the profile picture.
  static Future<void> setPhoto(String? path) async {
    final p = profile.value;
    if (p == null) return;
    if (p.photoPath != null && p.photoPath != path) await _deleteFile(p.photoPath);
    await _save(path == null ? p.copyWith(clearPhoto: true) : p.copyWith(photoPath: path));
  }

  // ----------------------------------------------------- profile on the phone

  static Future<void> createLocalProfile({
    required String firstName,
    String email = '',
    String? photoPath,
  }) =>
      _save(UserProfile(
        firstName: firstName.trim(),
        email: email.trim(),
        photoPath: photoPath,
        createdAt: DateTime.now(),
      ));

  static Future<void> updateName(String firstName) async {
    final p = profile.value;
    if (p == null) return;
    final name = firstName.trim();
    if (name.isEmpty) return;
    if (p.online) {
      final token = await _freshToken();
      await _send('PUT', _auth('user'), {
        'data': {'first_name': name}
      }, token: token);
    }
    await _save(p.copyWith(firstName: name));
  }

  // ------------------------------------------------- online accounts (Supabase)

  static Uri _auth(String path) =>
      Uri.parse('${AppConfig.supabaseUrl}/auth/v1/$path');

  static Map<String, String> _headers(String? token) => {
        'apikey': AppConfig.supabaseAnonKey,
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  static Future<Map<String, dynamic>> _send(
    String method,
    Uri uri,
    Map<String, dynamic> body, {
    String? token,
  }) async {
    http.Response res;
    try {
      final request = http.Request(method, uri)
        ..headers.addAll(_headers(token))
        ..body = jsonEncode(body);
      res = await http.Response.fromStream(
          await client.send(request).timeout(const Duration(seconds: 20)));
    } catch (_) {
      throw AccountException('acc_err_network');
    }
    Map<String, dynamic> json = {};
    try {
      final decoded = jsonDecode(utf8.decode(res.bodyBytes));
      if (decoded is Map<String, dynamic>) json = decoded;
    } catch (_) {}
    if (res.statusCode >= 200 && res.statusCode < 300) return json;

    final code = '${json['error_code'] ?? json['error'] ?? json['code'] ?? ''}';
    final msg = '${json['msg'] ?? json['error_description'] ?? json['message'] ?? ''}';
    final lower = msg.toLowerCase();
    if (code == 'invalid_credentials' || code == 'invalid_grant') {
      throw AccountException('acc_err_wrong_password');
    }
    if (code == 'user_already_exists' ||
        code == 'email_exists' ||
        lower.contains('already registered')) {
      throw AccountException('acc_err_exists');
    }
    if (code == 'weak_password' || lower.contains('password should')) {
      throw AccountException('acc_err_weak');
    }
    if (code == 'email_not_confirmed' || lower.contains('not confirmed')) {
      throw AccountException('acc_err_confirm');
    }
    if (res.statusCode == 429 || code.startsWith('over_')) {
      throw AccountException('acc_err_rate');
    }
    throw AccountException('acc_err_generic', msg.isEmpty ? 'HTTP ${res.statusCode}' : msg);
  }

  /// Creates an online account. Returns true when the person is signed in,
  /// false when they must first click the link in the confirmation e-mail.
  static Future<bool> signUp({
    required String firstName,
    required String email,
    required String password,
    String? photoPath,
  }) async {
    final body = await _send('POST', _auth('signup'), {
      'email': email.trim(),
      'password': password,
      'data': {'first_name': firstName.trim()},
    });
    if (body['access_token'] == null) {
      // E-mail confirmation is on: keep the picture for the first log-in.
      final prefs = await SharedPreferences.getInstance();
      if (photoPath != null) await prefs.setString(_pendingPhotoKey, photoPath);
      return false;
    }
    await _storeSession(body, photoPath: photoPath);
    return true;
  }

  static Future<void> logIn({required String email, required String password}) async {
    final body = await _send('POST', _auth('token?grant_type=password'), {
      'email': email.trim(),
      'password': password,
    });
    await _storeSession(body);
  }

  static Future<void> sendPasswordReset(String email) =>
      _send('POST', _auth('recover'), {'email': email.trim()});

  static Future<void> _storeSession(Map<String, dynamic> body, {String? photoPath}) async {
    final prefs = await SharedPreferences.getInstance();
    final user = (body['user'] as Map?)?.cast<String, dynamic>() ?? const {};
    final id = user['id'] as String?;
    final meta = (user['user_metadata'] as Map?)?.cast<String, dynamic>() ?? const {};
    final email = user['email'] as String? ?? '';
    final expiresIn = (body['expires_in'] as num?)?.toInt() ?? 3600;
    await prefs.setString(
        _sessionKey,
        jsonEncode({
          'access_token': body['access_token'],
          'refresh_token': body['refresh_token'],
          'expires_at': DateTime.now()
                  .add(Duration(seconds: expiresIn))
                  .millisecondsSinceEpoch,
        }));

    var photo = photoPath ?? (id == null ? null : prefs.getString(_photoKey(id)));
    final pending = prefs.getString(_pendingPhotoKey);
    if (photo == null && pending != null) photo = pending;
    await prefs.remove(_pendingPhotoKey);
    if (photo != null && !File(photo).existsSync()) photo = null;

    final name = (meta['first_name'] as String?)?.trim();
    await _save(UserProfile(
      firstName: (name == null || name.isEmpty) ? email.split('@').first : name,
      email: email,
      photoPath: photo,
      createdAt: DateTime.tryParse(user['created_at'] as String? ?? '') ?? DateTime.now(),
      online: true,
      userId: id,
    ));
  }

  /// A valid access token, refreshed if it has expired.
  static Future<String> _freshToken() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_sessionKey);
    if (raw == null) throw AccountException('acc_err_generic', 'not signed in');
    final s = jsonDecode(raw) as Map<String, dynamic>;
    final expiresAt = (s['expires_at'] as num?)?.toInt() ?? 0;
    if (DateTime.now().millisecondsSinceEpoch < expiresAt - 60000) {
      return s['access_token'] as String;
    }
    final body = await _send('POST', _auth('token?grant_type=refresh_token'),
        {'refresh_token': s['refresh_token']});
    await _storeSession(body, photoPath: profile.value?.photoPath);
    return body['access_token'] as String;
  }

  static Future<void> logOut() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_sessionKey);
    if (raw != null) {
      try {
        final token = (jsonDecode(raw) as Map<String, dynamic>)['access_token'] as String?;
        await _send('POST', _auth('logout'), {}, token: token);
      } catch (_) {
        // Already expired or offline: removing the session below is enough.
      }
    }
    await prefs.remove(_sessionKey);
    await _save(null); // the picture stays on the phone for the next log-in
  }

  /// Deletes the account for good (required by Google Play), including the
  /// profile picture. Check history is not part of the account.
  static Future<void> deleteAccount() async {
    final p = profile.value;
    if (p == null) return;
    if (p.online) {
      final token = await _freshToken();
      await _send('POST',
          Uri.parse('${AppConfig.supabaseUrl}/rest/v1/rpc/delete_my_account'), {},
          token: token);
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_sessionKey);
      if (p.userId != null) await prefs.remove(_photoKey(p.userId!));
    }
    await _deleteFile(p.photoPath);
    await _save(null);
  }
}
