import 'package:flutter_test/flutter_test.dart';
import 'package:newstrade/models.dart';

void main() {
  test('Signal.fromJson parses numeric and list fields', () {
    final signal = Signal.fromJson({
      'signal_id': 's1',
      'asset': 'SOL/USDT',
      'direction': 'LONG',
      'entry_low': 145.2,
      'entry_high': 146,
      'stop_loss': 143.5,
      'take_profits': [148, 150.5],
      'confidence': 78,
      'market_risk_factor': 0.8,
      'risk_reward': 2.8,
      'status': 'active',
      'expires_at': '2026-01-01T14:00:00Z',
    });

    expect(signal.signalId, 's1');
    expect(signal.asset, 'SOL/USDT');
    expect(signal.entryLow, 145.2);
    expect(signal.takeProfits, [148.0, 150.5]);
    expect(signal.confidence, 78);
    expect(signal.expiresAt, isNotNull);
  });

  test('News.fromJson tolerates missing optional fields', () {
    final news = News.fromJson({
      'id': 1,
      'headline': 'Binance lists SOL',
      'coins': ['SOL'],
      'source_count': 3,
    });

    expect(news.coins, ['SOL']);
    expect(news.sentiment, isNull);
    expect(news.sentimentScore, isNull);
    expect(news.sourceCount, 3);
  });

  test('Portfolio.fromJson parses nested open positions', () {
    final portfolio = Portfolio.fromJson({
      'mode': 'paper',
      'equity': 10000,
      'open_risk_amount': 100,
      'open_risk_pct': 1.0,
      'open_positions': [
        {
          'id': 1,
          'mode': 'paper',
          'asset': 'SOL/USDT',
          'direction': 'LONG',
          'entry_price': 100,
          'quantity': 1.5,
        }
      ],
      'realized_pnl_total': 12.5,
      'realized_pnl_day': 2.5,
      'realized_pnl_week': 8.0,
    });

    expect(portfolio.openPositions.single.asset, 'SOL/USDT');
    expect(portfolio.realizedPnlDay, 2.5);
  });

  test('Health.fromJson parses ingestion snapshot', () {
    final health = Health.fromJson({
      'status': 'ok',
      'trading_mode': 'paper',
      'kill_switch': false,
      'ingestion': {
        'reported': true,
        'connected': true,
        'seconds_since_heartbeat': 3.5,
        'stale': false,
        'status': 'ok',
      },
    });

    expect(health.ingestion, isNotNull);
    expect(health.ingestion!.connected, isTrue);
    expect(health.ingestion!.stale, isFalse);
    expect(health.ingestion!.healthy, isTrue);
  });

  test('Health.fromJson tolerates missing ingestion', () {
    final health = Health.fromJson({
      'status': 'ok',
      'trading_mode': 'paper',
      'kill_switch': false,
    });

    expect(health.ingestion, isNull);
  });

  test('AppNotification.fromJson classifies recovery and alerts', () {
    final recovered = AppNotification.fromJson({
      'id': 1,
      'channel': 'inapp',
      'event_type': 'alert_recovered',
      'title': 'Ingestion recovered',
      'read_at': null,
      'created_at': '2026-01-01T00:00:00Z',
    });
    final alert = AppNotification.fromJson({
      'id': 2,
      'channel': 'inapp',
      'event_type': 'alert_ingestor_disconnected',
      'title': 'Ingestor disconnected',
      'read_at': '2026-01-01T01:00:00Z',
    });

    expect(recovered.isRecovery, isTrue);
    expect(recovered.isAlert, isTrue);
    expect(recovered.isRead, isFalse);
    expect(alert.isRecovery, isFalse);
    expect(alert.isRead, isTrue);
  });
}
