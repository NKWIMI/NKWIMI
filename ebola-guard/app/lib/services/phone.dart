import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/l10n.dart';

Future<void> callNumber(BuildContext context, String number) =>
    _launch(context, Uri(scheme: 'tel', path: number),
        tr('cannot_dial', {'n': number}));

Future<void> openLink(BuildContext context, String url) =>
    _launch(context, Uri.parse(url), tr('cannot_open', {'url': url}));

Future<void> _launch(BuildContext context, Uri uri, String failMsg) async {
  var ok = false;
  try {
    ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
  } catch (_) {
    ok = false;
  }
  if (!ok && context.mounted) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(failMsg)));
  }
}
