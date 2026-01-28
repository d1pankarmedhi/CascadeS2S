import io
import tempfile
from faster_whisper import WhisperModel
from logger import setup_logger

logger = setup_logger("stt_model")

# Initialize faster-whisper model (using tiny for speed, can be changed to base/small)
# Model sizes: tiny, base, small, medium, large-v2, large-v3
# tiny: ~75MB, very fast, good accuracy for real-time
# base: ~142MB, faster, better accuracy
model = None

try:
    # Use CPU with 4 threads for faster inference
    # For GPU: device="cuda", compute_type="float16"
    model = WhisperModel("tiny", device="cpu", compute_type="int8", num_workers=4)
    logger.info("Faster-Whisper model loaded successfully (tiny model)")
except Exception as e:
    logger.error(f"Error loading Faster-Whisper model: {e}")


def transcribe_audio_file(file_path: str) -> str:
    """
    Transcribe audio from a file path.
    Used for batch processing (legacy endpoint).
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Transcribed text
    """
    if not model:
        raise RuntimeError("Model not loaded")
    
    try:
        logger.info(f"Transcribing audio file: {file_path}")
        
        # Transcribe with faster-whisper
        segments, info = model.transcribe(
            file_path,
            beam_size=1,  # Faster decoding
            vad_filter=True,  # Voice activity detection
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        
        # Combine all segments into single text
        transcription = " ".join([segment.text for segment in segments])
        
        logger.info(f"Transcription completed: {transcription[:100]}...")
        return transcription.strip()
        
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise


import numpy as np
from pydub import AudioSegment

def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """
    Transcribe raw Int16 PCM audio bytes.
    Bypasses FFmpeg/pydub for maximum robustness and low latency.
    
    Args:
        audio_bytes: Raw PCM audio data (Int16, 16kHz, Mono)
        
    Returns:
        Transcribed text
    """
    if not model:
        raise RuntimeError("Model not loaded")
    
    if not audio_bytes:
        return ""
    
    try:
        logger.info(f"Processing {len(audio_bytes)} bytes of raw PCM data")
        
        # Convert raw bytes to numpy array (Int16)
        # We handle potential trailing bytes that don't make a full Int16
        num_samples = len(audio_bytes) // 2
        samples_int16 = np.frombuffer(audio_bytes[:num_samples*2], dtype=np.int16)
        
        # Convert to Float32 [-1, 1]
        samples = samples_int16.astype(np.float32) / 32768.0
        
        # Log amplitude for debugging
        if len(samples) > 0:
            max_amp = np.abs(samples).max()
            logger.info(f"Audio decoded: {len(samples)/16000:.2f}s, Max amplitude: {max_amp}")
            
            # Simple normalization if it's too quiet
            if 0 < max_amp < 0.1:
                samples = samples / max_amp * 0.5
                logger.info("Applied auto-normalization to quiet audio")
        else:
            logger.warning("No audio samples decoded")
            return ""
        
        # Transcribe the numpy array directly
        segments, info = model.transcribe(
            samples,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        
        # Combine segments
        transcription = " ".join([segment.text for segment in segments])
        logger.info(f"Transcription completed: {transcription}")
        return transcription.strip()
        
    except Exception as e:
        logger.error(f"Error during raw PCM transcription: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ""

def calculate_energy(audio_bytes: bytes) -> float:
    """
    Calculate the RMS energy of raw Int16 PCM audio bytes.
    Used for simple silence detection.
    
    Args:
        audio_bytes: Raw PCM audio data (Int16, 16kHz, Mono)
        
    Returns:
        RMS energy value (0.0 to 1.0)
    """
    if not audio_bytes:
        return 0.0
    
    try:
        # Convert raw bytes to numpy array (Int16)
        num_samples = len(audio_bytes) // 2
        samples_int16 = np.frombuffer(audio_bytes[:num_samples*2], dtype=np.int16)
        
        if len(samples_int16) == 0:
            return 0.0
            
        # Convert to Float32 [-1, 1]
        samples = samples_int16.astype(np.float32) / 32768.0
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(samples**2))
        return float(rms)
        
    except Exception as e:
        logger.error(f"Error calculating energy: {e}")
        return 0.0
