FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.production
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0
COPY . .
RUN useradd --create-home app && mkdir -p /app/logs /app/data && chown -R app /app
USER app
# The embedding model is downloaded once at build time into the image (a volume at /app/data replaces it in production).
ENV COPILOT_MODEL_CACHE_DIR=/app/data/models COPILOT_RAW_DOCS_DIR=/app/data/raw_documents
RUN DJANGO_SETTINGS_MODULE=config.settings.development DB_ENGINE=django.db.backends.sqlite3 DB_NAME=/tmp/x.db DB_USER=x DB_PASSWORD=x     python manage.py copilot_prepare_model || echo "model download skipped; run copilot_prepare_model after deployment"
EXPOSE 8000
# Migrations run on every start (they are idempotent); the API is then served by gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
