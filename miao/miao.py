from enum import Enum
from concurrent.futures import CancelledError
import sys
import importlib
import asyncio
from pathlib import Path

from aiohttp import web
import logging
import argparse

from .kafka import register_kafka_consumers
from .https import register_https_endpoints
from .jaeger import initialize_jaeger

logger = logging.getLogger('miao.main')

def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.critical(f"Caught exception: {msg}")
    for task in asyncio.Task.all_tasks():
        task.cancel()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--service-name", required=True)
    args = parser.parse_args()
    initialize_jaeger(service_name=args.service_name)

    logger.info("Parsing modules...")
    for path in Path(args.path).rglob('*.py'):
        logger.info("Importing %s", path)
        mod = importlib.import_module(".".join(path.parts)[:-3])

    logger.info("Registering kafka consumers...")
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    register_kafka_consumers(loop)

    logger.info("Registering https endpoints...")
    app = register_https_endpoints()
    try:
        web.run_app(app)
    except CancelledError:
        pass
