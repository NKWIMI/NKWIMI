import 'dart:async';
import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../config.dart';
import '../l10n/l10n.dart';

enum AreaStatus { active, noRecent, imported, ended }

/// Picks the text for the app language from {"en": …, "fr": …}.
String _localized(Object? v) {
  if (v is String) return v;
  if (v is! Map) return '';
  final code = L10n.lang.value;
  return (v[code] ?? (L10n.current.beta ? v['fr'] : null) ?? v['en'] ?? v['fr'] ?? '')
      .toString();
}

class OutbreakArea {
  OutbreakArea.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        name = j['name'] as String,
        country = j['country'] as String? ?? '',
        lat = (j['lat'] as num).toDouble(),
        lng = (j['lng'] as num).toDouble(),
        status = AreaStatus.values.firstWhere((s) => s.name == j['status'],
            orElse: () => AreaStatus.active),
        zones = j['zones'] as String? ?? '',
        _note = j['note'];

  final String id, name, country, zones;
  final double lat, lng;
  final AreaStatus status;
  final Object? _note;
  String get note => _localized(_note);
}

class TreatmentCentre {
  TreatmentCentre.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        name = j['name'] as String,
        runBy = j['operator'] as String? ?? '',
        city = j['city'] as String? ?? '',
        province = j['province'] as String? ?? '',
        lat = (j['lat'] as num).toDouble(),
        lng = (j['lng'] as num).toDouble(),
        verified = j['verified'] as String? ?? '',
        _note = j['note'];

  final String id, name, runBy, city, province, verified;
  final double lat, lng;
  final Object? _note;
  String get note => _localized(_note);
}

class OutbreakMapData {
  OutbreakMapData.fromJson(Map<String, dynamic> j, {required this.origin})
      : updated = j['updated'] as String? ?? '',
        source = j['source'] as String? ?? '',
        sourceUrl = j['sourceUrl'] as String? ?? '',
        _summary = j['summary'],
        areas = [
          for (final a in (j['areas'] as List? ?? const []))
            OutbreakArea.fromJson(a as Map<String, dynamic>)
        ],
        centres = [
          for (final c in (j['centres'] as List? ?? const []))
            TreatmentCentre.fromJson(c as Map<String, dynamic>)
        ];

  final String updated, source, sourceUrl;
  final Object? _summary;
  final List<OutbreakArea> areas;
  final List<TreatmentCentre> centres;

  /// 'online', 'saved' or 'built-in' – shown to the user.
  final String origin;

  String get summary => _localized(_summary);
}

/// Loads the map data: latest from the backend if reachable, otherwise the
/// last copy saved on the phone, otherwise the copy built into the app.
class MapDataService {
  static const _cacheKey = 'outbreak_map_cache';
  static const _asset = 'assets/data/outbreak_map.json';

  Future<OutbreakMapData> load({http.Client? client}) async {
    final prefs = await SharedPreferences.getInstance();
    try {
      final res = await (client ?? http.Client())
          .get(Uri.parse('${AppConfig.backendUrl}/api/outbreak-map'))
          .timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        final body = utf8.decode(res.bodyBytes);
        final data = OutbreakMapData.fromJson(
            jsonDecode(body) as Map<String, dynamic>,
            origin: 'online');
        if (data.areas.isNotEmpty) {
          await prefs.setString(_cacheKey, body);
          return data;
        }
      }
    } catch (_) {
      // offline or backend not running – fall through
    }
    final cached = prefs.getString(_cacheKey);
    if (cached != null) {
      try {
        return OutbreakMapData.fromJson(
            jsonDecode(cached) as Map<String, dynamic>,
            origin: 'saved');
      } catch (_) {}
    }
    final bundled = await rootBundle.loadString(_asset);
    return OutbreakMapData.fromJson(
        jsonDecode(bundled) as Map<String, dynamic>,
        origin: 'built-in');
  }
}
