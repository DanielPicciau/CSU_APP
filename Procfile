web: gunicorn core.wsgi --log-file -
worker: celery -A core worker -l INFO
beat: celery -A core beat -l INFO
