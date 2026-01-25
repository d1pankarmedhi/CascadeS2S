FROM python:3.10-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"
ENV UV_HTTP_TIMEOUT=300

COPY ./api/requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY ./api/main.py .
COPY ./utils/logger.py .
COPY ./api/static ./static

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
