import 'package:flutter/material.dart';

import '../l10n/l10n.dart';
import '../services/phone.dart';

/// Education: prevention lessons, facts & myths (offline), plus videos and
/// trusted links (need internet). Texts live in lib/l10n (keys l1_…, f1_…,
/// vid1_…, link1_…). Have a health professional review them, and check that
/// the links still work before each release.
class InfoScreen extends StatelessWidget {
  const InfoScreen({super.key, this.initialTab = 0});

  final int initialTab;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      initialIndex: initialTab,
      child: Scaffold(
        appBar: AppBar(
          title: Text(tr('learn_title')),
          bottom: TabBar(
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            tabs: [
              Tab(icon: const Icon(Icons.shield_outlined), text: tr('tab_prevention')),
              Tab(icon: const Icon(Icons.menu_book_outlined), text: tr('tab_facts')),
              Tab(icon: const Icon(Icons.play_circle_outline), text: tr('tab_videos')),
              Tab(icon: const Icon(Icons.link), text: tr('tab_links')),
            ],
          ),
        ),
        body: const TabBarView(children: [
          _PreventionTab(),
          _FactsTab(),
          _VideosTab(),
          _LinksTab(),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- Prevention

class _Lesson {
  const _Lesson(this.icon, this.key, this.steps);
  final IconData icon;
  final String key; // l1 … l7
  final int steps;

  String get title => tr('${key}_title');
  String get why => tr('${key}_why');
  List<String> get stepTexts => [for (var i = 1; i <= steps; i++) tr('${key}_s$i')];
}

const _lessons = <_Lesson>[
  _Lesson(Icons.wash_outlined, 'l1', 3),
  _Lesson(Icons.do_not_touch_outlined, 'l2', 3),
  _Lesson(Icons.local_hospital_outlined, 'l3', 3),
  _Lesson(Icons.volunteer_activism_outlined, 'l4', 2),
  _Lesson(Icons.pets_outlined, 'l5', 2),
  _Lesson(Icons.vaccines_outlined, 'l6', 2),
  _Lesson(Icons.favorite_border, 'l7', 2),
];

class _PreventionTab extends StatelessWidget {
  const _PreventionTab();

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 4, 4, 12),
          child: Text(tr('prev_heading'), style: text.titleMedium),
        ),
        for (final (i, l) in _lessons.indexed)
          Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: ExpansionTile(
              leading: CircleAvatar(
                backgroundColor: scheme.primaryContainer,
                child: Icon(l.icon, color: scheme.onPrimaryContainer),
              ),
              title: Text('${i + 1}. ${l.title}',
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text(l.why),
              childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              children: [
                for (final s in l.stepTexts)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.check, size: 18, color: scheme.primary),
                        const SizedBox(width: 8),
                        Expanded(child: Text(s)),
                      ],
                    ),
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

// ---------------------------------------------------------------- Facts

class _FactsTab extends StatelessWidget {
  const _FactsTab();

  // (key prefix, icon, number of points)
  static const _sections = <(String, IconData, int)>[
    ('f1', Icons.info_outline, 3),
    ('f2', Icons.share_outlined, 4),
    ('f3', Icons.thermostat, 4),
    ('f4', Icons.report_gmailerrorred_outlined, 5),
  ];

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        for (final (key, icon, count) in _sections)
          ExpansionTile(
            initiallyExpanded: key == 'f4',
            leading: Icon(icon),
            title: Text(tr('${key}_title'), style: text.titleMedium),
            childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            children: [
              for (var i = 1; i <= count; i++)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('•  '),
                      Expanded(child: Text(tr('${key}_p$i'))),
                    ],
                  ),
                ),
            ],
          ),
      ],
    );
  }
}

// ---------------------------------------------------------------- Videos

class _Video {
  const _Video({
    required this.key,
    required this.source,
    required this.url,
    this.youtubeId,
  });

  final String key; // vid1 … vid5
  final String source;
  final String url;

  /// When set, a thumbnail is loaded from YouTube.
  final String? youtubeId;

