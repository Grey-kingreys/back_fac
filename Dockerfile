# Dockerfile — gestion_backend (Django REST Framework)
# Multi-stage : builder -> runner

# ── Stage 1 : Builder ─────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2 : Runner (image finale légère) ────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p /app/media /app/staticfiles /app/logs

RUN addgroup --system django \
    && adduser --system --ingroup django django \
    && chown -R django:django /app

USER django

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Pointe sur config.settings (et non backend.settings)
    DJANGO_SETTINGS_MODULE=config.settings

EXPOSE 8000

COPY --chown=django:django docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
# Pointe sur config.wsgi (et non backend.wsgi)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]