// public/vad-worklet.js
class VADProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.threshold = 0.0008; // Energy threshold for speech
    this.isSpeaking = false;
    this.silenceFrames = 0;
    this.silenceThreshold = 30; // Frames of silence before speech_ended
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    const channel = input[0];
    if (!channel) return true;
    
    let sum = 0;
    for (let i = 0; i < channel.length; i++) {
      sum += channel[i] * channel[i];
    }
    const rms = Math.sqrt(sum / channel.length);
    const hasVoice = rms > this.threshold;

    if (hasVoice) {
      this.silenceFrames = 0;
      if (!this.isSpeaking) {
        this.isSpeaking = true;
        this.port.postMessage({ type: 'speech_started', energy: rms });
      }
    } else {
      this.silenceFrames++;
      if (this.isSpeaking && this.silenceFrames > this.silenceThreshold) {
        this.isSpeaking = false;
        this.port.postMessage({ type: 'speech_ended' });
      }
    }
    
    // Always stream audio to the backend so it can do its own VAD and semantic barge-in
    const channelData = new Float32Array(channel);
    this.port.postMessage({ type: 'audio', data: channelData });

    // Always report energy for UI orb scaling
    this.port.postMessage({ type: 'energy', value: rms });

    return true;
  }
}

registerProcessor('vad-processor', VADProcessor);
