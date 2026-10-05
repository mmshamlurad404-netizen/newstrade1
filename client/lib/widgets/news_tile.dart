import 'package:flutter/material.dart';

import '../models.dart';

class NewsTile extends StatelessWidget {
  final News news;

  const NewsTile({super.key, required this.news});

  Color _sentimentColor() {
    switch (news.sentiment) {
      case 'bullish':
        return Colors.green;
      case 'bearish':
        return Colors.redAccent;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(news.coins.isEmpty ? 'unmapped' : news.coins.join(', '),
                    style: const TextStyle(color: Colors.lightBlueAccent, fontWeight: FontWeight.bold)),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: _sentimentColor().withOpacity(0.15),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(news.sentiment ?? 'unknown',
                      style: TextStyle(color: _sentimentColor(), fontSize: 11)),
                ),
                const Spacer(),
                Text('${news.sourceCount} src', style: const TextStyle(color: Colors.white54, fontSize: 11)),
              ],
            ),
            const SizedBox(height: 6),
            Text(news.headline, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Text(
              '${news.eventType ?? 'other'}  |  ${news.originChannel ?? 'unknown channel'}',
              style: const TextStyle(color: Colors.white54, fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }
}
