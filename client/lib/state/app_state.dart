import 'dart:async';

import 'package:flutter/foundation.dart';

import '../config.dart';
import '../models.dart';
import '../services/api_client.dart';
import '../services/settings_store.dart';

class AppState extends ChangeNotifier {
  final SettingsStore _store = SettingsStore();

  ApiClient _api = ApiClient(baseUrl: AppConfig.defaultBaseUrl, token: '');
  Health? health;
  List<AppNotification> notifications = [];
  Timer? _notifyTimer;
  bool ready = false;

  ApiClient get api => _api;
  String get baseUrl => _api.baseUrl;
  String get token => _api.token;
  int get unreadCount => notifications.where((note) => !note.isRead).length;

  Future<void> init() async {
    final storedBaseUrl = await _store.loadBaseUrl();
    final storedToken = await _store.loadToken();
    _api = ApiClient(
      baseUrl: storedBaseUrl ?? AppConfig.defaultBaseUrl,
      token: storedToken ?? '',
    );
    await refreshHealth();
    await refreshNotifications();
    startNotificationPolling();
    ready = true;
    notifyListeners();
  }

  void startNotificationPolling({
    Duration interval = const Duration(seconds: 20),
  }) {
    _notifyTimer?.cancel();
    _notifyTimer = Timer.periodic(interval, (_) => refreshNotifications());
  }

  Future<void> updateSettings({String? baseUrl, String? token}) async {
    if (baseUrl != null) await _store.saveBaseUrl(baseUrl);
    if (token != null) await _store.saveToken(token);
    _api = ApiClient(
      baseUrl: baseUrl ?? _api.baseUrl,
      token: token ?? _api.token,
    );
    await refreshHealth();
    await refreshNotifications();
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

  Future<void> refreshNotifications() async {
    try {
      notifications = await _api.notifications(limit: 50);
    } catch (_) {
      // Keep the previous list when the backend is unreachable.
    }
    notifyListeners();
  }

  Future<void> markNotificationRead(int id) async {
    try {
      await _api.markNotificationRead(id);
    } catch (_) {}
    await refreshNotifications();
  }

  Future<void> markAllNotificationsRead() async {
    try {
      await _api.markAllNotificationsRead();
    } catch (_) {}
    await refreshNotifications();
  }

  Future<void> toggleKillSwitch() async {
    final current = health;
    if (current == null) return;
    await _api.setKillSwitch(!current.killSwitch);
    await refreshHealth();
  }

  @override
  void dispose() {
    _notifyTimer?.cancel();
    super.dispose();
  }
}
