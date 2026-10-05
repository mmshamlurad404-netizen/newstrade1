import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models.dart';
import '../state/app_state.dart';

class PortfolioScreen extends StatefulWidget {
  const PortfolioScreen({super.key});

  @override
  State<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends State<PortfolioScreen> {
  late Future<(Portfolio, List<Trade>)> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<(Portfolio, List<Trade>)> _load() async {
    final api = context.read<AppState>().api;
    final portfolio = await api.portfolio();
    final trades = await api.trades(status: 'closed');
    return (portfolio, trades);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<(Portfolio, List<Trade>)>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return Center(child: Text('Failed: ${snapshot.error}'));
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final (portfolio, trades) = snapshot.data!;
        return RefreshIndicator(
          onRefresh: () async => setState(() => _future = _load()),
          child: ListView(
            padding: const EdgeInsets.all(12),
            children: [
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _stat('Equity', portfolio.equity.toStringAsFixed(2)),
                  _stat('Open risk',
                      '${portfolio.openRiskAmount.toStringAsFixed(2)} (${portfolio.openRiskPct.toStringAsFixed(2)}%)'),
                  _stat('Realized today', portfolio.realizedPnlDay.toStringAsFixed(2)),
                  _stat('Realized week', portfolio.realizedPnlWeek.toStringAsFixed(2)),
                  _stat('Realized total', portfolio.realizedPnlTotal.toStringAsFixed(2)),
                ],
              ),
              const SizedBox(height: 16),
              Text('Open positions (${portfolio.openPositions.length})',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              if (portfolio.openPositions.isEmpty)
                const Text('No open positions.', style: TextStyle(color: Colors.white54))
              else
                ...portfolio.openPositions.map(_positionTile),
              const SizedBox(height: 16),
              const Text('Closed trades', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              if (trades.isEmpty)
                const Text('No closed trades yet.', style: TextStyle(color: Colors.white54))
              else
                ...trades.map(_tradeTile),
            ],
          ),
        );
      },
    );
  }

  Widget _stat(String label, String value) {
    return Container(
      width: 160,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Colors.white54, fontSize: 11)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _positionTile(Trade trade) {
    return ListTile(
      dense: true,
      title: Text('${trade.asset}  ${trade.direction}'),
      subtitle: Text('Entry ${trade.entryPrice.toStringAsFixed(4)}  Qty ${trade.quantity.toStringAsFixed(4)}'),
    );
  }

  Widget _tradeTile(Trade trade) {
    final positive = (trade.pnl ?? 0) >= 0;
    return ListTile(
      dense: true,
      title: Text('${trade.asset}  ${trade.direction}  [${trade.mode}]'),
      subtitle: Text('${trade.closeReason ?? '-'}  exit ${trade.exitPrice?.toStringAsFixed(4) ?? '-'}'),
      trailing: Text(
        '${trade.pnl?.toStringAsFixed(2) ?? '-'} (${trade.pnlPct?.toStringAsFixed(2) ?? '-'}%)',
        style: TextStyle(color: positive ? Colors.green : Colors.redAccent),
      ),
    );
  }
}
