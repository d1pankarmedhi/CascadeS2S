# Stage 1: The Builder Stage
FROM python:3.10-slim as builder

ARG DEVICE=cpu

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"
ENV UV_HTTP_TIMEOUT=300

COPY ./api/requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Stage 2: The Final Application Stage
FROM python:3.10-slim

WORKDIR /app

# Copy dependencies
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY ./api/main.py .
COPY ./utils ./utils
COPY ./api/static ./static

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
