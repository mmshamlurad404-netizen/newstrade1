import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models.dart';
import '../state/app_state.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  bool _unreadOnly = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppState>().refreshNotifications();
    });
  }

  Color _accent(BuildContext context, AppNotification note) {
    if (note.isRecovery) return Colors.greenAccent;
    if (note.isAlert) return Colors.orangeAccent;
    return Theme.of(context).colorScheme.primary;
  }

  IconData _icon(AppNotification note) {
    if (note.isRecovery) return Icons.check_circle_outline;
    if (note.isAlert) return Icons.warning_amber_outlined;
    return Icons.notifications_none;
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final notes = _unreadOnly
        ? state.notifications.where((note) => !note.isRead).toList()
        : state.notifications;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: Row(
            children: [
              FilterChip(
                label: const Text('Unread only'),
                selected: _unreadOnly,
                onSelected: (value) => setState(() => _unreadOnly = value),
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: state.unreadCount == 0
                    ? null
                    : () => state.markAllNotificationsRead(),
                icon: const Icon(Icons.done_all, size: 18),
                label: const Text('Mark all read'),
              ),
            ],
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: state.refreshNotifications,
            child: notes.isEmpty
                ? ListView(
                    children: const [
                      Padding(
                        padding: EdgeInsets.all(40),
                        child: Center(child: Text('No notifications.')),
                      ),
                    ],
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: notes.length,
                    itemBuilder: (context, index) {
                      final note = notes[index];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 10),
                        child: ListTile(
                          leading: Icon(
                            _icon(note),
                            color: _accent(context, note),
                          ),
                          title: Text(
                            note.title,
                            style: TextStyle(
                              fontWeight: note.isRead
                                  ? FontWeight.normal
                                  : FontWeight.bold,
                            ),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(note.eventType,
                                  style: const TextStyle(fontSize: 12)),
                              if (note.body != null && note.body!.isNotEmpty)
                                Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(note.body!),
                                ),
                              if (note.createdAt != null)
                                Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(
                                    note.createdAt!.toLocal().toString(),
                                    style: const TextStyle(
                                        fontSize: 11, color: Colors.white54),
                                  ),
                                ),
                            ],
                          ),
                          isThreeLine: true,
                          trailing: note.isRead
                              ? null
                              : IconButton(
                                  icon: const Icon(Icons.mark_email_read),
                                  tooltip: 'Mark read',
                                  onPressed: () =>
                                      state.markNotificationRead(note.id),
                                ),
                          onTap: note.isRead
                              ? null
                              : () => state.markNotificationRead(note.id),
                        ),
                      );
                    },
                  ),
          ),
        ),
      ],
    );
  }
}
