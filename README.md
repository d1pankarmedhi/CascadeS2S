<div align="center">
<h1>Cascade Speech-to-Speech</h1>
<p>A real-time voice agent platform that enables natural conversations with AI. Built with microservices architecture using FastAPI, WebSockets, Redis, and powered by faster-whisper for 10x faster transcription.
</p>

![Python](https://img.shields.io/badge/Python-blue.svg?style=flat&logo=python&logoColor=white) ![Hugging Face](https://img.shields.io/badge/Hugging%20Face-FFD21E?logo=huggingface&logoColor=000) ![Redis](https://img.shields.io/badge/Redis-%23DD0031.svg?logo=redis&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff) ![Google Gemini](https://img.shields.io/badge/Google%20Gemini-886FBF?logo=googlegemini&logoColor=fff)

<img width="800" height="137" alt="image" src="https://github.com/user-attachments/assets/552b2bdc-0ce1-4ad5-8a3a-f85df39567a1" />

</div>



## 🌟 Features

- **Real-Time Voice Conversations**: Talk directly to AI with minimal latency (< 2 seconds)
- **Beautiful Web Interface**: Premium dark mode UI with glassmorphism effects
- **WebSocket Streaming**: Bidirectional audio streaming for live interactions
- **Faster-Whisper Integration**: 10x faster transcription compared to OpenAI Whisper
- **Conversational AI**: Natural, context-aware responses optimized for voice
- **Microservices Architecture**: Scalable, distributed system design
- **Docker Containerization**: Easy deployment and orchestration
- **Redis Pub/Sub**: Real-time communication between services
- **Batch Processing Support**: Legacy API for file-based processing
- **Robust Error Handling**: Comprehensive logging and error recovery

## 🏗️ Architecture

The project features dual-mode operation: **Real-Time** and **Batch Processing**.

```
├── api/               # WebSocket & REST API service
├── stt-worker/        # Speech-to-Text (faster-whisper)
├── llm-worker/        # Language Model (Google Gemini)
├── tts-worker/        # Text-to-Speech (ParlerTTS)
└── docker-compose.yml # Container orchestration
```

### Real-Time Voice Agent Pipeline

1. **Web Interface** (`api/static/`)
   - Beautiful, responsive voice UI
   - Real-time microphone access
   - WebSocket client for audio streaming
   - Live conversation display

2. **API Service** (`api/`)
   - WebSocket endpoint for bidirectional streaming
   - Session management for concurrent users
   - Redis pub/sub for worker communication
   - Static file serving

3. **Speech-to-Text Worker** (`stt-worker/`)
   - Receives audio chunks via Redis pub/sub
   - Uses faster-whisper for 10x speed improvement
   - Processes audio in real-time
   - Forwards transcription to LLM

4. **LLM Worker** (`llm-worker/`)
   - Processes text via Redis pub/sub
   - Optimized conversational prompts
   - Generates concise, natural responses
   - Sends text to TTS

5. **TTS Worker** (`tts-worker/`)
   - Synthesizes speech via Redis pub/sub
   - Generates audio files
   - Streams audio back to client
   
6. **Redis**
   - Pub/sub channels for real-time communication
   - Queues for batch processing
   - Session data storage

## 🚀 Getting Started

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/d1pankarmedhi/CascadeS2S.git
   cd CascadeS2S
   ```

2. Start the services:
   ```bash
   docker compose up --build
   ```
   *Note: On first startup, Ollama will automatically pull the Qwen 2.5:3b model (approx. 1.9GB). Subsequent starts will be immediate.*

### Management Script

For convenience, a `manage.sh` script is provided to handle common operations:

- **Start**: `./manage.sh start` (Builds and starts in detached mode)
- **Stop**: `./manage.sh stop`
- **Logs**: `./manage.sh logs` (Follow logs)
- **Status**: `./manage.sh status`
- **Pull Model**: `./manage.sh pull-llm` (Manually pull Qwen 2.5)
- **Clean**: `./manage.sh clean` (Remove containers and images)

### Real-Time Voice Agent Usage

1. **Open your browser** and navigate to:
   ```
   http://localhost:8000
   ```

2. **Grant microphone permissions** when prompted

3. **Click "Start Conversation"** to begin talking with the AI

4. **Speak naturally** - your voice is processed in real-time with these steps:
   - Your speech is captured and streamed
   - Transcribed to text (faster-whisper)
   - Processed by AI (Google Gemini)
   - Converted back to speech (ParlerTTS)
   - Played back automatically

5. **Watch the conversation** unfold in the transcript panel

### Legacy Batch Processing API

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

