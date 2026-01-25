FROM python:3.10-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"
ENV UV_HTTP_TIMEOUT=300

COPY ./llm-worker/requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY ./llm-worker/ .
COPY ./utils/logger.py .

CMD ["python", "worker.py"]
