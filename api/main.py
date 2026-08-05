import asyncio
import json
import os
import uuid
import grpc

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Import generated gRPC stubs
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if os.path.exists(os.path.join(parent_dir, "utils")):
    sys.path.append(parent_dir)
else:
    sys.path.append(current_dir)
from utils import voice_pb2, voice_pb2_grpc

STT_HOST = os.getenv("STT_HOST", "stt-worker:50051")
LLM_HOST = os.getenv("LLM_HOST", "llm-worker:50052")
TTS_HOST = os.getenv("TTS_HOST", "tts-worker:50053")

app = FastAPI(
    title="CascadeS2S Real-Time Voice API",
    description="API for real-time voice conversation with AI using gRPC.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    print(f"New WebSocket connection established: {session_id}")

    # Channels
    stt_channel = grpc.aio.insecure_channel(STT_HOST)
    llm_channel = grpc.aio.insecure_channel(LLM_HOST)
    tts_channel = grpc.aio.insecure_channel(TTS_HOST)

    stt_stub = voice_pb2_grpc.STTServiceStub(stt_channel)
    llm_stub = voice_pb2_grpc.LLMServiceStub(llm_channel)
    tts_stub = voice_pb2_grpc.TTSServiceStub(tts_channel)

    audio_queue = asyncio.Queue()

    async def stt_request_generator():
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                yield voice_pb2.AudioChunk(session_id=session_id, end_stream=True)
                break
            elif isinstance(chunk, dict):
                # Control signal
                yield voice_pb2.AudioChunk(
                    session_id=session_id, 
                    speech_started=chunk.get("speech_started", False),
                    end_stream=chunk.get("end_stream", False)
                )
            else:
                # Audio bytes
                yield voice_pb2.AudioChunk(session_id=session_id, data=chunk)

    async def process_llm_and_tts(text: str):
        """When STT yields a final transcript, stream it to LLM, then to TTS."""
        async def llm_request_generator():
            yield voice_pb2.TextChunk(session_id=session_id, text=text)
            yield voice_pb2.TextChunk(session_id=session_id, end_stream=True)

        try:
            llm_stream = llm_stub.GenerateStream(llm_request_generator())
            
            # Queue to pass text chunks from LLM to TTS
            tts_text_queue = asyncio.Queue()

            async def tts_request_generator():
                while True:
                    chunk = await tts_text_queue.get()
                    if chunk is None:
                        yield voice_pb2.TextChunk(session_id=session_id, end_stream=True)
                        break
                    yield voice_pb2.TextChunk(session_id=session_id, text=chunk)

            # Start TTS stream
            tts_stream = tts_stub.SynthesizeStream(tts_request_generator())

            # Read from LLM and send to client & TTS
            async def read_llm():
                print(f"[{session_id}] Started reading LLM stream...")
                try:
                    async for response in llm_stream:
                        print(f"[{session_id}] Received LLM chunk: '{response.text_chunk}'")
                        if response.text_chunk:
                            await websocket.send_json({
                                "type": "llm_response",
                                "text": response.text_chunk
                            })
                            await tts_text_queue.put(response.text_chunk)
                        
                        if response.stream_finished:
                            print(f"[{session_id}] LLM stream finished.")
                            break
                    await tts_text_queue.put(None) # EOF for TTS
                except Exception as e:
                    print(f"[{session_id}] ERROR in read_llm: {e}")

            # Read from TTS and send to client
            async def read_tts():
                print(f"[{session_id}] Started reading TTS stream...")
                try:
                    async for response in tts_stream:
                        print(f"[{session_id}] Received TTS chunk: {len(response.data)} bytes")
                        if response.data:
                            await websocket.send_bytes(response.data)
                    print(f"[{session_id}] TTS stream finished.")
                except Exception as e:
                    print(f"[{session_id}] ERROR in read_tts: {e}")

            print(f"[{session_id}] Gathering LLM and TTS tasks...")
            await asyncio.gather(read_llm(), read_tts())
            print(f"[{session_id}] Cascade for utterance finished successfully.")
            
        except Exception as e:
            print(f"[{session_id}] Error in LLM/TTS pipeline: {e}")


    async def listen_stt(stt_stream):
        try:
            async for response in stt_stream:
                if response.interrupt or response.restore_audio:
                    # Semantic barge-in
                    action = "stop_audio" if response.interrupt else "restore_audio"
                    await websocket.send_json({"type": action})
                
                if response.text:
                    await websocket.send_json({
                        "type": "transcription",
                        "text": response.text
                    })
                    
                    if response.is_final:
                        # Launch LLM/TTS cascade for this utterance
                        asyncio.create_task(process_llm_and_tts(response.text))
        except grpc.aio.AioRpcError as e:
            print(f"STT gRPC error: {e}")
            try:
                await websocket.close(code=1011, reason="STT Service Unavailable")
            except Exception:
                pass
        except Exception as e:
            print(f"STT stream listener error: {e}")
            try:
                await websocket.close(code=1011, reason="Internal Error")
            except Exception:
                pass

    try:
        # Start STT stream
        stt_stream = stt_stub.TranscribeStream(stt_request_generator())
        listen_task = asyncio.create_task(listen_stt(stt_stream))

        while True:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(code=data.get("code", 1000))
                
            if "bytes" in data and data["bytes"]:
                await audio_queue.put(data["bytes"])
            elif "text" in data and data["text"]:
                print(f"Received websocket text: {data['text']}")
                message = json.loads(data["text"])
                if message.get("type") == "end_stream":
                    await audio_queue.put({"end_stream": True})
                elif message.get("type") == "speech_started":
                    await audio_queue.put({"speech_started": True})

    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"WebSocket error for {session_id}: {e}")
    finally:
        await audio_queue.put(None) # Shutdown generator
        await stt_channel.close()
        await llm_channel.close()
        await tts_channel.close()
        print(f"Session cleaned up: {session_id}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
