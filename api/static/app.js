// WebSocket and Audio Management
let ws = null;
let audioContext = null;
let audioSource = null;
let audioProcessor = null;
let audioStream = null;
let isRecording = false;

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
            await playAudioResponse(event.data);

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
            } else if (data.type === 'llm_response') {
                addTranscriptMessage('assistant', data.text);
            } else if (data.type === 'status') {
                console.log('Status update:', data.message);
                if (data.message === 'processing') {
                    updateStatus('processing', 'Processing...');
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
async function playAudioResponse(audioBlob) {
    return new Promise((resolve, reject) => {
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);

        audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            resolve();
        };

        audio.onerror = (error) => {
            console.error('Error playing audio:', error);
            URL.revokeObjectURL(audioUrl);
            reject(error);
        };

        audio.play().catch(reject);
    });
}

// UI Updates
function updateStatus(state, text) {
    statusText.textContent = text;
    statusIcon.className = 'status-icon ' + state;

    // Hide all icons
    micIcon.classList.add('hidden');
    processingIcon.classList.add('hidden');
    speakingIcon.classList.add('hidden');

    // Show appropriate icon
    switch (state) {
        case 'listening':
            micIcon.classList.remove('hidden');
            break;
        case 'processing':
            processingIcon.classList.remove('hidden');
            break;
        case 'speaking':
            speakingIcon.classList.remove('hidden');
            break;
        default:
            micIcon.classList.remove('hidden');
    }
}

function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.classList.add('connected');
        connectionStatus.querySelector('span').textContent = 'Connected';
    } else {
        connectionStatus.classList.remove('connected');
        connectionStatus.querySelector('span').textContent = 'Disconnected';
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
    transcript.scrollTop = transcript.scrollHeight;
}

function clearTranscript() {
    transcript.innerHTML = '<p class="placeholder">Your conversation will appear here...</p>';
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
