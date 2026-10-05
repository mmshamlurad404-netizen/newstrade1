import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models.dart';

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}

class ApiClient {
  final String baseUrl;
  final String token;

  ApiClient({required this.baseUrl, required this.token});

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token.isNotEmpty) 'Authorization': 'Bearer $token',
      };

  Uri _uri(String path, [Map<String, String>? query]) {
    final uri = Uri.parse('$baseUrl$path');
    if (query == null || query.isEmpty) return uri;
    return uri.replace(queryParameters: query);
  }

  Future<dynamic> _get(String path, [Map<String, String>? query]) async {
    final response = await http.get(_uri(path, query), headers: _headers);
    if (response.statusCode >= 400) {
      throw ApiException('${response.statusCode} ${response.reasonPhrase ?? ''}');
    }
    return jsonDecode(response.body);
  }

  Future<Health> health() async {
    return Health.fromJson(await _get('/api/health') as Map<String, dynamic>);
  }

  Future<List<News>> news({String? coin, String? eventType, String? urgency}) async {
    final query = <String, String>{
      if (coin != null && coin.isNotEmpty) 'coin': coin,
      if (eventType != null && eventType.isNotEmpty) 'event_type': eventType,
      if (urgency != null && urgency.isNotEmpty) 'urgency': urgency,
    };
    final data = await _get('/api/news', query) as List<dynamic>;
    return data.map((e) => News.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Signal>> signals({int? confidenceMin, String? direction}) async {
    final query = <String, String>{
      if (confidenceMin != null && confidenceMin > 0)
        'confidence_min': '$confidenceMin',
      if (direction != null && direction.isNotEmpty) 'direction': direction,
    };
    final data = await _get('/api/signals', query) as List<dynamic>;
    return data.map((e) => Signal.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Portfolio> portfolio() async {
    return Portfolio.fromJson(await _get('/api/portfolio') as Map<String, dynamic>);
  }

  Future<List<Trade>> trades({String? status}) async {
    final data = await _get('/api/trades', {if (status != null) 'status': status})
        as List<dynamic>;
    return data.map((e) => Trade.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Channel>> channels() async {
    final data = await _get('/api/channels') as List<dynamic>;
    return data.map((e) => Channel.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<bool> killSwitch() async {
    final data = await _get('/api/kill-switch') as Map<String, dynamic>;
    return data['kill_switch'] as bool? ?? false;
  }

  Future<bool> setKillSwitch(bool enabled) async {
    final response = await http.post(
      _uri('/api/kill-switch'),
      headers: _headers,
      body: jsonEncode({'enabled': enabled}),
    );
    if (response.statusCode >= 400) {
      throw ApiException('${response.statusCode} ${response.reasonPhrase ?? ''}');
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return data['kill_switch'] as bool? ?? enabled;
  }
}