  String get title => tr('${key}_title');
  String get description => tr('${key}_desc');
}

const _videos = <_Video>[
  _Video(
    key: 'vid1',
    source: 'Global Health Media',
    url: 'https://www.youtube.com/watch?v=TZI-FayZkvg',
    youtubeId: 'TZI-FayZkvg',
  ),
  _Video(
    key: 'vid2',
    source: 'World Health Organization',
    url: 'https://www.youtube.com/watch?v=qnvlQHJkBBY',
    youtubeId: 'qnvlQHJkBBY',
  ),
  _Video(
    key: 'vid3',
    source: 'SAWBO (Scientific Animations Without Borders)',
    url: 'https://sawbo-animations.org/441',
  ),
  _Video(
    key: 'vid4',
    source: 'World Health Organization',
    url: 'https://www.youtube.com/watch?v=_eoQtEy_7NI',
    youtubeId: '_eoQtEy_7NI',
  ),
  _Video(
    key: 'vid5',
    source: 'WHO Africa (2026)',
    url:
        'https://www.afro.who.int/media-centre/multimedia/inside-ebola-response-building-trust-protecting-health-workers-and-saving',
  ),
];

class _VideosTab extends StatelessWidget {
  const _VideosTab();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 4, 4, 12),
          child: Text(tr('vid_intro')),
        ),
        for (final v in _videos) _VideoCard(video: v),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: () => openLink(context,
              'https://www.youtube.com/results?search_query=WHO+Ebola+prevention'),
          icon: const Icon(Icons.search),
          label: Text(tr('vid_more')),
        ),
      ],
    );
  }
}

class _VideoCard extends StatelessWidget {
  const _VideoCard({required this.video});
  final _Video video;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final placeholder = Container(
      color: scheme.surfaceContainerHighest,
      alignment: Alignment.center,
      child: Icon(Icons.ondemand_video, size: 48, color: scheme.primary),
    );
    return Card(
      clipBehavior: Clip.antiAlias,
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => openLink(context, video.url),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AspectRatio(
              aspectRatio: 16 / 9,
              child: Stack(fit: StackFit.expand, children: [
                if (video.youtubeId != null)
                  Image.network(
                    'https://img.youtube.com/vi/${video.youtubeId}/hqdefault.jpg',
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stack) => placeholder,
                  )
                else
                  placeholder,
                const Center(
                  child: CircleAvatar(
                    radius: 28,
                    backgroundColor: Colors.black54,
                    child: Icon(Icons.play_arrow, color: Colors.white, size: 36),
                  ),
                ),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(video.title,
                      style: const TextStyle(
                          fontWeight: FontWeight.w600, fontSize: 16)),
                  const SizedBox(height: 2),
                  Text(video.source,
                      style: TextStyle(color: scheme.primary, fontSize: 13)),
                  const SizedBox(height: 6),
                  Text(video.description),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- Links

// (title – kept as the organisation's own name, description key, url)
const _links = <(String, String, String)>[
  ('WHO – Ebola', 'link1_desc', 'https://www.who.int/health-topics/ebola'),
  ('WHO Africa – Ebola', 'link2_desc', 'https://www.afro.who.int/health-topics/ebola-disease'),
  ('US CDC – Ebola', 'link3_desc', 'https://www.cdc.gov/ebola/'),
  ('CDC – After travel', 'link4_desc', 'https://www.cdc.gov/ebola/travel/index.html'),
  ('Global Health Media – Ebola', 'link5_desc', 'https://globalhealthmedia.org/portfolio_category/ebola/'),
];

class _LinksTab extends StatelessWidget {
  const _LinksTab();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        for (final (title, descKey, url) in _links)
          Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: ListTile(
              leading: const Icon(Icons.public),
              title: Text(title,
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text(tr(descKey)),
              trailing: const Icon(Icons.open_in_new),
              onTap: () => openLink(context, url),
            ),
          ),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Text(tr('links_footer'), textAlign: TextAlign.center),
        ),
      ],
    );
  }
}
