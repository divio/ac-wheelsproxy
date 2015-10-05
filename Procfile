web: python manage.py runserver 0.0.0.0:80
worker: celery -A celery_app.app worker -B -l info --concurrency=${CELERY_CONCURRENCY:-6}
