# Stage 1: The Builder Stage
FROM python:3.10-slim as builder

ARG DEVICE=cpu

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"
ENV UV_HTTP_TIMEOUT=300

COPY ./llm-worker/requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Stage 2: The Final Application Stage
FROM python:3.10-slim

WORKDIR /app

# Copy dependencies
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY ./llm-worker/ .
COPY ./utils ./utils

CMD ["python", "worker.py"]
