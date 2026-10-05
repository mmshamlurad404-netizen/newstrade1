import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config.dart';
import '../state/app_state.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _baseUrl;
  late final TextEditingController _token;

  @override
  void initState() {
    super.initState();
    final state = context.read<AppState>();
    _baseUrl = TextEditingController(text: state.baseUrl);
    _token = TextEditingController(text: state.token);
  }

  @override
  void dispose() {
    _baseUrl.dispose();
    _token.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final messenger = ScaffoldMessenger.of(context);
    await context.read<AppState>().updateSettings(
          baseUrl: _baseUrl.text.trim().isEmpty
              ? AppConfig.defaultBaseUrl
              : _baseUrl.text.trim(),
          token: _token.text.trim(),
        );
    messenger.showSnackBar(const SnackBar(content: Text('Settings saved')));
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, state, _) {
        final health = state.health;
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text('Connection', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            TextField(
              controller: _baseUrl,
              decoration: const InputDecoration(
                labelText: 'Backend base URL',
                hintText: 'http://localhost:8080',
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _token,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'API token'),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton(onPressed: _save, child: const Text('Save')),
            ),
            const Divider(height: 32),
            const Text('Trading safety', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (health == null)
              const Text('Backend unreachable.', style: TextStyle(color: Colors.redAccent))
            else ...[
              Text('Mode: ${health.tradingMode}'),
              Text('Kill switch: ${health.killSwitch ? 'ENGAGED' : 'off'}'),
              const SizedBox(height: 8),
              FilledButton.tonal(
                onPressed: () => state.toggleKillSwitch(),
                child: Text(health.killSwitch ? 'Release kill switch' : 'Engage kill switch'),
              ),
            ],
            const SizedBox(height: 16),
            const Text(
              'Exchange keys never leave the backend. Paper trading is the default; '
              'live execution requires explicit confirmation and 2FA.',
              style: TextStyle(color: Colors.white54, fontSize: 12),
            ),
          ],
        );
      },
    );
  }
}
