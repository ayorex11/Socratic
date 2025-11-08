import os
from celery import Celery

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

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')