FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ART_OPTIMIZER_DATA_DIR=/data

WORKDIR /app

COPY pyproject.toml README.md ./
COPY art_optimizer ./art_optimizer
RUN pip install --no-cache-dir .

VOLUME ["/data"]
EXPOSE 8000

CMD ["python", "-m", "art_optimizer.app", "--host", "0.0.0.0", "--port", "8000"]
