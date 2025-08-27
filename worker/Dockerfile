FROM python:3.10-slim
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# download model during build time
RUN python -c "import whisper; whisper.load_model('base')"

COPY . .

CMD ["python", "worker.py"]
