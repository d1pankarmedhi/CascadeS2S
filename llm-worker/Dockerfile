FROM python:3.10-slim

WORKDIR /app

COPY ./llm-worker/requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

COPY ./llm-worker/ .
COPY ./utils/logger.py .

CMD ["python", "worker.py"]
