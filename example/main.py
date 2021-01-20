from miao.https import get
from miao.kafka import kafka_consumer
from aiohttp import web

@get("/healthz")
async def healthz(request):
    return web.Response(text="OK")

@kafka_consumer("topic")
async def lol(message):
    return web.Response(text="OK")
