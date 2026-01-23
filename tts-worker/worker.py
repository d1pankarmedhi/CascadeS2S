# tts-worker/worker.py
import json
import os
import time
import uuid
import threading

import redis
import soundfile as sf
import torch
from logger import setup_logger
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer

logger = setup_logger("tts_worker")

# --- Set up Redis connection ---
try:
    r = redis.Redis(host="redis", port=6379, db=0)
    r.ping()
    logger.info("TTS Worker connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    logger.error(f"TTS Worker could not connect to Redis: {e}")
    r = None

# --- ParlerTTS Model Setup ---
# Set device to GPU if available, otherwise use CPU
device = "cuda:0" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")

try:
    # Load the model and tokenizer - using tiny for faster generation
    model = ParlerTTSForConditionalGeneration.from_pretrained(
        "parler-tts/parler-tts-tiny-v1"
    ).to(device)
    tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler-tts-tiny-v1")
    logger.info("ParlerTTS model and tokenizer loaded successfully!")
except Exception as e:
    model = None
    tokenizer = None
    logger.error(f"Error loading ParlerTTS model: {e}")

# Voice description for consistent voice
DEFAULT_VOICE_DESCRIPTION = "A clear, friendly voice with natural pacing, sounding like a helpful assistant."


def synthesize_speech(text: str, output_path: str) -> bool:
    """
    Synthesize speech from text and save to file.
    
    Args:
        text: Text to synthesize
        output_path: Path to save audio file
        
    Returns:
        True if successful, False otherwise
    """
    if not model or not tokenizer:
        logger.error("TTS model not loaded")
        return False
    
    try:
        # Prepare inputs
        input_ids = tokenizer(
            DEFAULT_VOICE_DESCRIPTION, return_tensors="pt"
        ).input_ids.to(device)
        prompt_input_ids = tokenizer(
            text, return_tensors="pt"
        ).input_ids.to(device)

        # Generate audio
        generation = model.generate(
            input_ids=input_ids, prompt_input_ids=prompt_input_ids
        )
        audio_arr = generation.cpu().numpy().squeeze()

        # Save audio file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sf.write(output_path, audio_arr, model.config.sampling_rate)
        
        return True
        
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        return False


def process_realtime_requests():
    """
    Listens for real-time TTS requests via Redis pubsub.
    Synthesizes audio and sends back to client.
    """
    if not r:
        logger.error("Cannot start real-time processor - no Redis connection")
        return
    
    pubsub = r.pubsub()
    pubsub.subscribe("realtime_tts")
    logger.info("TTS Worker listening for real-time requests...")
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    session_id = data.get("session_id")
                    text_to_speech = data.get("text_to_speech")
                    
                    if not session_id or not text_to_speech:
                        continue
                    
                    logger.info(f"Processing real-time TTS for session {session_id} ({len(text_to_speech)} chars)")
                    
                    # Generate unique filename
                    audio_filename = f"output/{session_id}_{uuid.uuid4().hex[:8]}.wav"
                    
                    # Synthesize speech
                    start_time = time.time()
                    success = synthesize_speech(text_to_speech, audio_filename)
                    latency = (time.time() - start_time) * 1000
                    
                    if success:
                        # Send audio path to API via pubsub
                        r.publish(f"response:{session_id}", json.dumps({
                            "type": "audio",
                            "audio_path": audio_filename
                        }))
                        
                        logger.info(f"TTS audio generated for session {session_id} in {latency:.0f}ms")
                    else:
                        logger.error(f"Failed to generate TTS for session {session_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing real-time TTS: {e}")
    
    except KeyboardInterrupt:
        logger.info("Real-time processor shutting down...")
    finally:
        pubsub.close()


def process_batch_jobs():
    """
    [LEGACY] Listens for batch jobs on the tts_jobs queue.
    """
    if not r:
        logger.error("Exiting TTS worker due to no Redis connection.")
        return

    logger.info("TTS Worker listening for batch jobs...")
    while True:
        job_data = r.brpop("tts_jobs", timeout=1)

        if job_data:
            job_payload = json.loads(job_data[1])
            job_id = job_payload.get("job_id")
            text_to_speech = job_payload.get("text_to_speech")

            logger.info(f"TTS Worker processing batch job {job_id}")

            if not model or not tokenizer:
                error_payload = {
                    "job_id": job_id,
                    "status": "failed",
                    "error": "TTS model not loaded.",
                }
                r.set(f"result:{job_id}", json.dumps(error_payload))
                continue

            try:
                audio_filename = f"output/{job_id}_response.wav"
                
                if synthesize_speech(text_to_speech, audio_filename):
                    final_payload = {
                        "job_id": job_id,
                        "status": "completed",
                        "final_audio_path": audio_filename,
                    }
                    r.set(f"result:{job_id}", json.dumps(final_payload))
                    logger.info(f"TTS Worker completed job {job_id}. Final audio saved.")
                else:
                    raise Exception("Speech synthesis failed")

            except Exception as e:
                error_payload = {"job_id": job_id, "status": "failed", "error": str(e)}
                if job_id:
                    r.set(f"result:{job_id}", json.dumps(error_payload))
                logger.error(f"TTS Worker job {job_id} failed with error: {e}")


if __name__ == "__main__":
    # Run both real-time and batch processors in parallel
    realtime_thread = threading.Thread(target=process_realtime_requests, daemon=True)
    batch_thread = threading.Thread(target=process_batch_jobs, daemon=True)
    
    realtime_thread.start()
    batch_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("TTS Worker shutting down...")

