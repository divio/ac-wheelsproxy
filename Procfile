web: uwsgi --module=wsgi --http=0.0.0.0:80 --workers=4 --max-requests=500
worker: celery -A celery_app.app worker -B -l info --concurrency=${CELERY_CONCURRENCY:-6}
