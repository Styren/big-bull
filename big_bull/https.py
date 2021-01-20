import logging
from enum import Enum

import opentracing
from aiohttp import web
from prometheus_client import REGISTRY
from prometheus_client.exposition import choose_encoder

logger = logging.getLogger("bigbull.https")


async def prometheus_metrics_handler(request):
    encoder, content_type = choose_encoder(request.headers.get("Accept"))
    print(content_type)
    registry = REGISTRY
    if "name[]" in request.path_qs:
        registry = registry.restricted_registry(request.path_qs["name[]"])
    output = encoder(registry)
    return web.Response(body=output, status=200, headers={"Content-Type": content_type})


class HTTPMethod(Enum):
    GET = web.get
    POST = web.post
    PUT = web.put
    DELETE = web.delete


_https_endpoint_registry = []


def get_https_span(request, tracer):
    span_context = tracer.extract(
        format=opentracing.Format.HTTP_HEADERS,
        carrier=request.headers,
    )
    span = tracer.start_span(
        operation_name=request.path,
        child_of=span_context,
    )
    span.set_tag("https.method", request.method)
    span.set_tag("https.url", request.url)

    return span


def get_https_wrapper(func):
    async def inner(request):
        tracer = opentracing.global_tracer()
        span = get_https_span(request, tracer)
        with tracer.scope_manager.activate(span, True):
            return await func(request)

    return inner


def get(endpoint, *args, **kwargs):
    def decorator(func):
        _https_endpoint_registry.append(
            (HTTPMethod.GET, endpoint, get_https_wrapper(func))
        )
        return get_https_wrapper(func)

    return decorator


def register_https_endpoints():
    app = web.Application()
    for (method, endpoint, handler) in _https_endpoint_registry:
        app.add_routes([method(endpoint, handler)])
    app.add_routes([web.get("/metrics", prometheus_metrics_handler)])
    return app
