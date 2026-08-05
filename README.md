<div align="center">
<h1>Cascade Speech-to-Speech</h1>
<p>A low-latency, real-time voice agent platform featuring natural conversational turn-taking and semantic barge-in (interruption).
<br>Built with <b>FastAPI</b>, <b>React</b>, <b>WebSockets</b>, and <b>gRPC</b>. Supported by <b>faster-whisper</b> and <b>Pocket TTS</b>.
</p>

![Python](https://img.shields.io/badge/Python-blue.svg?style=flat&logo=python&logoColor=white) ![gRPC](https://img.shields.io/badge/gRPC-244C5A.svg?logo=grpc&logoColor=white) ![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)

<img width="800" alt="interface" src="assets/interface.png" />
</div>

## 🌟 Key Features

- **Real-Time Interruptible Voice**: "Duck and Decide" architecture allows you to instantly interrupt the AI ("barge-in") with sub-500ms latency.
- **Smart Turn-Taking**: Hybrid heuristic endpointing detects semantic boundaries (punctuation vs. filler words) to know exactly when you've finished speaking.
- **Semantic Barge-in**: Agent gracefully ignores non-verbal backchannels ("uh-huh", "yeah") without interrupting its own speech.
- **Modern React Frontend**: A beautiful, OpenAI-style "Breathing Orb" UI built with React, Vite, and Client-Side Web Audio API VAD (Voice Activity Detection).
- **Asynchronous API**: Highly optimized FastAPI gateway using `grpc.aio` for fully non-blocking, point-to-point bidirectional streams.
- **Optimized AI Stack**: `faster-whisper` for fast STT, local LLMs (via Ollama), and `Pocket TTS` for speech generation.

## 🚀 Quick Start

### 1. Requirements
Ensure you have **Python 3.10+** installed, as well as **Node.js** for the frontend.
You must also have [Ollama](https://ollama.com/) running locally.

### 2. Install Backend Dependencies
```bash
uv sync --all-packages
```

### 3. Launch Backend Services
```bash
./start_local.sh
```

### 4. Launch Frontend UI
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
The application will be available at [http://localhost:5173](http://localhost:5173).

## 🏗️ Architecture

CascadeS2S relies on a gRPC microservice architecture. The FastAPI gateway orchestrates bidirectional streams with worker nodes, allowing for ultra-low latency point-to-point communication and instantaneous interruption capabilities.

```mermaid
graph TD
    subgraph Frontend [React Frontend]
        UI[Breathing Orb UI]
        VAD[Client-Side VAD<br>AudioWorklet]
        Gain[Audio Ducking<br>Gain Node]
    end

    subgraph Backend [FastAPI Gateway]
        API[WebSocket API<br>gRPC Orchestrator]
    end

    subgraph Workers [gRPC Microservices]
        STT[STT Worker<br>Faster-Whisper]
        LLM[LLM Worker<br>Ollama]
        TTS[TTS Worker<br>Pocket TTS]
    end

    %% Connections
    UI <-->|WebSocket<br>PCM Audio & JSON| API
    VAD -->|Triggers volume ducking| Gain
    VAD -->|Emits speech_started| API
    
    API <-->|gRPC Bidirectional Stream<br>AudioChunk / STTEvent| STT
    API <-->|gRPC Bidirectional Stream<br>TextChunk / LLMEvent| LLM
    API <-->|gRPC Bidirectional Stream<br>TextChunk / AudioChunk| TTS
```

### System Components:
- **`frontend/`**: React/Vite application. Uses `AudioWorklet` for low-latency VAD. Ducks agent audio to 20% on user speech.
- **`api/`**: Async FastAPI Gateway. Relays WebSockets to gRPC bidirectional streams. 
- **`stt-worker/`**: Speech-to-Text gRPC server. Evaluates semantics to determine turn boundaries and checks for true barge-in vs. backchannels.
- **`llm-worker/`**: Language Model gRPC server. Streams tokens and halts generation instantly on stream disconnect.
- **`tts-worker/`**: Speech synthesis gRPC server. Synthesizes text chunks directly into audio byte streams.

### Data Flow (Barge-In Sequence):
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant STT as STT Service
    participant LLM as LLM Service
    participant TTS as TTS Service

    User->>Frontend: Speaks
    Frontend->>Frontend: VAD detects speech
    Frontend->>Frontend: Duck agent audio to 20%
    Frontend->>API: {"type": "speech_started"}
    API->>STT: Stream AudioChunk (speech_started=True)
    Frontend->>API: Stream PCM Audio Bytes
    API->>STT: Stream AudioChunk (bytes)
    
    STT->>STT: Analyze audio (Semantic Barge-in check at 500ms)
    
    alt Is Backchannel (e.g., "uh-huh")
        STT->>API: Yield STTEvent (restore_audio=True)
        API->>Frontend: Send restore_audio
        Frontend->>Frontend: Restore agent volume to 100%
    else Is True Interruption
        STT->>API: Yield STTEvent (interrupt=True)
        API->>Frontend: Send stop_audio
        Frontend->>Frontend: Halt playback immediately
    end
    
    User->>Frontend: Stops speaking
    Frontend->>API: {"type": "end_stream"}
    API->>STT: Stream AudioChunk (end_stream=True)
    
    STT->>STT: Hybrid Heuristic Endpointing
    STT->>API: Yield STTEvent (is_final=True, text="...")
    
    API->>LLM: Stream TextChunk (text="...")
    LLM->>LLM: Generate response stream
    LLM->>API: Yield LLMEvent (text_chunk="...")
    
    API->>TTS: Stream TextChunk (text="...")
    TTS->>TTS: Synthesize audio
    TTS->>API: Yield AudioChunk (bytes)
    
    API->>Frontend: Stream audio bytes via WebSocket
    Frontend->>User: Plays agent response
```

## 📄 License
This project is licensed under the MIT License.
