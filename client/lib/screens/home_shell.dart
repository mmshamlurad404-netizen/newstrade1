import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'channels_screen.dart';
import 'news_feed_screen.dart';
import 'portfolio_screen.dart';
import 'settings_screen.dart';
import 'signals_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  static const _titles = ['News', 'Signals', 'Portfolio', 'Channels', 'Settings'];

  @override
  Widget build(BuildContext context) {
    final health = context.watch<AppState>().health;
    return Scaffold(
      appBar: AppBar(
        title: Text('Newstrade - ${_titles[_index]}'),
        actions: [
          if (health?.killSwitch ?? false)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 8),
              child: Chip(
                label: Text('KILL', style: TextStyle(color: Colors.white)),
                backgroundColor: Colors.redAccent,
              ),
            ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Center(child: Text(health?.tradingMode ?? 'offline')),
          ),
        ],
      ),
      body: IndexedStack(
        index: _index,
        children: const [
          NewsFeedScreen(),
          SignalsScreen(),
          PortfolioScreen(),
          ChannelsScreen(),
          SettingsScreen(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.newspaper), label: 'News'),
          NavigationDestination(icon: Icon(Icons.insights), label: 'Signals'),
          NavigationDestination(icon: Icon(Icons.account_balance_wallet), label: 'Portfolio'),
          NavigationDestination(icon: Icon(Icons.groups), label: 'Channels'),
          NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}
