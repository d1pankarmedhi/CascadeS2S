// WebSocket and Audio Management
let ws = null;
let audioContext = null;
let audioSource = null;
let audioProcessor = null;
let audioStream = null;
let isRecording = false;
let lastAssistantMessage = null;

// DOM Elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusText = document.getElementById('statusText');
const statusIcon = document.getElementById('statusIcon');
const micIcon = document.getElementById('micIcon');
const processingIcon = document.getElementById('processingIcon');
const speakingIcon = document.getElementById('speakingIcon');
const connectionStatus = document.getElementById('connectionStatus');
const transcript = document.getElementById('transcript');
const clearBtn = document.getElementById('clearBtn');

// WebSocket Connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/voice`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);
        updateStatus('ready', 'Connected - Ready to start');
    };

    ws.onmessage = async (event) => {
        console.log('Received message from server');

        if (event.data instanceof Blob) {
            // Received audio blob from TTS
            updateStatus('speaking', 'Speaking...');
            const audioUrl = URL.createObjectURL(event.data);
            if (lastAssistantMessage) {
                appendAudioPlayer(lastAssistantMessage, audioUrl);
            }
            await playAudioResponse(audioUrl);

            // After playing audio, go back to listening
            if (isRecording) {
                updateStatus('listening', 'Listening...');
            } else {
                updateStatus('ready', 'Ready to start');
            }
        } else {
            // Text message (transcription or status update)
            const data = JSON.parse(event.data);

            if (data.type === 'transcription') {
                addTranscriptMessage('user', data.text);
                lastAssistantMessage = null;
            } else if (data.type === 'llm_response') {
                lastAssistantMessage = addTranscriptMessage('assistant', data.text);
            } else if (data.type === 'latency_report') {
                console.log('Latency report received:', data.metrics);
                if (lastAssistantMessage) {
                    appendLatencyMetrics(lastAssistantMessage, data.metrics);
                }
            } else if (data.type === 'error') {
                console.error('Server error:', data.message);
                updateStatus('ready', 'Error: ' + data.message);
            }
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
        updateStatus('ready', 'Connection error');
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);
        updateStatus('ready', 'Disconnected');

        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
            if (!ws || ws.readyState === WebSocket.CLOSED) {
                console.log('Attempting to reconnect...');
                connectWebSocket();
            }
        }, 3000);
    };
}

// Audio Recording with Web Audio API (Raw PCM)
async function startRecording() {
    try {
        console.log('Starting audio recording...');

        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000
        });

        console.log('AudioContext created. State:', audioContext.state, 'Sample rate:', audioContext.sampleRate);

        if (audioContext.state === 'suspended') {
            await audioContext.resume();
            console.log('AudioContext resumed. State:', audioContext.state);
        }

        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        audioSource = audioContext.createMediaStreamSource(audioStream);

        // Use a fixed buffer size that is a power of 2
        audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);

        let chunkCount = 0;
        let totalBytes = 0;

        audioProcessor.onaudioprocess = (e) => {
            if (!isRecording || !ws || ws.readyState !== WebSocket.OPEN) return;

            const inputData = e.inputBuffer.getChannelData(0);

            // Convert Float32 to Int16 PCM
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                const s = Math.max(-1, Math.min(1, inputData[i]));
                pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }

            // Send raw bytes
            const bytes = pcmData.buffer;
            ws.send(bytes);

            chunkCount++;
            totalBytes += bytes.byteLength;
            if (chunkCount % 20 === 0) {
                console.log(`Sent ${chunkCount} chunks (${totalBytes} total bytes)`);
            }
        };

        // Important: connect the processor to destination to trigger events
        audioSource.connect(audioProcessor);
        audioProcessor.connect(audioContext.destination);

        isRecording = true;
        updateStatus('listening', 'Listening...');
        startBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');

    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Could not access microphone: ' + error.message);
    }
}

