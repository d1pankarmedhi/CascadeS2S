# app/main.py
import os
import shutil

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.transcribe.model import transcribe_audio_file

# --- Set up the FastAPI app ---
app = FastAPI(
    title="Speech-to-Text API",
    description="A simple API to transcribe audio files using OpenAI's Whisper model.",
    version="1.0.0",
)


# --- API Endpoint ---
@app.post("/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribes an uploaded audio file and returns the text.

    - **audio_file**: The audio file to transcribe (e.g., MP3, WAV, M4A).
    """
    # Create a temporary file to save the uploaded audio
    temp_file_path = f"temp_{audio_file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # Call the dedicated ML service function to transcribe the file
        print(f"Calling ML service for transcription of {audio_file.filename}...")
        transcribed_text = transcribe_audio_file(temp_file_path)

        return JSONResponse(content={"transcribed_text": transcribed_text})

    except RuntimeError as e:
        # Catch errors from the ML service and return a 500
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
    finally:
        # Always clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
