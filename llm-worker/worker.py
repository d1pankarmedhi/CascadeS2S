# llm-worker/worker.py
import json
import os
import time

import redis
from dotenv import load_dotenv
from google import genai
from logger import setup_logger

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
logger = setup_logger("llm_worker")

# Setup LLM Client
client = genai.Client(api_key=API_KEY)

# Setup Redis connection
try:
    r = redis.Redis(host="redis", port=6379, db=0)
    r.ping()
    logger.info("LLM Worker connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    logger.error(f"LLM Worker could not connect to Redis: {e}")
    r = None


# Provision for adding custom models
def generate_response(text_input: str) -> str:
    """
    Generates a response using the configured LLM.
    This function can be easily swapped to use a local model later.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Give a very short answer to the input text:\nInput Text:"
            + text_input,
        )
        return response.text
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        return "Sorry, I couldn't generate a response."


def process_jobs():
    """
    Listens for new jobs on the llm_jobs queue, generates a response,
    and pushes the response to the next stage.
    """
    if not r:
        logger.error("Exiting LLM worker due to no Redis connection.")
        return

    logger.info("LLM Worker is listening for jobs...")
    try:
        while True:
            job_data = r.brpop("llm_jobs", timeout=1)

            if job_data:
                job_payload = json.loads(job_data[1])
                job_id = job_payload.get("job_id")
                text_input = job_payload.get("text_input")

                logger.info(f"LLM Worker processing job {job_id}")

                try:
                    llm_response = generate_response(text_input)

                    # Push the result to the new 'tts_jobs' queue for the next stage
                    tts_payload = {"job_id": job_id, "text_to_speech": llm_response}
                    r.lpush("tts_jobs", json.dumps(tts_payload))

                    logger.info(
                        f"LLM Worker completed job {job_id}. Pushed to TTS queue."
                    )

                except Exception as e:
                    error_payload = {
                        "job_id": job_id,
                        "status": "failed",
                        "error": str(e),
                    }
                    if job_id:
                        r.set(f"result:{job_id}", json.dumps(error_payload))

                    logger.error(f"LLM Worker job {job_id} failed with error: {e}")

            # time.sleep(1)
    except KeyboardInterrupt:
        logger.info("LLM Worker shutting down...")


if __name__ == "__main__":
    process_jobs()
