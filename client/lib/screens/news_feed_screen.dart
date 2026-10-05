import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models.dart';
import '../services/ws_service.dart';
import '../state/app_state.dart';
import '../widgets/news_tile.dart';

class NewsFeedScreen extends StatefulWidget {
  const NewsFeedScreen({super.key});

  @override
  State<NewsFeedScreen> createState() => _NewsFeedScreenState();
}

class _NewsFeedScreenState extends State<NewsFeedScreen> {
  final List<News> _live = [];
  WsService? _ws;
  List<News>? _news;
  String? _error;
  String _coin = '';
  String? _eventType;
  String? _urgency;

  static const _events = [
    'listing',
    'delisting',
    'hack',
    'partnership',
    'unlock',
    'regulation',
    'adoption',
    'macro',
  ];

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
      ..connect('/ws/news');
    _ws!.stream.listen((event) {
      if (event['type'] == 'news' && mounted) {
        setState(() {
          _live.insert(0, News.fromJson(event['data'] as Map<String, dynamic>));
        });
      }
    });
  }

  Future<void> _load() async {
    try {
      final data = await context
          .read<AppState>()
          .api
          .news(coin: _coin, eventType: _eventType, urgency: _urgency);
      if (!mounted) return;
      setState(() {
        _news = data;
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
    final known = (_news ?? []).map((item) => item.id).toSet();
    final merged = [
      ..._live.where((item) => !known.contains(item.id)),
      ...?_news,
    ];

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              TextField(
                decoration: const InputDecoration(
                  labelText: 'Coin (e.g. SOL)',
                  isDense: true,
                ),
                textCapitalization: TextCapitalization.characters,
                onChanged: (value) => setState(() => _coin = value.toUpperCase()),
                onSubmitted: (_) => _load(),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _eventType,
                      decoration: const InputDecoration(labelText: 'Event', isDense: true),
                      items: [
                        const DropdownMenuItem(value: null, child: Text('All events')),
                        ..._events.map(
                          (value) => DropdownMenuItem(value: value, child: Text(value)),
                        ),
                      ],
                      onChanged: (value) {
                        setState(() => _eventType = value);
                        _load();
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _urgency,
                      decoration: const InputDecoration(labelText: 'Urgency', isDense: true),
                      items: const [
                        DropdownMenuItem(value: null, child: Text('Any')),
                        DropdownMenuItem(value: 'high', child: Text('high')),
                        DropdownMenuItem(value: 'medium', child: Text('medium')),
                        DropdownMenuItem(value: 'low', child: Text('low')),
                      ],
                      onChanged: (value) {
                        setState(() => _urgency = value);
                        _load();
                      },
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text('Failed to load news: $_error',
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
                        child: Center(child: Text('No news yet.')),
                      ),
                    ],
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: merged.length,
                    itemBuilder: (context, index) => NewsTile(news: merged[index]),
                  ),
          ),
        ),
      ],
    );
  }
}
