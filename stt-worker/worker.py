import json
import os
import time
import traceback

import redis
from logger import setup_logger
from ml_service.model import transcribe_audio_file

logger = setup_logger("stt_worker")

# --- Set up Redis connection ---
try:
    r = redis.Redis(host="redis", port=6379, db=0)
    r.ping()
    logger.info("Worker connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    logger.error(f"Worker could not connect to Redis: {e}")
    r = None


def process_jobs():
    """
    Listens for new jobs on the transcription_jobs queue and processes them.
    """
    if not r:
        logger.error("Exiting worker due to no Redis connection.")
        return

    logger.info("STT Worker is listening for jobs...")
    try:
        while True:
            job_data = r.brpop("transcription_jobs", timeout=1)

            if job_data:
                job_payload = json.loads(job_data[1])
                job_id = job_payload.get("job_id")
                file_path = job_payload.get("file_path")

                logger.info(
                    f" ASR worker processing job {job_id} for file: {file_path}"
                )

                try:
                    transcribed_text = transcribe_audio_file(file_path)

                    llm_payload = {
                        "job_id": job_id,
                        "text_input": transcribed_text,
                    }

                    r.lpush("llm_jobs", json.dumps(llm_payload))

                    logger.info(
                        f"ASR Worker completed job {job_id}. Pushed to LLM queue."
                    )

                except Exception as e:
                    # Store an error result in case of failure
                    error_payload = {
                        "job_id": job_id,
                        "status": "failed",
                        "error": str(e),
                    }
                    if job_id:
                        # We store the error in Redis so the API can retrieve it
                        r.set(f"result:{job_id}", json.dumps(error_payload))

                    logger.error(f"ASR Worker job {job_id} failed with error: {e}")
                finally:
                    if os.path.exists(file_path):
                        os.remove(file_path)

            # time.sleep(1)
    except KeyboardInterrupt:
        logger.error("Worker shutting down...")


if __name__ == "__main__":
    process_jobs()
