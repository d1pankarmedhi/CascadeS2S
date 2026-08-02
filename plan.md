# Implementation Plan: Real-Time Voice Agent with Barge-In

This document outlines the end-to-end plan for transforming the current CascadeS2S pipeline into a completely real-time, interruptible voice agent using the "Duck and Decide" architecture.

## Phase 1: Infrastructure Plumbing (The Kill Switch)
*Goal: Ensure the server can instantly abort generation and playback when an interruption is detected.*

1. **Redis Pub/Sub for Control Signals**
   - Create a new Redis channel: `system_control`.
   - Define a JSON payload standard for control events: `{"action": "interrupt", "session_id": "<uuid>"}`.

2. **Update `llm-worker/worker.py`**
   - Refactor the `process_realtime_requests` loop to listen to `system_control` on a background thread.
   - Maintain a shared state `active_sessions[session_id] = {"is_cancelled": False}`.
   - Inside the Ollama streaming loop (`for chunk in stream:`), check `is_cancelled`. If true, `break` the loop immediately, stop sending chunks to TTS, and log the cancellation.

3. **Update `tts-worker/worker.py`**
   - Similar to the LLM worker, listen to `system_control`.
   - Maintain a set of cancelled sessions. 
   - Before synthesizing a sentence chunk, check if the session is cancelled. If so, discard the chunk.

4. **Update `api/main.py`**
   - When an `interrupt` signal is received via `system_control`, send a WebSocket message to the client: `{"type": "stop_audio"}`.

## Phase 2: Frontend Overhaul (VAD, AEC, & Ducking)
*Goal: Move speech detection to the edge to save bandwidth and implement instantaneous volume ducking.*

1. **Acoustic Echo Cancellation (AEC)**
   - Update `static/index.html` (or the frontend codebase) to explicitly request AEC and noise suppression when acquiring the microphone:
     ```javascript
     navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
     ```

2. **Client-Side VAD (Web Audio API)**
   - Implement an `AudioWorkletNode` that calculates audio energy locally.
   - Only transmit audio bytes over the WebSocket when energy exceeds the speech threshold.
   - Send `{"type": "speech_started"}` when the user starts speaking, and `{"type": "speech_ended"}` when they stop.

3. **The "Duck" Action**
   - When the client VAD detects local speech, immediately reduce the volume of the HTML5 Audio element (or Web Audio context) playing the agent's voice to 20%.

## Phase 3: The Brain (Semantics & Turn-Taking)
*Goal: Make the STT worker intelligent enough to differentiate backchannels from interruptions and predict when the user is done speaking.*

1. **Update `stt-worker/worker.py` - Semantic Completeness (Endpointing)**
   - Remove the hardcoded `0.5s` silence trigger.
   - Implement the Hybrid Heuristic:
     - **Fast Turn (0.4s silence):** Trigger if the transcript ends with `?`, `.`, or `!`.
     - **Thinking Turn (2.0s silence):** Trigger if the transcript ends with filler words ("um", "uh", "so") or lacks punctuation.
     - **Fallback (2.5s silence):** Always trigger.

2. **Update `stt-worker/worker.py` - Semantic Barge-In**
   - When the server receives a `speech_started` event from the client, the agent is already "ducked" on the frontend.
   - Buffer the incoming audio and run a fast, initial STT pass (e.g., after 500ms of audio).
   - Check the transcript against a list of common backchannels ("yeah", "uh-huh", "right", "mhm").
   - **Decision:**
     - If it IS a backchannel: Send `{"type": "restore_audio"}` to the client. The agent's volume goes back to 100%.
     - If it IS NOT a backchannel: Broadcast `{"action": "interrupt", "session_id": "<uuid>"}` to `system_control`. The LLM/TTS abort, and the client stops audio playback completely.

## Phase 4: New React UI (OpenAI Style)
*Goal: Create a premium, completely separate React application with a dynamic "breathing" voice interface and a text chat toggle.*

1. **Project Setup**
   - Initialize a new React project using Vite (e.g., `npx create-vite-app`).
   - Use Vanilla CSS for styling to allow maximum control over complex CSS animations and micro-interactions.

2. **The "Breathing" UI Component**
   - Design a central, circular orb UI that responds to audio activity.
   - Implement CSS keyframe animations for the "breathing" effect (pulsing scale, radial gradients, and box-shadow glows).
   - Wire the orb's animation state to the WebSocket events:
     - **Idle:** Slow, gentle pulsing.
     - **Listening:** Expanding and contracting based on user mic energy levels (from the AudioWorklet).
     - **Thinking:** A distinct color shift or rotation animation while waiting for the LLM.
     - **Speaking:** Rapid, dynamic pulsing mapped to the audio playback of the TTS.

3. **Chat Transcript Toggle**
   - Add a sleek, animated slide-out panel or a secondary view to display the live text transcript of the conversation.
   - As STT and LLM events stream in from the WebSocket, update the chat history in real-time.
   - Ensure the UI remains primarily voice-focused, with the chat acting as an accessible fallback or history log.

4. **Integration with Phase 2 (VAD & AEC)**
   - Port all logic from Phase 2 (requesting microphone with AEC, Web Audio API Worklet for VAD, and the "Ducking" logic) directly into React hooks within this new interface.
