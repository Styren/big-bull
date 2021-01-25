import logging
from enum import Enum

import opentracing
from aiohttp import web
from prometheus_client import REGISTRY
from prometheus_client.exposition import choose_encoder
from big_bull import graph

logger = logging.getLogger("bigbull.route")


async def prometheus_metrics_handler(request):
    encoder, content_type = choose_encoder(request.headers.get("Accept"))
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


_route_endpoint_registry = []


def get_route_span(request, tracer):
    span_context = tracer.extract(
        format=opentracing.Format.HTTP_HEADERS,
        carrier=request.headers,
    )
    span = tracer.start_span(
        operation_name=f"{request.method}:{request.path}",
        child_of=span_context,
    )
    span.set_tag("span.kind", "server")
    span.set_tag("http.method", request.method)
    span.set_tag("http.url", request.url)
    span.set_tag("http.ip", request.remote)

    return span


def get_route_wrapper(func):
    def injection_wrapper(**kwargs):
        async def inner(request):
            tracer = opentracing.global_tracer()
            span = get_route_span(request, tracer)
            with tracer.scope_manager.activate(span, True):
                ret = await graph.inject_func(func, kwargs, request=request)
                if isinstance(ret, web.Response):
                    span.set_tag("http.status_code", ret.status)
                return ret

        return inner

    return injection_wrapper


def route_decorator(method, endpoint):
    def inner(func):
        _route_endpoint_registry.append(
            (method, endpoint, func, get_route_wrapper(func))
        )
        return get_route_wrapper(func)

    return inner


def get(endpoint, *args, **kwargs):
    return route_decorator(method=HTTPMethod.GET, endpoint=endpoint)


def post(endpoint, *args, **kwargs):
    return route_decorator(method=HTTPMethod.POST, endpoint=endpoint)


def put(endpoint, *args, **kwargs):
    return route_decorator(method=HTTPMethod.PUT, endpoint=endpoint)


def delete(endpoint, *args, **kwargs):
    return route_decorator(method=HTTPMethod.DELETE, endpoint=endpoint)


def register_route_endpoints(injectables):
    app = web.Application()
    for (method, endpoint, func, handler) in _route_endpoint_registry:
        args = graph.get_arguments_to_inject(func, injectables, ignore_args=["request"])
        app.add_routes([method(endpoint, handler(**args))])
    app.add_routes([web.get("/metrics", prometheus_metrics_handler)])
    return app
