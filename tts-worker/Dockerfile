# Stage 1: The Builder Stage
FROM python:3.10 as builder

WORKDIR /build

# Install Python dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the ParlerTTS model and tokenizer during the build process
RUN python -c "from parler_tts import ParlerTTSForConditionalGeneration; from transformers import AutoTokenizer; ParlerTTSForConditionalGeneration.from_pretrained('parler-tts/parler-tts-tiny-v1'); AutoTokenizer.from_pretrained('parler-tts/parler-tts-tiny-v1')"

# Stage 2: The Final Application Stage
FROM python:3.10-slim

WORKDIR /app

# Copy only the necessary Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# Copy the pre-downloaded model cache
RUN mkdir -p /root/.cache/huggingface/hub/
COPY --from=builder /root/.cache/huggingface/hub/ /root/.cache/huggingface/hub/

# Copy the application code
COPY . .

# Command to run the worker script
CMD ["python", "worker.py"]
