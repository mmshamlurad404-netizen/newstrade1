import 'package:flutter/foundation.dart';

import '../config.dart';
import '../models.dart';
import '../services/api_client.dart';
import '../services/settings_store.dart';

class AppState extends ChangeNotifier {
  final SettingsStore _store = SettingsStore();

  ApiClient _api = ApiClient(baseUrl: AppConfig.defaultBaseUrl, token: '');
  Health? health;
  bool ready = false;

  ApiClient get api => _api;
  String get baseUrl => _api.baseUrl;
  String get token => _api.token;

  Future<void> init() async {
    final storedBaseUrl = await _store.loadBaseUrl();
    final storedToken = await _store.loadToken();
    _api = ApiClient(
      baseUrl: storedBaseUrl ?? AppConfig.defaultBaseUrl,
      token: storedToken ?? '',
    );
    await refreshHealth();
    ready = true;
    notifyListeners();
  }

  Future<void> updateSettings({String? baseUrl, String? token}) async {
    if (baseUrl != null) await _store.saveBaseUrl(baseUrl);
    if (token != null) await _store.saveToken(token);
    _api = ApiClient(
      baseUrl: baseUrl ?? _api.baseUrl,
      token: token ?? _api.token,
    );
    await refreshHealth();
    notifyListeners();
  }

  Future<void> refreshHealth() async {
    try {
      health = await _api.health();
    } catch (_) {
      health = null;
    }
    notifyListeners();
  }

  Future<void> toggleKillSwitch() async {
    final current = health;
    if (current == null) return;
    await _api.setKillSwitch(!current.killSwitch);
    await refreshHealth();
  }
}
