import json
import os
import shutil
import uuid

import redis
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

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
    title="Asynchronous Speech-to-Text API",
    description="API to queue audio files for transcription.",
    version="1.0.0",
)


@app.post("/transcribe")
async def queue_transcription(audio_file: UploadFile = File(...)):
    """
    Receives an audio file, saves it, and adds a transcription job to the queue.
    Returns a job ID for status tracking.
    """
    if not r:
        raise HTTPException(status_code=503, detail="Redis service is not available.")

    job_id = str(uuid.uuid4())
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
