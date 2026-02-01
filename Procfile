web: gunicorn Config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: celery -A Config worker --loglevel=info --pool=solo --concurrency=2
beat: celery -A Config beat --loglevel=info