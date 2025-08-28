# Cascade Speech-to-Speech

A distributed speech-to-speech pipeline that converts speech input to text, processes it through an LLM, and converts the response back to speech. Built with microservices architecture using FastAPI, Redis, and Docker.

## 🌟 Features

- Speech-to-Text conversion using ML models
- LLM processing of transcribed text
- Text-to-Speech synthesis
- Asynchronous job processing
- Microservices architecture
- Docker containerization
- Redis-based job queue system
- Robust error handling and logging

## 🏗️ Architecture

The project is structured into several microservices:

```
├── api/               # API service for handling HTTP requests
├── stt-worker/        # Speech-to-Text worker service
├── llm-worker/        # Language Model worker service
├── tts-worker/        # Text-to-Speech worker service
└── docker-compose.yml # Container orchestration
```

### Component Pipeline

1. **API Service** (`api/`)
   - Handles incoming audio file uploads
   - Generates unique job IDs
   - Queues jobs for processing
   - Provides status endpoints

2. **Speech-to-Text Worker** (`stt-worker/`)
   - Processes audio files from the queue
   - Converts speech to text
   - Forwards text to LLM queue

3. **LLM Worker** (`llm-worker/`)
   - Processes text using LLM models
   - Generates responses
   - Queues text for speech synthesis
  
4. **TTS Worker** (`tts-worker/`)
   - Process text from the queue
   - Converts text to speech

5. **Redis Queue System**
   - Manages job queues between services
   - Handles job status tracking
   - Ensures reliable message passing

## 🚀 Getting Started

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/d1pankarmedhi/CascadeS2S.git
   cd CascadeS2S
   ```

2. Add env variables to `.env` file :
   ```bash
   # .env 
   GEMINI_API_KEY = <your-api-key>
   ```

3. Start the services:
   ```bash
   docker-compose up --build
   ```

### API Usage

#### Submit Audio for Processing

```bash
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: multipart/form-data" \
  -F "audio_file=@your_audio.wav"
```

The audio output can be accessed in the `output` directory with filename *"{job_id}_response.wav*".


## 🐳 Docker Compose Services

```yaml
services:
  stt-api:
    build: ./api 
    ports:
      - "8000:8000"
    volumes:
      - ./shared_data:/app/shared_data
    depends_on:
      - redis

  stt-worker:
    build: ./stt-worker
    volumes:
      - ./shared_data:/app/shared_data
    depends_on:
      - redis
    deploy:
      replicas: 1
    
  llm-worker:
    build: ./llm-worker
    volumes:
      - ./shared_data:/app/shared_data
    depends_on:
      - redis
    deploy:
      replicas: 1
    environment:
      - LLM_API=${LLM_API}

  tts-worker:
    build: ./tts-worker
    volumes:
      - ./shared_data:/app/shared_data
    depends_on:
      - redis
      - llm-worker
    deploy:
      replicas: 1
  
  redis:
    image: redis:6.2-alpine
    container_name: redis-queue
    ports:
      - "6379:6379"
```


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

