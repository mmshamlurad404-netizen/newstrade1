class AppConfig {
  /// Base URL of the backend API. Override at build time with
  /// --dart-define=API_BASE_URL=https://host:port
  static const String defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8080',
  );
}
