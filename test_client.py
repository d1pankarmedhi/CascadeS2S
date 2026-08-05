import asyncio
import websockets
import wave
import json
import time

async def test_audio():
    uri = "ws://127.0.0.1:8000/ws/voice"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected. Opening audio file...")
            
            # Start a background task to receive messages
            async def receive_messages():
                try:
                    async for message in websocket:
                        if isinstance(message, str):
                            data = json.loads(message)
                            safe_text = str(data).encode('cp1252', errors='replace').decode('cp1252')
                            print(f"[RECV JSON] {safe_text}")
                        else:
                            print(f"[RECV AUDIO] {len(message)} bytes (TTS output)")
                except Exception as e:
                    print(f"Receive loop ended: {e}")
            
            receive_task = asyncio.create_task(receive_messages())
            
            # Open WAV file and stream it
            with wave.open("testaudio_16000_test01_20s.wav", "rb") as wf:
                print(f"WAV Info: {wf.getnchannels()} channels, {wf.getsampwidth()} bytes/sample, {wf.getframerate()} Hz")
                if wf.getframerate() != 16000 or wf.getsampwidth() != 2:
                    print("WARNING: Test assumes 16kHz 16-bit PCM!")
                
                print("Streaming audio in real-time...")
                
                chunk_frames = 128  # 128 frames at 16kHz = 8ms chunks
                frames_sent = 0
                
                start_time = time.time()
                
                while True:
                    data = wf.readframes(chunk_frames)
                    if not data:
                        break
                    
                    # Send binary audio data
                    await websocket.send(data)
                    frames_sent += chunk_frames
                    
                    # Pace to real-time to allow VAD to work naturally
                    expected_duration = frames_sent / wf.getframerate()
                    elapsed = time.time() - start_time
                    if expected_duration > elapsed:
                        await asyncio.sleep(expected_duration - elapsed)
            
            print(f"Finished sending {frames_sent} frames in {time.time() - start_time:.2f} seconds.")
            
            print("Streaming silence to trigger VAD response...")
            silence_chunk = b'\x00' * (chunk_frames * 2)
            silence_start = time.time()
            
            while time.time() - silence_start < 8:
                await websocket.send(silence_chunk)
                await asyncio.sleep(0.008)
                
            print("Holding connection open for 120s to await LLM and TTS responses...")
            await asyncio.sleep(120)
            
            print("Test complete. Cancelling receiver...")
            receive_task.cancel()
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_audio())
