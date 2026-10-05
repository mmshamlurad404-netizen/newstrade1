import 'package:flutter/material.dart';

import '../models.dart';
import 'confidence_bar.dart';
import 'direction_badge.dart';

class SignalCard extends StatelessWidget {
  final Signal signal;

  const SignalCard({super.key, required this.signal});

  String _countdown() {
    final expiresAt = signal.expiresAt;
    if (expiresAt == null) return '-';
    final remaining = expiresAt.difference(DateTime.now());
    if (remaining.isNegative) return 'expired';
    if (remaining.inMinutes < 60) return '${remaining.inMinutes}m';
    return '${remaining.inHours}h ${remaining.inMinutes % 60}m';
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    signal.asset,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
                DirectionBadge(direction: signal.direction),
                const SizedBox(width: 8),
                Text(signal.status, style: const TextStyle(color: Colors.white54)),
              ],
            ),
            const SizedBox(height: 10),
            ConfidenceBar(value: signal.confidence),
            const SizedBox(height: 10),
            _row('Entry',
                '${signal.entryLow.toStringAsFixed(4)} - ${signal.entryHigh.toStringAsFixed(4)}'),
            _row('Stop', signal.stopLoss.toStringAsFixed(4)),
            _row('Targets',
                signal.takeProfits.map((tp) => tp.toStringAsFixed(4)).join(' / ')),
            _row('Reward/Risk', signal.riskReward?.toStringAsFixed(2) ?? '-'),
            _row('Risk factor', signal.marketRiskFactor.toStringAsFixed(2)),
            _row('Expires in', _countdown()),
            if (signal.rationale != null) ...[
              const SizedBox(height: 8),
              Text(signal.rationale!,
                  style: const TextStyle(color: Colors.white54, fontSize: 12)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(width: 96, child: Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12))),
          Expanded(child: Text(value, style: const TextStyle(fontSize: 13))),
        ],
      ),
    );
  }
}
