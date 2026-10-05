double? _toDouble(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  return double.tryParse(value.toString());
}

DateTime? _toDate(dynamic value) {
  if (value == null) return null;
  return DateTime.tryParse(value.toString());
}

class News {
  final int id;
  final String headline;
  final List<String> coins;
  final String? eventType;
  final String? sentiment;
  final double? sentimentScore;
  final String? urgency;
  final int sourceCount;
  final String? originChannel;
  final DateTime? firstSeenAt;

  News({
    required this.id,
    required this.headline,
    required this.coins,
    this.eventType,
    this.sentiment,
    this.sentimentScore,
    this.urgency,
    this.sourceCount = 1,
    this.originChannel,
    this.firstSeenAt,
  });

  factory News.fromJson(Map<String, dynamic> json) => News(
        id: json['id'] as int,
        headline: json['headline'] as String? ?? '',
        coins: (json['coins'] as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
        eventType: json['event_type'] as String?,
        sentiment: json['sentiment'] as String?,
        sentimentScore: _toDouble(json['sentiment_score']),
        urgency: json['urgency'] as String?,
        sourceCount: (json['source_count'] as num?)?.toInt() ?? 1,
        originChannel: json['origin_channel'] as String?,
        firstSeenAt: _toDate(json['first_seen_at']),
      );
}

class Signal {
  final String signalId;
  final String asset;
  final String direction;
  final double entryLow;
  final double entryHigh;
  final double stopLoss;
  final List<double> takeProfits;
  final int confidence;
  final double marketRiskFactor;
  final double? riskReward;
  final String? rationale;
  final String status;
  final DateTime? expiresAt;

  Signal({
    required this.signalId,
    required this.asset,
    required this.direction,
    required this.entryLow,
    required this.entryHigh,
    required this.stopLoss,
    required this.takeProfits,
    required this.confidence,
    this.marketRiskFactor = 1.0,
    this.riskReward,
    this.rationale,
    this.status = 'new',
    this.expiresAt,
  });

  factory Signal.fromJson(Map<String, dynamic> json) => Signal(
        signalId: json['signal_id']?.toString() ?? '',
        asset: json['asset'] as String? ?? '',
        direction: json['direction'] as String? ?? 'NO_TRADE',
        entryLow: _toDouble(json['entry_low']) ?? 0,
        entryHigh: _toDouble(json['entry_high']) ?? 0,
        stopLoss: _toDouble(json['stop_loss']) ?? 0,
        takeProfits: (json['take_profits'] as List<dynamic>? ?? [])
            .map((e) => _toDouble(e) ?? 0)
            .toList(),
        confidence: (json['confidence'] as num?)?.toInt() ?? 0,
        marketRiskFactor: _toDouble(json['market_risk_factor']) ?? 1.0,
        riskReward: _toDouble(json['risk_reward']),
        rationale: json['rationale'] as String?,
        status: json['status'] as String? ?? 'new',
        expiresAt: _toDate(json['expires_at']),
      );
}

class Trade {
  final int id;
  final String mode;
  final String asset;
  final String direction;
  final double entryPrice;
  final double? exitPrice;
  final double quantity;
  final double? pnl;
  final double? pnlPct;
  final DateTime? openedAt;
  final DateTime? closedAt;
  final String? closeReason;

  Trade({
    required this.id,
    required this.mode,
    required this.asset,
    required this.direction,
    required this.entryPrice,
    this.exitPrice,
    required this.quantity,
    this.pnl,
    this.pnlPct,
    this.openedAt,
    this.closedAt,
    this.closeReason,
  });

  factory Trade.fromJson(Map<String, dynamic> json) => Trade(
        id: (json['id'] as num).toInt(),
        mode: json['mode'] as String? ?? 'paper',
        asset: json['asset'] as String? ?? '',
        direction: json['direction'] as String? ?? '',
        entryPrice: _toDouble(json['entry_price']) ?? 0,
        exitPrice: _toDouble(json['exit_price']),
        quantity: _toDouble(json['quantity']) ?? 0,
        pnl: _toDouble(json['pnl']),
        pnlPct: _toDouble(json['pnl_pct']),
        openedAt: _toDate(json['opened_at']),
        closedAt: _toDate(json['closed_at']),
        closeReason: json['close_reason'] as String?,
      );
}

class Portfolio {
  final String mode;
  final double equity;
  final double openRiskAmount;
  final double openRiskPct;
  final List<Trade> openPositions;
  final double realizedPnlTotal;
  final double realizedPnlDay;
  final double realizedPnlWeek;

  Portfolio({
    required this.mode,
    required this.equity,
    required this.openRiskAmount,
    required this.openRiskPct,
    required this.openPositions,
    required this.realizedPnlTotal,
    required this.realizedPnlDay,
    required this.realizedPnlWeek,
  });

  factory Portfolio.fromJson(Map<String, dynamic> json) => Portfolio(
        mode: json['mode'] as String? ?? 'paper',
        equity: _toDouble(json['equity']) ?? 0,
        openRiskAmount: _toDouble(json['open_risk_amount']) ?? 0,
        openRiskPct: _toDouble(json['open_risk_pct']) ?? 0,
        openPositions: (json['open_positions'] as List<dynamic>? ?? [])
            .map((e) => Trade.fromJson(e as Map<String, dynamic>))
            .toList(),
        realizedPnlTotal: _toDouble(json['realized_pnl_total']) ?? 0,
        realizedPnlDay: _toDouble(json['realized_pnl_day']) ?? 0,
        realizedPnlWeek: _toDouble(json['realized_pnl_week']) ?? 0,
      );
}

class Channel {
  final int id;
  final String title;
  final String? username;
  final bool isPrivate;
  final double credibility;
  final bool isActive;

  Channel({
    required this.id,
    required this.title,
    this.username,
    required this.isPrivate,
    required this.credibility,
    required this.isActive,
  });

  factory Channel.fromJson(Map<String, dynamic> json) => Channel(
        id: (json['id'] as num).toInt(),
        title: json['title'] as String? ?? '',
        username: json['username'] as String?,
        isPrivate: json['is_private'] as bool? ?? false,
        credibility: _toDouble(json['credibility']) ?? 0.5,
        isActive: json['is_active'] as bool? ?? true,
      );
}

class Health {
  final String status;
  final String tradingMode;
  final bool killSwitch;

  Health({
    required this.status,
    required this.tradingMode,
    required this.killSwitch,
  });

  factory Health.fromJson(Map<String, dynamic> json) => Health(
        status: json['status'] as String? ?? 'unknown',
        tradingMode: json['trading_mode'] as String? ?? 'paper',
        killSwitch: json['kill_switch'] as bool? ?? false,
      );
}
