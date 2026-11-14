import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../l10n/l10n.dart';
import '../services/account_service.dart';
import '../theme.dart';

/// Round profile picture: the photo, else initials, else a person icon.
/// Follows the signed-in profile unless [photoPath]/[initials] are given.
class ProfileAvatar extends StatelessWidget {
  const ProfileAvatar({
    super.key,
    this.size = 44,
    this.onTap,
    this.photoPath,
    this.initials,
    this.useProfile = true,
  });

  final double size;
  final VoidCallback? onTap;
  final String? photoPath;
  final String? initials;

  /// false = show only [photoPath]/[initials] (used on the sign-up screen).
  final bool useProfile;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<UserProfile?>(
      valueListenable: AccountService.profile,
      builder: (context, p, _) {
        final photo = photoPath ?? (useProfile ? p?.photoPath : null);
        final letters = initials ?? (useProfile ? p?.initials : null);
        final hasPhoto = photo != null && File(photo).existsSync();

        Widget inner;
        if (hasPhoto) {
          inner = Image.file(File(photo!), fit: BoxFit.cover, width: size, height: size);
        } else if (letters != null && letters.isNotEmpty) {
          inner = Center(
            child: Text(letters,
                style: TextStyle(
                    fontSize: size * 0.34,
                    fontWeight: FontWeight.w800,
                    color: Ui.avatarText)),
          );
        } else {
          inner = Icon(Icons.person_outline_rounded, size: size * 0.5, color: Ui.muted);
        }

        final circle = Container(
          width: size,
          height: size,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: (letters != null && letters.isNotEmpty) || hasPhoto
                ? Ui.avatar
                : const Color(0xFFE3E9EF),
            border: Border.all(color: Colors.white, width: size >= 80 ? 4 : 2),
            boxShadow: const [
              BoxShadow(color: Color(0x220B1F33), blurRadius: 6, offset: Offset(0, 2)),
            ],
          ),
          child: inner,
        );

        if (onTap == null) return circle;
        return Semantics(
          button: true,
          label: p == null ? tr('acc_signup_title') : tr('profile_title'),
          child: InkWell(customBorder: const CircleBorder(), onTap: onTap, child: circle),
        );
      },
    );
  }
}

/// Small teal camera button placed on the corner of a big avatar.
class CameraBadge extends StatelessWidget {
  const CameraBadge({super.key, required this.onTap, required this.tooltip});
  final VoidCallback onTap;
  final String tooltip;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Ui.teal,
        shape: const CircleBorder(side: BorderSide(color: Ui.bg, width: 3)),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: onTap,
          child: const SizedBox(
            width: 40,
            height: 40,
            child: Icon(Icons.photo_camera_outlined, color: Colors.white, size: 19),
          ),
        ),
      ),
    );
  }
}

/// Result of [choosePhoto].
class PhotoChoice {
  const PhotoChoice.picked(this.path) : removed = false;
  const PhotoChoice.removed()
      : path = null,
        removed = true;
  final String? path;
  final bool removed;
}

/// Asks "camera or gallery?", then opens it. Returns null if cancelled.
Future<PhotoChoice?> choosePhoto(BuildContext context, {bool canRemove = false}) async {
  final action = await showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (ctx) => SafeArea(
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: Text(tr('photo_camera')),
              onTap: () => Navigator.pop(ctx, 'camera'),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: Text(tr('photo_gallery')),
              onTap: () => Navigator.pop(ctx, 'gallery'),
            ),
            if (canRemove)
              ListTile(
                leading: const Icon(Icons.delete_outline, color: Ui.red),
                title: Text(tr('photo_remove'), style: const TextStyle(color: Ui.red)),
                onTap: () => Navigator.pop(ctx, 'remove'),
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    ),
  );
  if (action == null) return null;
  if (action == 'remove') return const PhotoChoice.removed();
  try {
    final path = await AccountService.pickPhoto(
        action == 'camera' ? ImageSource.camera : ImageSource.gallery);
    return path == null ? null : PhotoChoice.picked(path);
  } catch (_) {
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(tr('photo_error'))));
    }
    return null;
  }
}
