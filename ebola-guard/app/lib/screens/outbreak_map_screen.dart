import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../config.dart';
import '../l10n/l10n.dart';
import '../services/map_data.dart';
import '../services/phone.dart';
import '../widgets/emergency_banner.dart';

/// Map of areas with reported Ebola cases and of treatment centres.
/// Safety rule: people with symptoms must CALL the hotline before going
/// anywhere, so every "Directions" button asks them to call first.
class OutbreakMapScreen extends StatefulWidget {
  const OutbreakMapScreen({super.key, this.startOnList = false});

  /// Open the List tab (e.g. from an urgent result: "Find a treatment centre").
  final bool startOnList;

  @override
  State<OutbreakMapScreen> createState() => _OutbreakMapScreenState();
}

const _colorActive = Color(0xFFC62828);
const _colorNoRecent = Color(0xFFF9A825);
const _colorImported = Color(0xFF6A1B9A);
const _colorEnded = Color(0xFF757575);
const _colorCentre = Color(0xFF2E7D32);

Color _statusColor(AreaStatus s) => switch (s) {
      AreaStatus.active => _colorActive,
      AreaStatus.noRecent => _colorNoRecent,
      AreaStatus.imported => _colorImported,
      AreaStatus.ended => _colorEnded,
    };

String _statusText(AreaStatus s) => switch (s) {
      AreaStatus.active => tr('map_legend_active'),
      AreaStatus.noRecent => tr('map_legend_norecent'),
      AreaStatus.imported => tr('map_legend_imported'),
      AreaStatus.ended => tr('map_legend_ended'),
    };

String _hotline() =>
    AppConfig.healthHotline.isNotEmpty ? AppConfig.healthHotline : AppConfig.emergencyNumber;

