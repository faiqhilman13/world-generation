# Interior World Runbook

## Primary failure buckets

- `UPLOAD_PREPARE_FAILED`
- `UPLOAD_PROXY_FAILED`
- `UPLOAD_CONFIRM_FAILED`
- `GENERATION_SUBMIT_FAILED`
- `GENERATION_PROVIDER_402`
- `GENERATION_PROVIDER_4XX`
- `GENERATION_PROVIDER_5XX`
- `OPERATION_TIMEOUT`
- `WORLD_FETCH_FAILED`
- `VIEWER_UNSUPPORTED_PAYLOAD`

## Metrics to watch

- `world_generate_requests_total`
- `world_generate_failures_total`
- `operation_poll_cycles_histogram`
- `time_to_world_ready_seconds`
- `viewer_open_success_rate`

## Operational checks

1. API health: `GET /health`
2. Metrics health: `GET /metrics`
3. Queue health: run `celery -A worker_app.celery_app:celery_app inspect ping`
4. DB reachability: run `alembic current`

## Incident response quick steps

1. Verify `WORLDLABS_API_KEY` is present and valid.
2. Check `world_generate_failures_total` spikes.
3. Inspect API logs for `request_failed` and worker logs for `world_job_failed`.
4. If failures are provider-side (`4xx/5xx`), throttle new generation traffic.
5. If polling timeout spikes, increase `WORLDLABS_POLL_HORIZON_SECONDS` temporarily.

## Upload CORS incident note

1. Browser direct upload to provider signed URLs can fail due provider bucket CORS.
2. App fallback path is `POST /v1/uploads/proxy` (API uploads server-side).
3. Verify fallback route exists in OpenAPI and API container is healthy before triage.

## Release checklist

1. `python -m ruff check .` in `api` and `worker`
2. `python -m pytest -q` in `api`
3. `npm run lint` in `web`
4. `docker compose up --build` smoke run
5. Confirm upload -> generate -> viewer path with a live key in staging
