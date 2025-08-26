# app/ml_service/model_service.py
import whisper

# Load the model once when this module is imported
# This ensures the model is loaded in memory for all subsequent requests
try:
    _model = whisper.load_model("base")
    print("Whisper model loaded successfully.")
except Exception as e:
    _model = None
    print(f"Error loading Whisper model: {e}")


def transcribe_audio_file(file_path: str) -> str:
    """
    Performs transcription on a given audio file path using the Whisper model.
    """
    if not _model:
        raise RuntimeError("ML model is not loaded.")

    try:
        # The core transcription logic
        result = _model.transcribe(file_path)
        return result["text"]
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")
