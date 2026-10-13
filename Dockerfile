FROM python:3.12-slim

ARG REQUIREMENTS=prod

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=myshop.settings.prod \
    MEDIA_ROOT=/data/media

WORKDIR /app

COPY requirements/ requirements/
RUN pip install -r requirements/${REQUIREMENTS}.txt

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data/media /app/staticfiles \
    && chown -R app:app /data /app

COPY --chown=app:app . .
RUN chmod +x docker/entrypoint.sh \
    && SECRET_KEY=build-only DB_NAME=x DB_USER=x DB_PASSWORD=x \
       python manage.py collectstatic --noinput -v0

USER app
EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "myshop.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
