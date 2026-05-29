"""Gunicorn configuration for production.

Runs Uvicorn workers (ASGI) behind Gunicorn's process manager so the service
uses multiple CPU cores and recycles workers to bound memory — the basis of
handling high traffic horizontally *within* a container, complemented by
running multiple container replicas behind a load balancer.
"""
import multiprocessing
import os

# Bind
bind = f"0.0.0.0:{os.getenv('API_PORT', '8000')}"

# Workers: a common heuristic for CPU-bound apps is (2*cores)+1. This service is
# I/O-bound (LLM + web calls), so async Uvicorn workers handle many concurrent
# requests per worker; keep worker count ~= cores and scale replicas out.
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count()))
worker_class = "uvicorn.workers.UvicornWorker"

# Resilience
timeout = 120          # allow for slow LLM/search calls
graceful_timeout = 30
keepalive = 5
max_requests = 1000    # recycle workers to mitigate memory leaks
max_requests_jitter = 100

# Logging to stdout/stderr (collected by the container runtime)
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
