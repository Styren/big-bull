import logging
from aiokafka import AIOKafkaConsumer

logger = logging.getLogger('miao.kafka')

_kafka_consumer_registry = []

def get_kafka_consumer_span(message, tracer):
    span_context = tracer.extract(
        format=Format.TEXT_HEADERS,
        carrier=message.headers,
    )
    span = tracer.start_span(
        operation_name=f"from_{message.topic}",
        follows_from=span_context
    )
    span.set_tag('kafka.topic', message.topic)

    return span

def get_kafka_wrapper(func):
    async def inner(message):
        span = get_kafka_consumer_span(message, opentracing.global_tracer())
        with tracer.scope_manager.activate(span, True) as scope:
            response = await func(message)

def kafka_consumer(*args, **kwargs):
    def decorator(func):
        _kafka_consumer_registry.append((get_kafka_wrapper(func), args, kwargs))
        return get_kafka_wrapper(func)
    return decorator

async def kafka_consumer_task(func, *args, **kwargs):
    consumer = AIOKafkaConsumer(*args, **kwargs)
    try:
        await consumer.start()
        async for message in consumer:
            await kafka_wrapper(func, message)
    finally:
        await consumer.stop()

def register_kafka_consumers(loop):
    for (func, args, kwargs) in _kafka_consumer_registry:
        loop.create_task(kafka_consumer_task(func, *args, **kwargs))
