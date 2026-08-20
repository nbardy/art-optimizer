FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ART_OPTIMIZER_DATA_DIR=/data

WORKDIR /app

RUN groupadd --system artoptimizer \
    && useradd --system --gid artoptimizer --home-dir /app artoptimizer

COPY pyproject.toml README.md LICENSE ./
COPY art_optimizer ./art_optimizer
RUN python -m pip install --no-cache-dir . \
    && mkdir -p /data \
    && chown -R artoptimizer:artoptimizer /data /app

USER artoptimizer

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import json, urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3))['ok']" || exit 1

CMD ["python", "-m", "uvicorn", "art_optimizer.app:app", "--host", "0.0.0.0", "--port", "8000"]
