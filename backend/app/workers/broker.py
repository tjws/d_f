"""Dramatiq 与 Redis 的连接配置。Redis 只负责投递，结果仍写 PostgreSQL。"""

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.workers.heartbeat import WorkerHeartbeatMiddleware


redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
broker = RedisBroker(url=redis_url, namespace="k12_sales_assistant")
broker.add_middleware(WorkerHeartbeatMiddleware())
dramatiq.set_broker(broker)
