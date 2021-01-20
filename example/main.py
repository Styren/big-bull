from aiohttp import web

from bigbull.https import get
from bigbull.kafka import kafka_consumer


@get("/healthz")
async def healthz(request):
    return web.Response(text="OK")


@kafka_consumer("topic")
async def lol(message):
    return web.Response(text="OK")
