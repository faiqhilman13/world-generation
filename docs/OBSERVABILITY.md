# Observability Reference

## Logs

API and worker emit JSON logs with stable fields:

- `request_id`
- `session_id`
- `job_id`
- `provider_operation_id`
- `world_id`
- `duration_ms` or `duration_seconds`

## Metrics endpoint

- `GET /metrics`

Key metrics:

- `world_generate_requests_total`
- `world_generate_failures_total`
- `operation_poll_cycles_histogram`
- `time_to_world_ready_seconds`
- `viewer_open_success_rate`
- `http_request_duration_seconds`

## Suggested alert thresholds

1. `world_generate_failures_total / world_generate_requests_total > 0.15` over 15m
2. `histogram_quantile(0.95, time_to_world_ready_seconds) > 900`
3. `viewer_open_success_rate < 0.9` over 30m
