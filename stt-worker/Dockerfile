FROM python:3.12-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"
ENV UV_HTTP_TIMEOUT=300

COPY ./stt-worker/requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# faster-whisper will download models - we pre-download here for performance
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"

COPY ./stt-worker/ .
COPY ./utils/logger.py .

CMD ["python", "worker.py"]
