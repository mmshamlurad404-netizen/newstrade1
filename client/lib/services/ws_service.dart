import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

/// Reconnecting WebSocket client. Windows has no official FCM support, so the
/// desktop build relies on this stream to raise in-app and toast notifications.
class WsService {
  final String baseUrl;
  final String token;

  WebSocketChannel? _channel;
  Timer? _retry;
  bool _closed = false;
  int _backoff = 1000;

  final _controller = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get stream => _controller.stream;

  WsService({required this.baseUrl, required this.token});

  Uri _uri(String path) {
    final uri = Uri.parse(baseUrl);
    return uri.replace(
      scheme: uri.scheme == 'https' ? 'wss' : 'ws',
      path: path,
      queryParameters: {if (token.isNotEmpty) 'token': token},
    );
  }

  void connect(String path) {
    _closed = false;
    _open(path);
  }

  void _open(String path) {
    if (_closed) return;
    try {
      final channel = WebSocketChannel.connect(_uri(path));
      _channel = channel;
      channel.stream.listen(
        (event) {
          _backoff = 1000;
          final data = jsonDecode(event as String) as Map<String, dynamic>;
          if (data['type'] == 'ping') return;
          _controller.add(data);
        },
        onDone: () => _schedule(path),
        onError: (_) => _schedule(path),
      );
    } catch (_) {
      _schedule(path);
    }
  }

  void _schedule(String path) {
    if (_closed) return;
    _retry?.cancel();
    _retry = Timer(Duration(milliseconds: _backoff), () => _open(path));
    _backoff = (_backoff * 2).clamp(1000, 30000);
  }

  Future<void> dispose() async {
    _closed = true;
    _retry?.cancel();
    await _channel?.sink.close();
    await _controller.close();
  }
}
