import { useState, useEffect, useRef, useCallback } from 'react';

export function useVoiceAgent() {
  const [status, setStatus] = useState('disconnected'); // disconnected, idle, listening, thinking, speaking
  const [micEnergy, setMicEnergy] = useState(0);
  const [transcript, setTranscript] = useState([]);
  
  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const workletNodeRef = useRef(null);
  const streamRef = useRef(null);
  
  const playContextRef = useRef(null);
  const gainNodeRef = useRef(null);
  const nextPlayTimeRef = useRef(0);

  const connect = useCallback(async () => {
    setStatus('idle');
    try {
      playContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      gainNodeRef.current = playContextRef.current.createGain();
      gainNodeRef.current.connect(playContextRef.current.destination);

      const wsUrl = `ws://${window.location.hostname}:8000/ws/voice`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WS Connected');
        startMic();
      };

      wsRef.current.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          setStatus('speaking');
          const arrayBuffer = await event.data.arrayBuffer();
          playContextRef.current.decodeAudioData(arrayBuffer, (buffer) => {
            const source = playContextRef.current.createBufferSource();
            source.buffer = buffer;
            source.connect(gainNodeRef.current);
            
            const currentTime = playContextRef.current.currentTime;
            const playTime = Math.max(currentTime, nextPlayTimeRef.current);
            
            source.start(playTime);
            nextPlayTimeRef.current = playTime + buffer.duration;
            
            source.onended = () => {
              if (playContextRef.current.currentTime >= nextPlayTimeRef.current - 0.1) {
                 setStatus('idle');
              }
            };
          });
        } else {
          const data = JSON.parse(event.data);
          if (data.type === 'stop_audio') {
            if (playContextRef.current) {
              playContextRef.current.close();
              playContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
              gainNodeRef.current = playContextRef.current.createGain();
              gainNodeRef.current.connect(playContextRef.current.destination);
              nextPlayTimeRef.current = 0;
              setStatus('idle');
            }
          } else if (data.type === 'restore_audio') {
            if (gainNodeRef.current) {
              gainNodeRef.current.gain.setTargetAtTime(1.0, playContextRef.current.currentTime, 0.1);
            }
          } else if (data.type === 'transcription') {
            setTranscript(prev => [...prev, { role: 'user', text: data.text }]);
          } else if (data.type === 'llm_response') {
            setStatus('thinking');
            setTranscript(prev => {
              const newT = [...prev];
              const last = newT[newT.length - 1];
              if (last && last.role === 'agent' && !last.is_final) {
                last.text = data.text;
                last.is_final = data.is_final;
              } else {
                newT.push({ role: 'agent', text: data.text, is_final: data.is_final });
              }
              return newT;
            });
          }
        }
      };

      wsRef.current.onclose = () => {
        setStatus('disconnected');
        stopMic();
      };
    } catch (e) {
      console.error(e);
      setStatus('disconnected');
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    stopMic();
    if (playContextRef.current) {
      playContextRef.current.close();
    }
    setStatus('disconnected');
  }, []);

  const stopMic = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
  };

  const startMic = async () => {
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({ 
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } 
      });
      
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      
      await audioContextRef.current.audioWorklet.addModule('/vad-worklet.js');
      
      const source = audioContextRef.current.createMediaStreamSource(streamRef.current);
      workletNodeRef.current = new AudioWorkletNode(audioContextRef.current, 'vad-processor');
      
      let speechTimer = null;

      let lastEnergyTime = 0;
      workletNodeRef.current.port.onmessage = (e) => {
        const msg = e.data;
        if (msg.type === 'energy') {
          const now = performance.now();
          if (now - lastEnergyTime > 50) {
            setMicEnergy(msg.value);
            lastEnergyTime = now;
          }
        } else if (msg.type === 'speech_started') {
          setStatus('listening');
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'speech_started' }));
          }
          if (gainNodeRef.current && playContextRef.current) {
            gainNodeRef.current.gain.setTargetAtTime(0.2, playContextRef.current.currentTime, 0.05);
          }
        } else if (msg.type === 'speech_ended') {
          setStatus('thinking');
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'speech_ended' }));
          }
        } else if (msg.type === 'audio') {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            const pcm = new Int16Array(msg.data.length);
            for (let i = 0; i < msg.data.length; i++) {
              pcm[i] = Math.max(-1, Math.min(1, msg.data[i])) * 0x7FFF;
            }
            wsRef.current.send(pcm.buffer);
          }
        }
      };
      
      source.connect(workletNodeRef.current);
      // Dummy connect to destination is required to start worklet
      const dummyGain = audioContextRef.current.createGain();
      dummyGain.gain.value = 0;
      workletNodeRef.current.connect(dummyGain);
      dummyGain.connect(audioContextRef.current.destination);
      
    } catch (e) {
      console.error('Mic error:', e);
    }
  };

  return { status, micEnergy, transcript, connect, disconnect };
}
