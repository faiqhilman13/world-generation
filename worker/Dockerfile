FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/worker:/app/api

WORKDIR /app

COPY worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY worker /app/worker
COPY api /app/api

CMD ["celery", "-A", "worker_app.celery_app:celery_app", "worker", "--loglevel=info", "--concurrency=2"]
