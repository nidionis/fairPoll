#!/bin/bash
NB_LINES=${1:-100}

docker compose exec web python manage.py shell -c "
from polls.models import PollLog
recent_logs = PollLog.objects.all().order_by('-timestamp')[:$NB_LINES]
if not recent_logs:
    print('No logs found.')
else:
    print(f'--- Last {len(recent_logs)} Logs ---')
    for log in recent_logs:
        user_info = log.user.username if log.user else 'Anonymous'
        ip_info = log.ip_address or 'Unknown IP'
        content_type_name = log.content_type.model if log.content_type else 'Unknown Type'
        
        print(
            f\"[{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] \"
            f\"Action: {log.get_action_type_display()} | \"
            f\"User: {user_info} | \"
            f\"IP: {ip_info} | \"
            f\"Target Object: {log.poll} (Type: {content_type_name}, ID: {log.object_id})\"
        )
"