class _OutbreakMapScreenState extends State<OutbreakMapScreen> {
  late final Future<OutbreakMapData> _future = MapDataService().load();
  late int _tab = widget.startOnList ? 1 : 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('map_title'))),
      body: Column(
        children: [
          const EmergencyBanner(),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
            child: SegmentedButton<int>(
              segments: [
                ButtonSegment(value: 0, icon: const Icon(Icons.map_outlined), label: Text(tr('map_tab_map'))),
                ButtonSegment(value: 1, icon: const Icon(Icons.list), label: Text(tr('map_tab_list'))),
              ],
              selected: {_tab},
              onSelectionChanged: (s) => setState(() => _tab = s.first),
            ),
          ),
          Expanded(
            child: FutureBuilder<OutbreakMapData>(
              future: _future,
              builder: (context, snap) {
                if (!snap.hasData) {
                  return Center(
                    child: snap.hasError
                        ? Text('${snap.error}')
                        : const CircularProgressIndicator(),
                  );
                }
                final data = snap.data!;
                return Column(children: [
                  _DataBanner(data: data),
                  Expanded(child: _tab == 0 ? _MapView(data: data) : _ListView(data: data)),
                ]);
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- banner

class _DataBanner extends StatelessWidget {
  const _DataBanner({required this.data});
  final OutbreakMapData data;

  @override
  Widget build(BuildContext context) {
    final originKey = switch (data.origin) {
      'online' => 'map_origin_online',
      'saved' => 'map_origin_saved',
      _ => 'map_origin_builtin',
    };
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${tr('map_data_as_of', {'d': data.updated})} · ${tr(originKey)}',
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          if (data.summary.isNotEmpty)
            Text(data.summary, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- map

class _MapView extends StatelessWidget {
  const _MapView({required this.data});
  final OutbreakMapData data;

  double _radiusMetres(OutbreakArea a) {
    final n = int.tryParse(a.zones.split('/').first) ?? 0;
    return switch (a.status) {
      AreaStatus.imported => 60000,
      AreaStatus.ended => 50000,
      _ => 40000.0 + 4000.0 * n,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        FlutterMap(
          options: MapOptions(
            initialCenter: LatLng(1.0, 26.0),
            initialZoom: 4.6,
            minZoom: 3,
            maxZoom: 17,
            interactionOptions: const InteractionOptions(
              flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
            ),
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'org.ebolaguard.app',
            ),
            CircleLayer(
              circles: [
                for (final a in data.areas)
                  CircleMarker(
                    point: LatLng(a.lat, a.lng),
                    radius: _radiusMetres(a),
                    useRadiusInMeter: true,
                    color: _statusColor(a.status).withValues(alpha: 0.22),
                    borderColor: _statusColor(a.status),
                    borderStrokeWidth: 2,
                  ),
              ],
            ),
            MarkerLayer(
              markers: [
                for (final a in data.areas)
                  Marker(
                    point: LatLng(a.lat, a.lng),
                    width: 130,
                    height: 30,
                    alignment: Alignment.topCenter,
                    child: GestureDetector(
                      onTap: () => showAreaSheet(context, a, data),
                      child: _AreaLabel(area: a),
                    ),
                  ),
                for (final c in data.centres)
                  Marker(
                    point: LatLng(c.lat, c.lng),
                    width: 36,
                    height: 36,
                    child: GestureDetector(
                      onTap: () => showCentreSheet(context, c),
                      child: const CircleAvatar(
                        backgroundColor: _colorCentre,
                        child: Icon(Icons.local_hospital, color: Colors.white, size: 20),
                      ),
                    ),
                  ),
              ],
            ),
            RichAttributionWidget(
              attributions: [
                TextSourceAttribution(
                  'OpenStreetMap contributors',
                  onTap: () => openLink(context, 'https://www.openstreetmap.org/copyright'),
                ),
              ],
            ),
          ],
        ),
        const Positioned(left: 8, bottom: 8, child: _Legend()),
      ],
    );
  }
}

class _AreaLabel extends StatelessWidget {
  const _AreaLabel({required this.area});
  final OutbreakArea area;

  @override
  Widget build(BuildContext context) {
    final c = _statusColor(area.status);
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: c, width: 1.5),
          boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 3)],
        ),
        child: Text(area.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: c)),
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend();

  @override
  Widget build(BuildContext context) {
    Widget row(Color c, String t, {bool centre = false}) => Padding(
          padding: const EdgeInsets.only(bottom: 3),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            centre
                ? const Icon(Icons.local_hospital, size: 14, color: _colorCentre)
                : Container(
                    width: 12,
                    height: 12,
                    decoration: BoxDecoration(
                        color: c.withValues(alpha: 0.3),
                        border: Border.all(color: c, width: 1.5),
                        shape: BoxShape.circle)),
            const SizedBox(width: 6),
            Text(t, style: const TextStyle(fontSize: 11.5, color: Colors.black87)),
          ]),
        );
    return Container(
      constraints: const BoxConstraints(maxWidth: 230),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.93),
        borderRadius: BorderRadius.circular(10),
        boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          row(_colorActive, tr('map_legend_active')),
          row(_colorNoRecent, tr('map_legend_norecent')),
          row(_colorImported, tr('map_legend_imported')),
          row(_colorEnded, tr('map_legend_ended')),
          row(_colorCentre, tr('map_legend_centre'), centre: true),
          const SizedBox(height: 2),
          Text(tr('map_circle_note'),
              style: const TextStyle(fontSize: 10.5, color: Colors.black54)),
          Text(tr('map_offline_tiles'),
              style: const TextStyle(fontSize: 10.5, color: Colors.black54)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- list

class _ListView extends StatelessWidget {
  const _ListView({required this.data});
  final OutbreakMapData data;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return ListView(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 24),
      children: [
        const _CallFirstBox(),
        const SizedBox(height: 12),
        Text(tr('map_centres'), style: text.titleMedium),
        for (final c in data.centres)
          Card(
            margin: const EdgeInsets.only(top: 8),
            child: ListTile(
              leading: const CircleAvatar(
                backgroundColor: _colorCentre,
                child: Icon(Icons.local_hospital, color: Colors.white),
              ),
              title: Text(c.name, style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text('${c.city}, ${c.province}'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => showCentreSheet(context, c),
            ),
          ),
        const SizedBox(height: 20),
        Text(tr('map_areas'), style: text.titleMedium),
        for (final a in data.areas)
          Card(
            margin: const EdgeInsets.only(top: 8),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: _statusColor(a.status).withValues(alpha: 0.18),
                child: Icon(Icons.coronavirus_outlined, color: _statusColor(a.status)),
              ),
              title: Text('${a.name}${a.country.isNotEmpty && a.country != a.name ? ' (${a.country})' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text([
                _statusText(a.status),
                if (a.zones.isNotEmpty) tr('map_zones', {'z': a.zones}),
              ].join(' · ')),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => showAreaSheet(context, a, data),
            ),
          ),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: () => openLink(context, data.sourceUrl),
          icon: const Icon(Icons.open_in_new),
          label: Text(tr('map_open_source')),
        ),
        const SizedBox(height: 4),
        Text('${tr('map_source')}: ${data.source}', style: text.bodySmall),
      ],
    );
  }
}

