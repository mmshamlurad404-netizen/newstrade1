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
}
