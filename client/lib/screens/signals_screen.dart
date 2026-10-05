import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models.dart';
import '../services/ws_service.dart';
import '../state/app_state.dart';
import '../widgets/signal_card.dart';

class SignalsScreen extends StatefulWidget {
  const SignalsScreen({super.key});

  @override
  State<SignalsScreen> createState() => _SignalsScreenState();
}

class _SignalsScreenState extends State<SignalsScreen> {
  final List<Signal> _live = [];
  WsService? _ws;
  List<Signal>? _signals;
  String? _error;
  double _confidenceMin = 0;
  String? _direction;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _load();
      _connect();
    });
  }

  void _connect() {
    final state = context.read<AppState>();
    _ws = WsService(baseUrl: state.baseUrl, token: state.token)
      ..connect('/ws/signals');
    _ws!.stream.listen((event) {
      if (event['type'] == 'signal' && mounted) {
        setState(() {
          _live.insert(0, Signal.fromJson(event['data'] as Map<String, dynamic>));
        });
      }
    });
  }

  Future<void> _load() async {
    try {
      final data = await context
          .read<AppState>()
          .api
          .signals(confidenceMin: _confidenceMin.round(), direction: _direction);
      if (!mounted) return;
      setState(() {
        _signals = data;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    }
  }

  @override
  void dispose() {
    _ws?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final known = (_signals ?? []).map((item) => item.signalId).toSet();
    final merged = [
      ..._live.where((item) => !known.contains(item.signalId)),
      ...?_signals,
    ];

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              Row(
                children: [
                  Text('Min confidence: ${_confidenceMin.round()}'),
                  Expanded(
                    child: Slider(
                      value: _confidenceMin,
                      min: 0,
                      max: 100,
                      divisions: 20,
                      label: _confidenceMin.round().toString(),
                      onChanged: (value) => setState(() => _confidenceMin = value),
                      onChangeEnd: (_) => _load(),
                    ),
                  ),
                ],
              ),
              DropdownButtonFormField<String>(
                value: _direction,
                decoration: const InputDecoration(labelText: 'Direction', isDense: true),
                items: const [
                  DropdownMenuItem(value: null, child: Text('Any direction')),
                  DropdownMenuItem(value: 'LONG', child: Text('LONG')),
                  DropdownMenuItem(value: 'SHORT', child: Text('SHORT')),
                ],
                onChanged: (value) {
                  setState(() => _direction = value);
                  _load();
                },
              ),
            ],
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text('Failed to load signals: $_error',
                style: const TextStyle(color: Colors.redAccent)),
          ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _load,
            child: merged.isEmpty
                ? ListView(
                    children: const [
                      Padding(
                        padding: EdgeInsets.all(40),
                        child: Center(child: Text('No signals yet.')),
                      ),
                    ],
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: merged.length,
                    itemBuilder: (context, index) =>
                        SignalCard(signal: merged[index]),
                  ),
          ),
        ),
      ],
    );
  }
}
