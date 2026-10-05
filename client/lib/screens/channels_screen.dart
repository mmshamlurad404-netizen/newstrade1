import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models.dart';
import '../state/app_state.dart';

class ChannelsScreen extends StatefulWidget {
  const ChannelsScreen({super.key});

  @override
  State<ChannelsScreen> createState() => _ChannelsScreenState();
}

class _ChannelsScreenState extends State<ChannelsScreen> {
  late Future<List<Channel>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.channels();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Channel>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return Center(child: Text('Failed: ${snapshot.error}'));
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final channels = snapshot.data!;
        if (channels.isEmpty) {
          return const Center(child: Text('No channels tracked yet.'));
        }
        return ListView.builder(
          itemCount: channels.length,
          itemBuilder: (context, index) {
            final channel = channels[index];
            return ListTile(
              title: Text(channel.title),
              subtitle: Text(
                '${channel.username ?? '-'}  |  ${channel.isPrivate ? 'private' : 'public'}',
              ),
              trailing: Text(
                channel.credibility.toStringAsFixed(3),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            );
          },
        );
      },
    );
  }
}
