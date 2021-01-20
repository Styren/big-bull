from jaeger_client import Config
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
from opentracing.scope_managers.contextvars import ContextVarsScopeManager
from opentracing_instrumentation.client_hooks import install_all_patches


def initialize_jaeger(service_name):
    install_all_patches()
    config = Config(
        config={
            "sampler": {
                "type": "const",
                "param": 1,
            },
            "logging": True,
        },
        service_name=service_name,
        validate=True,
        scope_manager=ContextVarsScopeManager(),
        metrics_factory=PrometheusMetricsFactory(namespace=service_name),
    )
    return config.initialize_tracer()