// ---------------------------------------------------------------- sheets

class _CallFirstBox extends StatelessWidget {
  const _CallFirstBox();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFEBEE),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _colorActive),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.phone_in_talk, color: _colorActive),
            const SizedBox(width: 8),
            Expanded(
              child: Text(tr('map_call_first'),
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, fontSize: 16, color: _colorActive)),
            ),
          ]),
          const SizedBox(height: 6),
          Text(tr('map_call_first_body'), style: const TextStyle(color: Colors.black87)),
          const SizedBox(height: 10),
          FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: _colorActive),
            onPressed: () => callNumber(context, _hotline()),
            icon: const Icon(Icons.call),
            label: Text('${tr('map_call_now')} (${_hotline()})'),
          ),
        ],
      ),
    );
  }
}

Future<void> showAreaSheet(BuildContext context, OutbreakArea a, OutbreakMapData data) {
  return showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (ctx) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(a.name, style: Theme.of(ctx).textTheme.titleLarge),
            if (a.country.isNotEmpty && a.country != a.name) Text(a.country),
            const SizedBox(height: 8),
            Chip(
              avatar: Icon(Icons.circle, size: 12, color: _statusColor(a.status)),
              label: Text(_statusText(a.status)),
            ),
            if (a.zones.isNotEmpty) Text(tr('map_zones', {'z': a.zones})),
            const SizedBox(height: 8),
            Text(a.note),
            const SizedBox(height: 12),
            Text(tr('map_data_as_of', {'d': data.updated}),
                style: Theme.of(ctx).textTheme.bodySmall),
          ],
        ),
      ),
    ),
  );
}

Future<void> showCentreSheet(BuildContext context, TreatmentCentre c) {
  return showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (ctx) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(c.name, style: Theme.of(ctx).textTheme.titleLarge),
            Text('${c.city}, ${c.province}'),
            if (c.runBy.isNotEmpty)
              Text(tr('map_run_by', {'o': c.runBy}), style: Theme.of(ctx).textTheme.bodySmall),
            const SizedBox(height: 8),
            if (c.note.isNotEmpty) Text(c.note),
            const SizedBox(height: 6),
            Text(tr('map_verified', {'d': c.verified}),
                style: Theme.of(ctx).textTheme.bodySmall),
            const SizedBox(height: 14),
            const _CallFirstBox(),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () => _confirmDirections(ctx, c),
              icon: const Icon(Icons.directions),
              label: Text(tr('map_directions')),
            ),
          ],
        ),
      ),
    ),
  );
}

Future<void> _confirmDirections(BuildContext context, TreatmentCentre c) async {
  final go = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      icon: const Icon(Icons.warning_amber_rounded, color: _colorActive),
      title: Text(tr('map_directions_confirm_title')),
      content: Text(tr('map_directions_confirm_body')),
      actions: [
        TextButton(
          onPressed: () {
            Navigator.pop(ctx, false);
            callNumber(context, _hotline());
          },
          child: Text(tr('map_call_now')),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(ctx, true),
          child: Text(tr('map_called_go')),
        ),
      ],
    ),
  );
  if (go == true && context.mounted) {
    // Opens Google Maps (or the browser) with directions from the user's
    // current location; the app itself never reads the location.
    await openLink(context,
        'https://www.google.com/maps/dir/?api=1&destination=${c.lat},${c.lng}');
  }
}
