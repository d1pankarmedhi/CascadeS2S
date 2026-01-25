# Stage 1: The Builder Stage
FROM python:3.10 as builder

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"
ENV UV_HTTP_TIMEOUT=300

# Install Python dependencies using uv
COPY ./tts-worker/requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Download the Qwen3-TTS model during the build process
RUN python -c "from qwen_tts import Qwen3TTSModel; Qwen3TTSModel.from_pretrained('Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice')"

# Stage 2: The Final Application Stage
FROM python:3.10-slim

WORKDIR /app

# Copy only the necessary Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# Copy the pre-downloaded model cache
RUN mkdir -p /root/.cache/huggingface/hub/
COPY --from=builder /root/.cache/huggingface/hub/ /root/.cache/huggingface/hub/

# Copy the application code
COPY ./tts-worker/ .
COPY ./utils/logger.py .

# Command to run the worker script
CMD ["python", "worker.py"]
