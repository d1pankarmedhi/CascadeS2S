import json
import os
import time

import redis
from ml_service.model import transcribe_audio_file

# --- Set up Redis connection ---
try:
    r = redis.Redis(host="redis", port=6379, db=0)
    r.ping()
    print("Worker connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    print(f"Worker could not connect to Redis: {e}")
    r = None


def process_jobs():
    """
    Listens for new jobs on the transcription_jobs queue and processes them.
    """
    if not r:
        print("Exiting worker due to no Redis connection.")
        return

    print("Worker is listening for jobs...")
    while True:
        job_data = r.brpop("transcription_jobs", timeout=1)

        if job_data:
            job_payload = json.loads(job_data[1])
            job_id = job_payload.get("job_id")
            file_path = job_payload.get("file_path")

            print(f"Processing job {job_id} for file: {file_path}")

            try:
                transcribed_text = transcribe_audio_file(file_path)

                result_payload = {
                    "job_id": job_id,
                    "status": "completed",
                    "transcribed_text": transcribed_text,
                }
                r.set(f"result:{job_id}", json.dumps(result_payload))

                print(f"Job {job_id} completed. Result stored in Redis.")

            except Exception as e:
                error_payload = {"job_id": job_id, "status": "failed", "error": str(e)}
                if job_id:
                    r.set(f"result:{job_id}", json.dumps(error_payload))

                print(f"Job {job_id} failed with error: {e}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        time.sleep(1)


if __name__ == "__main__":
    process_jobs()
