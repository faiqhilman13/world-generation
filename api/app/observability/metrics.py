from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

world_generate_requests_total = Counter(
    "world_generate_requests_total",
    "Total world generation requests submitted by users.",
)

world_generate_failures_total = Counter(
    "world_generate_failures_total",
    "Total world generation requests that failed before provider completion.",
)

operation_poll_cycles_histogram = Histogram(
    "operation_poll_cycles_histogram",
    "Distribution of provider operation polling loop cycles.",
    buckets=(1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144),
)

time_to_world_ready_seconds = Histogram(
    "time_to_world_ready_seconds",
    "Time from generation submit to world success.",
    buckets=(5, 10, 20, 30, 45, 60, 90, 120, 180, 240, 360, 600, 900, 1200),
)

viewer_open_events_total = Counter(
    "viewer_open_events_total",
    "Viewer open events.",
    labelnames=("result",),
)

viewer_open_success_rate = Gauge(
    "viewer_open_success_rate",
    "Rolling success ratio for viewer open events in current process.",
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("method", "path", "status_code"),
)

_viewer_total = 0
_viewer_success = 0


def record_viewer_open(success: bool) -> None:
    global _viewer_total
    global _viewer_success
    _viewer_total += 1
    if success:
        _viewer_success += 1
        viewer_open_events_total.labels(result="success").inc()
    else:
        viewer_open_events_total.labels(result="failure").inc()
    if _viewer_total > 0:
        viewer_open_success_rate.set(_viewer_success / _viewer_total)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