function stopRecording() {
    console.log('Stopping recording...');
    isRecording = false;

    // Stop tracks and release microphone
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        audioStream = null;
    }

    if (audioProcessor) {
        audioProcessor.disconnect();
        audioProcessor = null;
    }

    if (audioSource) {
        audioSource.disconnect();
        audioSource = null;
    }

    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    // Send end-of-stream signal to server
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'end_stream' }));
    }

    updateStatus('ready', 'Ready to start');
    stopBtn.classList.add('hidden');
    startBtn.classList.remove('hidden');
}

// Audio Playback for Responses
async function playAudioResponse(audioUrl) {
    return new Promise((resolve, reject) => {
        const audio = new Audio(audioUrl);

        audio.onended = () => {
            resolve();
        };

        audio.onerror = (error) => {
            console.error('Error playing audio:', error);
            reject(error);
        };

        audio.play().catch(reject);
    });
}

function appendAudioPlayer(container, audioUrl) {
    const playerContainer = document.createElement('div');
    playerContainer.className = 'audio-player-container';

    const audio = document.createElement('audio');
    audio.controls = true;
    audio.src = audioUrl;

    const downloadLink = document.createElement('a');
    downloadLink.href = audioUrl;
    downloadLink.download = `response_${Date.now()}.wav`;
    downloadLink.className = 'download-link';
    downloadLink.title = 'Download Audio';
    downloadLink.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
    `;

    playerContainer.appendChild(audio);
    playerContainer.appendChild(downloadLink);
    container.appendChild(playerContainer);

    // Scroll to bottom after adding player
    transcript.scrollTop = transcript.scrollHeight;
}

function appendLatencyMetrics(container, metrics) {
    const latencyDiv = document.createElement('div');
    latencyDiv.className = 'latency-metrics';

    // Calculate Client E2E (from server trigger to now)
    const now = Date.now() / 1000;
    const clientE2E = (now - metrics.trigger_time) * 1000;

    const format = (ms) => `${ms.toFixed(2)}ms (${(ms / 1000).toFixed(1)}s)`;

    latencyDiv.innerHTML = `
        <div class="latency-row">STT Latency: ${format(metrics.stt_latency_ms)}</div>
        <div class="latency-row">LLM Latency: ${format(metrics.llm_latency_ms)}</div>
        <div class="latency-row">TTS Latency: ${format(metrics.tts_latency_ms)}</div>
        <div class="latency-row total">Total Pipeline Latency: ${format(metrics.pipeline_latency_ms)}</div>
        <div class="latency-row e2e">Client End-to-End Latency: ${format(clientE2E)}</div>
    `;

    container.appendChild(latencyDiv);

    // Scroll to bottom
    transcript.scrollTop = transcript.scrollHeight;
}

// UI Updates
function updateStatus(state, text) {
    statusText.textContent = text;
    // statusIcon and specific icons are now handled more minimally or hidden
    console.log(`Status changed to: ${state} (${text})`);

    // We could add visual feedback to the action bar here if needed
}

function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        connectionStatus.classList.remove('connected');
        statusText.textContent = 'Disconnected';
    }
}

function addTranscriptMessage(role, text) {
    // Remove placeholder if it exists
    const placeholder = transcript.querySelector('.placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const label = document.createElement('div');
    label.className = 'message-label';
    label.textContent = role === 'user' ? 'You' : 'Assistant';

    const messageText = document.createElement('div');
    messageText.className = 'message-text';
    messageText.textContent = text;

    messageDiv.appendChild(label);
    messageDiv.appendChild(messageText);
    transcript.appendChild(messageDiv);

    // Scroll to bottom
    transcript.scrollTo({
        top: transcript.scrollHeight,
        behavior: 'smooth'
    });

    return messageDiv;
}

function clearTranscript() {
    transcript.innerHTML = '<div class="placeholder">How can I help you today?</div>';
    lastAssistantMessage = null;
}

// Event Listeners
startBtn.addEventListener('click', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        startRecording();
    } else {
        alert('Not connected to server. Please wait...');
    }
});

stopBtn.addEventListener('click', stopRecording);
clearBtn.addEventListener('click', clearTranscript);

// Initialize
connectWebSocket();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (isRecording) {
        stopRecording();
    }
    if (ws) {
        ws.close();
    }
});
