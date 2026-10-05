import 'package:flutter/material.dart';

class DirectionBadge extends StatelessWidget {
  final String direction;

  const DirectionBadge({super.key, required this.direction});

  Color get _color {
    switch (direction) {
      case 'LONG':
        return Colors.green;
      case 'SHORT':
        return Colors.redAccent;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: _color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        direction,
        style: TextStyle(color: _color, fontWeight: FontWeight.bold, fontSize: 12),
      ),
    );
  }
}
