<div align="center">
<h1>Cascade Speech-to-Speech</h1>
<p>A low-latency, real-time voice agent platform featuring natural conversational turn-taking and semantic barge-in (interruption).
<br>Built with <b>FastAPI</b>, <b>React</b>, <b>WebSockets</b>, and <b>Redis</b>. Supported by <b>faster-whisper</b> and <b>Pocket TTS</b>.
</p>

![Python](https://img.shields.io/badge/Python-blue.svg?style=flat&logo=python&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff) ![Redis](https://img.shields.io/badge/Redis-%23DD0031.svg?logo=redis&logoColor=white) ![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)

<img width="800" alt="interface" src="assets/interface.png" />
</div>

## 🌟 Key Features

- **Real-Time Interruptible Voice**: "Duck and Decide" architecture allows you to instantly interrupt the AI ("barge-in") with sub-500ms latency.
- **Smart Turn-Taking**: Hybrid heuristic endpointing detects semantic boundaries (punctuation vs. filler words) to know exactly when you've finished speaking.
- **Semantic Barge-in**: Agent gracefully ignores non-verbal backchannels ("uh-huh", "yeah") without interrupting its own speech.
- **Modern React Frontend**: A beautiful, OpenAI-style "Breathing Orb" UI built with React, Vite, and Client-Side Web Audio API VAD (Voice Activity Detection).
- **Asynchronous API**: Highly optimized FastAPI gateway using `redis.asyncio` for zero-polling, fully non-blocking WebSocket streams.
- **Optimized AI Stack**: `faster-whisper` for fast STT, local LLMs (via Ollama), and `Pocket TTS` for speech generation.

## 🚀 Quick Start

### 1. Requirements
Ensure you have **Docker** and **Docker Compose** installed.
You will also need **Node.js** for the frontend.

### 2. Launch Backend Services
```bash
./manage.sh start
```

### 3. Launch Frontend UI
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
The application will be available at [http://localhost:5173](http://localhost:5173).

## 🏗️ Architecture

CascadeS2S relies on an event-driven microservice architecture connected via Redis Pub/Sub, allowing workers to operate concurrently and cancel ongoing generations instantly when an interruption occurs.

```mermaid
graph TD
    subgraph Frontend [React Frontend]
        UI[Breathing Orb UI]
        VAD[Client-Side VAD<br>AudioWorklet]
        Gain[Audio Ducking<br>Gain Node]
    end

    subgraph Backend [FastAPI Gateway]
        API[WebSocket API<br>Async Redis]
    end

    subgraph Workers [Python Microservices]
        STT[STT Worker<br>Faster-Whisper<br>Endpointing and Barge-in]
        LLM[LLM Worker<br>Ollama]
        TTS[TTS Worker<br>Pocket TTS]
    end

    Redis[(Redis Pub/Sub<br>Message Bus)]

    %% Connections
    UI <-->|WebSocket<br>PCM Audio & JSON| API
    VAD -->|Triggers volume ducking| Gain
    VAD -->|Emits speech_started| API
    
    API <-->|realtime_audio| Redis
    
    Redis <-->|realtime_audio| STT
    STT -->|system_control interrupt| Redis
    STT -->|realtime_llm| Redis
    
    Redis <-->|realtime_llm| LLM
    LLM -->|realtime_tts| Redis
    
    Redis <-->|realtime_tts| TTS
    TTS -->|response session_id| Redis
    
    Redis -->|system_control / response| API
```

### System Components:
- **`frontend/`**: React/Vite application. Uses `AudioWorklet` for low-latency VAD. Ducks agent audio to 20% on user speech.
- **`api/`**: Async FastAPI Gateway. Relays WebSockets to Redis channels. 
- **`stt-worker/`**: Speech-to-Text. Evaluates semantics to determine turn boundaries and checks for true barge-in vs. backchannels.
- **`llm-worker/`**: Language Model. Streams tokens. Listens to `system_control` to halt generation instantly on interruption.
- **`tts-worker/`**: Speech synthesis. Aborts queued audio generation if the session is interrupted.

### Data Flow (Barge-In Sequence):
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Redis
    participant STT as STT Worker
    participant LLM as LLM Worker
    participant TTS as TTS Worker

    User->>Frontend: Speaks
    Frontend->>Frontend: VAD detects speech
    Frontend->>Frontend: Duck agent audio to 20%
    Frontend->>API: {"type": "speech_started"}
    API->>Redis: Publish to realtime_audio
    Frontend->>API: Stream PCM Audio Bytes
    API->>Redis: Publish audio bytes
    
    Redis->>STT: Receive audio & speech_started
    STT->>STT: Analyze audio (Semantic Barge-in check at 500ms)
    
    alt Is Backchannel (e.g., "uh-huh")
        STT->>Redis: Publish {"type": "restore_audio"} to system_control
        Redis->>API: Route system_control
        API->>Frontend: Send restore_audio
        Frontend->>Frontend: Restore agent volume to 100%
    else Is True Interruption
        STT->>Redis: Publish {"action": "interrupt"} to system_control
        Redis->>LLM: Abort current generation
        Redis->>TTS: Flush pending audio jobs
        Redis->>API: Route system_control
        API->>Frontend: Send stop_audio
        Frontend->>Frontend: Halt playback immediately
    end
    
    User->>Frontend: Stops speaking
    Frontend->>API: {"type": "end_stream"}
    API->>Redis: Publish to realtime_audio
    
    STT->>STT: Hybrid Heuristic Endpointing (0.4s to 2.5s)
    STT->>Redis: Publish transcribed text to realtime_llm
    
    Redis->>LLM: Receive text
    LLM->>LLM: Generate response stream
    LLM->>Redis: Publish tokens to realtime_tts
    
    Redis->>TTS: Receive tokens
    TTS->>TTS: Synthesize audio
    TTS->>Redis: Publish audio payload to response session_id
    
    Redis->>API: Receive audio payload
    API->>Frontend: Stream audio bytes via WebSocket
    Frontend->>User: Plays agent response
```

## 📄 License
This project is licensed under the MIT License.
