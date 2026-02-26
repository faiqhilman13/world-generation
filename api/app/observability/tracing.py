from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def configure_tracing(service_name: str) -> None:
    current_provider = trace.get_tracer_provider()
    if getattr(current_provider, "_interior_world_configured", False):
        return

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    setattr(provider, "_interior_world_configured", True)
    trace.set_tracer_provider(provider)


def get_tracer():
    return trace.get_tracer("interior_world")
