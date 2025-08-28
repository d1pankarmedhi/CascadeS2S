# tts-worker/worker.py
import json
import os
import time
import uuid

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
    # Load the model and tokenizer from the pre-downloaded cache
    model = ParlerTTSForConditionalGeneration.from_pretrained(
        "parler-tts/parler-tts-tiny-v1"
    ).to(device)
    tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler-tts-tiny-v1")
    logger.info("ParlerTTS model and tokenizer loaded successfully!")
except Exception as e:
    model = None
    tokenizer = None
    logger.error(f"Error loading ParlerTTS model: {e}")

# This is a fixed description for the voice style
DEFAULT_VOICE_DESCRIPTION = "The speaker has a clear, friendly tone with a slightly fast pace, and sounds like a helpful assistant."


def process_jobs():
    """
    Listens for new jobs on the tts_jobs queue, synthesizes audio,
    and stores the final audio file path.
    """
    if not r:
        logger.error("Exiting TTS worker due to no Redis connection.")
        return

    logger.info("TTS Worker is listening for jobs...")
    while True:
        job_data = r.brpop("tts_jobs", timeout=1)

        if job_data:
            job_payload = json.loads(job_data[1])
            job_id = job_payload.get("job_id")
            text_to_speech = job_payload.get("text_to_speech")

            logger.info(f"TTS Worker processing job {job_id}")

            if not model or not tokenizer:
                error_payload = {
                    "job_id": job_id,
                    "status": "failed",
                    "error": "TTS model not loaded.",
                }
                r.set(f"result:{job_id}", json.dumps(error_payload))
                continue

            try:
                # Prepare inputs for the model
                input_ids = tokenizer(
                    DEFAULT_VOICE_DESCRIPTION, return_tensors="pt"
                ).input_ids.to(device)
                prompt_input_ids = tokenizer(
                    text_to_speech, return_tensors="pt"
                ).input_ids.to(device)

                # Generate the audio
                generation = model.generate(
                    input_ids=input_ids, prompt_input_ids=prompt_input_ids
                )
                audio_arr = generation.cpu().numpy().squeeze()

                # Save the audio as a WAV file
                os.makedirs("output", exist_ok=True)
                audio_filename = f"output/{job_id}_response.wav"
                sf.write(audio_filename, audio_arr, model.config.sampling_rate)

                final_payload = {
                    "job_id": job_id,
                    "status": "completed",
                    "final_audio_path": audio_filename,
                }
                r.set(f"result:{job_id}", json.dumps(final_payload))

                logger.info(f"TTS Worker completed job {job_id}. Final audio saved.")

            except Exception as e:
                error_payload = {"job_id": job_id, "status": "failed", "error": str(e)}
                if job_id:
                    r.set(f"result:{job_id}", json.dumps(error_payload))

                logger.error(f"TTS Worker job {job_id} failed with error: {e}")

        # time.sleep(1)


if __name__ == "__main__":
    process_jobs()
