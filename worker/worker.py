from __future__ import annotations

import logging

from redis import Redis
from rq import Connection, Worker

from app.config import get_settings
from app.logging import setup_logging


def main() -> None:
    setup_logging()
    settings = get_settings()
    logger = logging.getLogger(__name__)

    redis_conn = Redis.from_url(settings.redis_url)
    queue_name = settings.rq_queue_name

    logger.info("Starting RQ worker. queue=%s", queue_name)
    with Connection(redis_conn):
        worker = Worker([queue_name])
        worker.work()


if __name__ == "__main__":
    main()
