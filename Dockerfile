FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system classpulse && adduser --system --ingroup classpulse classpulse

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN SECRET_KEY=build-only-secret \
    ALLOWED_HOSTS=localhost \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    python manage.py collectstatic --noinput \
    && chmod 755 /app/docker/entrypoint.sh \
    && chown -R classpulse:classpulse /app

USER classpulse

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
