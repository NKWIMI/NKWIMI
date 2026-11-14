import 'package:flutter/material.dart';

import '../l10n/l10n.dart';
import 'chat_screen.dart';
import 'home_screen.dart';
import 'info_screen.dart';
import 'outbreak_map_screen.dart';
import 'screening_screen.dart';

/// Main screen with the bottom navigation bar:
/// Home · Check · Map · Learn · Assistant.
class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  static const _home = 0, _check = 1;
  int _index = _home;

  /// Tabs are built the first time they are opened (saves data and battery).
  final _opened = <int>{_home};

  void _select(int i) {
    if (i == _check) {
      // The check is a step-by-step flow, so it opens as its own page.
      Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => const ScreeningScreen()));
      return;
    }
    setState(() {
      _index = i;
      _opened.add(i);
    });
  }

  Widget _page(int i) => switch (i) {
        0 => HomeScreen(onOpenTab: _select),
        2 => const OutbreakMapScreen(),
        3 => const InfoScreen(),
        4 => const ChatScreen(),
        _ => const SizedBox.shrink(),
      };

  @override
  Widget build(BuildContext context) {
    return PopScope(
      // Android back button: go to Home first, then leave the app.
      canPop: _index == _home,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) setState(() => _index = _home);
      },
      child: Scaffold(
        body: IndexedStack(
          index: _index,
          children: [
            for (var i = 0; i < 5; i++)
              _opened.contains(i) ? _page(i) : const SizedBox.shrink(),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: _select,
          destinations: [
            NavigationDestination(
                icon: const Icon(Icons.home_outlined),
                selectedIcon: const Icon(Icons.home_rounded),
                label: tr('nav_home')),
            NavigationDestination(
                icon: const Icon(Icons.fact_check_outlined),
                label: tr('nav_check')),
            NavigationDestination(
                icon: const Icon(Icons.map_outlined),
                selectedIcon: const Icon(Icons.map_rounded),
                label: tr('nav_map')),
            NavigationDestination(
                icon: const Icon(Icons.menu_book_outlined),
                selectedIcon: const Icon(Icons.menu_book_rounded),
                label: tr('nav_learn')),
            NavigationDestination(
                icon: const Icon(Icons.chat_bubble_outline_rounded),
                selectedIcon: const Icon(Icons.chat_bubble_rounded),
                label: tr('nav_assistant')),
          ],
        ),
      ),
    );
  }
}
