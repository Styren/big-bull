import logging

import opentracing
from aiokafka import AIOKafkaConsumer
from big_bull.graph import get_arguments_to_inject

logger = logging.getLogger("bigbull.kafka")

_kafka_consumer_registry = []


def get_kafka_consumer_span(message, consumer, tracer):
    span_context = tracer.extract(
        format=opentracing.Format.TEXT_HEADERS,
        carrier=message.headers,
    )
    span = tracer.start_span(
        operation_name=f"from_{message.topic}", follows_from=span_context
    )
    span.set_tag("span.kind", "consumer")
    span.set_tag("message_bus.destination", message.topic)
    span.set_tag("message_bus.topic", message.topic)
    span.set_tag("message_bus.timestamp", message.timestamp)
    span.set_tag("message_bus.timestamp_type", message.timestamp_type)
    span.set_tag("message_bus.group_id", consumer.group_id)
    span.set_tag("message_bus.client_id", consumer.client_id)
    span.set_tag("message_bus.api_version", consumer.api_version)

    return span


def get_kafka_wrapper(func):
    async def inner(message, consumer, *args, **kwargs):
        tracer = opentracing.global_tracer()
        span = get_kafka_consumer_span(message, consumer, tracer)
        with tracer.scope_manager.activate(span, True):
            return await func(*args, message, **kwargs)


def consumer(*args, **kwargs):
    def decorator(func):
        _kafka_consumer_registry.append((get_kafka_wrapper(func), args, kwargs))
        return get_kafka_wrapper(func)

    return decorator


async def kafka_consumer_task(func, graph, *args, **kwargs):
    consumer = AIOKafkaConsumer(*args, **kwargs)
    try:
        await consumer.start()
        async for message in consumer:
            args = get_arguments_to_inject(func, graph, ["message"])
            await func(message=message, consumer=consumer, **args)
    finally:
        await consumer.stop()


def register_kafka_consumers(graph, loop):
    for (func, args, kwargs) in _kafka_consumer_registry:
        loop.create_task(kafka_consumer_task(func, graph, *args, **kwargs))
