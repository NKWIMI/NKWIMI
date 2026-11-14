import 'package:flutter/material.dart';

/// Brand colours. Change these to restyle the whole app.
class Brand {
  static const primary = Color(0xFF0E7C6B); // teal – trust, health
  static const primaryDark = Color(0xFF0A5F52);
  static const accent = Color(0xFFFFB300); // warm amber – highlights
  static const danger = Color(0xFFC62828); // emergencies only

  static const headerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF12907C), Color(0xFF0A5F52)],
  );
}

/// Colours of the new design (light, calm, high contrast).
class Ui {
  static const ink = Color(0xFF0B1F33); // main text
  static const muted = Color(0xFF5B6B7B); // secondary text
  static const bg = Color(0xFFF3F6F9); // page background
  static const line = Color(0xFFDCE3EA); // borders
  static const teal = Color(0xFF0E7C6B);
  static const red = Color(0xFFC62828);
  static const amber = Color(0xFFE0A100);
  static const purple = Color(0xFF6A1B9A);
  static const blue = Color(0xFF1565C0);
  static const green = Color(0xFF1B7A3E);
  static const avatar = Color(0xFFFFD8B5);
  static const avatarText = Color(0xFF7A3A00);

  static BoxDecoration card({Color color = Colors.white, double radius = 20}) =>
      BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(radius),
        boxShadow: const [
          BoxShadow(color: Color(0x0F0B1F33), blurRadius: 4, offset: Offset(0, 1)),
        ],
      );
}

ThemeData buildTheme(Brightness brightness) {
  final scheme = ColorScheme.fromSeed(
    seedColor: Brand.primary,
    brightness: brightness,
    primary: brightness == Brightness.light ? Brand.primary : null,
    error: brightness == Brightness.light ? Brand.danger : null,
  );
  final base = ThemeData(useMaterial3: true, colorScheme: scheme);
  final text = base.textTheme;

  return base.copyWith(
    scaffoldBackgroundColor: brightness == Brightness.light
        ? Ui.bg
        : scheme.surface,
    textTheme: text.copyWith(
      headlineSmall: text.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
      titleLarge: text.titleLarge?.copyWith(fontWeight: FontWeight.w700),
      titleMedium: text.titleMedium?.copyWith(fontWeight: FontWeight.w600),
      bodyMedium: text.bodyMedium?.copyWith(height: 1.4),
    ),
    appBarTheme: AppBarTheme(
      centerTitle: false,
      elevation: 0,
      scrolledUnderElevation: 1,
      backgroundColor: brightness == Brightness.light ? Ui.bg : scheme.surface,
      titleTextStyle: text.titleLarge?.copyWith(
        fontWeight: FontWeight.w700,
        color: scheme.onSurface,
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surfaceContainerHighest.withValues(alpha: 0.5),
      border: const OutlineInputBorder(
        borderRadius: BorderRadius.all(Radius.circular(24)),
        borderSide: BorderSide.none,
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: brightness == Brightness.light ? Colors.white : null,
      indicatorColor: Brand.primary.withValues(alpha: 0.14),
      height: 68,
      labelTextStyle: WidgetStateProperty.resolveWith((states) => TextStyle(
            fontSize: 12,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w700
                : FontWeight.w500,
          )),
    ),
  );
}

/// Colours used for screening result levels.
class RiskColors {
  static const urgent = Color(0xFFC62828);
  static const monitor = Color(0xFFEF6C00);
  static const seeDoctor = Color(0xFF1565C0);
  static const low = Color(0xFF2E7D32);
}

/// Rounded white card used across the app.
class SoftCard extends StatelessWidget {
  const SoftCard({
    super.key,
    required this.child,
    this.onTap,
    this.color,
    this.padding = const EdgeInsets.all(16),
  });

  final Widget child;
  final VoidCallback? onTap;
  final Color? color;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: color ?? scheme.surface,
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      elevation: 0,
      child: InkWell(
        onTap: onTap,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.5)),
          ),
          padding: padding,
          child: child,
        ),
      ),
    );
  }
}
