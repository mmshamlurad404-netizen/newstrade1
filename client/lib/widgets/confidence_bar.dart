import 'package:flutter/material.dart';

class ConfidenceBar extends StatelessWidget {
  final int value;

  const ConfidenceBar({super.key, required this.value});

  Color get _color {
    if (value >= 85) return Colors.green;
    if (value >= 75) return Colors.amber;
    return Colors.redAccent;
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: (value.clamp(0, 100)) / 100,
              minHeight: 8,
              backgroundColor: Colors.white12,
              valueColor: AlwaysStoppedAnimation<Color>(_color),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text('$value', style: const TextStyle(fontWeight: FontWeight.bold)),
      ],
    );
  }
}
