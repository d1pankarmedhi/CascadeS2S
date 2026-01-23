FROM python:3.10-slim

WORKDIR /app

COPY ./api/requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

COPY ./api/main.py .
COPY ./utils/logger.py .
COPY ./api/static ./static

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
