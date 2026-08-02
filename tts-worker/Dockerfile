# Stage 1: The Builder Stage
FROM python:3.10-slim as builder

ARG DEVICE=cpu

WORKDIR /build

# Install system dependencies needed for building/installing certain packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"
ENV UV_HTTP_TIMEOUT=300

# Install Python dependencies using uv
COPY ./tts-worker/requirements.txt .

# Conditional torch installation based on DEVICE
RUN if [ "$DEVICE" = "gpu" ]; then \
        uv pip install --system --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu124; \
    else \
        uv pip install --system --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi && \
    uv pip install --system --no-cache-dir -r requirements.txt

# Download the Pocket TTS model during the build process
RUN python -c "from pocket_tts import TTSModel; TTSModel.load_model()"

# Stage 2: The Final Application Stage
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy only the necessary Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the pre-downloaded model cache
RUN mkdir -p /root/.cache/huggingface/hub/
COPY --from=builder /root/.cache/huggingface/hub/ /root/.cache/huggingface/hub/

# Copy the application code
COPY ./tts-worker/worker.py .
COPY ./utils ./utils

# Command to run the worker script
CMD ["python", "worker.py"]
