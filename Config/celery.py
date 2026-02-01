import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings')

app = Celery('Config')

# Use Redis URL from environment if available (for Render)
if os.getenv('REDIS_URL'):
    app.conf.broker_url = os.getenv('REDIS_URL')
    app.conf.result_backend = os.getenv('REDIS_URL')
else:
    # Fallback for local development
    app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# Celery Beat Schedule for Periodic Tasks
app.conf.beat_schedule = {
    # Check and expire subscriptions daily at midnight UTC
    'check-expired-subscriptions': {
        'task': 'Account.tasks.check_expired_subscriptions',
        'schedule': crontab(hour=0, minute=0),  # Daily at 00:00 UTC
    },
    # Send expiration warnings daily at 9 AM UTC
    'send-expiration-warnings': {
        'task': 'Account.tasks.send_expiration_warnings',
        'schedule': crontab(hour=9, minute=0),  # Daily at 09:00 UTC
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')