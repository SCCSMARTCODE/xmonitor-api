$env:PYTHONPATH = "$PWD"
.\.venv\Scripts\celery -A app.core.celery_app worker --loglevel=info --pool=solo
