import asyncio
import json
import os
import shutil
import uuid
from typing import Dict

import redis
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Redis connection setup
try:
    r = redis.Redis(host="redis", port=6379, db=0)
    # Check if the connection is working
    r.ping()
    print("API connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    print(f"API could not connect to Redis: {e}")
    r = None

# FastAPI app setup
app = FastAPI(
    title="CascadeS2S Real-Time Voice API",
    description="API for real-time voice conversation with AI.",
    version="2.0.0",
)

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Session management
active_sessions: Dict[str, dict] = {}


@app.get("/")
async def root():
    """Serve the main web interface."""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice conversation.
    Handles bidirectional audio streaming.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    if not r:
        await websocket.send_json({"type": "error", "message": "Redis service not available"})
        await websocket.close()
        return
    
    # Create session with telemetry tracking
    active_sessions[session_id] = {
        "websocket": websocket,
        "audio_buffer": b"",
        "context": [],
        "chunks": 0,
        "bytes": 0
    }
    
    print(f"New WebSocket connection established: {session_id}")
    
    # Create pubsub for this session to receive responses
    pubsub = r.pubsub()
    pubsub.subscribe(f"response:{session_id}")
    
    try:
        # Start listening for responses from workers in background
        async def listen_for_responses():
            """Listen for responses from workers and send to client."""
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message and message['type'] == 'message':
                    data = json.loads(message['data'])
                    
                    if data.get('type') == 'transcription':
                        await websocket.send_json(data)
                    elif data.get('type') == 'llm_response':
                        await websocket.send_json(data)
                    elif data.get('type') == 'audio':
                        # Send binary audio data
                        audio_path = data.get('audio_path')
                        if audio_path and os.path.exists(audio_path):
                            with open(audio_path, 'rb') as f:
                                audio_data = f.read()
                            await websocket.send_bytes(audio_data)
                            # Clean up audio file
                            os.remove(audio_path)
                
                await asyncio.sleep(0.01)
        
        # Start background task
        response_task = asyncio.create_task(listen_for_responses())
        
        # Main loop: receive audio from client
        while True:
            data = await websocket.receive()
            
            if "bytes" in data:
                # Received audio chunk
                audio_chunk = data["bytes"]
                
                # Track metrics
                session_data = active_sessions[session_id]
                session_data["chunks"] += 1
                session_data["bytes"] += len(audio_chunk)
                
                if session_data["chunks"] % 20 == 0:
                    print(f"Session {session_id}: Received {session_data['chunks']} chunks ({session_data['bytes']} total bytes)")
                
                # Send to STT worker via Redis pubsub
                job_payload = {
                    "session_id": session_id,
                    "audio_chunk": audio_chunk.hex(),
                    "timestamp": asyncio.get_event_loop().time()
                }
                r.publish("realtime_audio", json.dumps(job_payload))
            
            elif "text" in data:
                message = json.loads(data["text"])
                
                if message.get("type") == "end_stream":
                    print(f"Session {session_id}: End of stream signal received. Total bytes: {active_sessions.get(session_id, {}).get('bytes', 0)}")
                    # Signal end of audio stream
                    r.publish("realtime_audio", json.dumps({
                        "session_id": session_id,
                        "type": "end_stream"
                    }))
                    
                    # Reset counters for next potential recording in same session
                    if session_id in active_sessions:
                        active_sessions[session_id]["chunks"] = 0
                        active_sessions[session_id]["bytes"] = 0
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"WebSocket error for {session_id}: {e}")
    finally:
        # Cleanup
        response_task.cancel()
        pubsub.unsubscribe(f"response:{session_id}")
        pubsub.close()
        if session_id in active_sessions:
            del active_sessions[session_id]
        print(f"Session cleaned up: {session_id}")


@app.post("/transcribe")
async def queue_transcription(audio_file: UploadFile = File(...)):
    """
    [LEGACY ENDPOINT - Batch Processing]
    Receives an audio file, saves it, and adds a transcription job to the queue.
    Returns a job ID for status tracking.
    """
    if not r:
        raise HTTPException(status_code=503, detail="Redis service is not available.")

    job_id = str(uuid.uuid4())
    os.makedirs("shared_data", exist_ok=True)
    file_path = f"shared_data/{job_id}_{audio_file.filename}"

    try:
        # Save the audio file to the shared volume
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # Create a job payload and push it to the queue
        job_payload = {"job_id": job_id, "file_path": file_path}
        r.lpush("transcription_jobs", json.dumps(job_payload))

        return JSONResponse(
            content={"message": "Transcription job submitted.", "job_id": job_id}
        )
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {e}")


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    [LEGACY ENDPOINT - Batch Processing]
    Retrieves the status and result of a transcription job.
    """
    if not r:
        raise HTTPException(status_code=503, detail="Redis service is not available.")

    result = r.get(f"result:{job_id}")

    if result:
        return JSONResponse(content=json.loads(result))
    else:
        return JSONResponse(content={"job_id": job_id, "status": "pending"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
