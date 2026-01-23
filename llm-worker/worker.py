# llm-worker/worker.py
import json
import os
import time
import threading

import redis
from dotenv import load_dotenv
import ollama
from logger import setup_logger

load_dotenv()

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODEL_NAME = "qwen2.5:3b"
logger = setup_logger("llm_worker")

# State
model_ready = False

# Setup Redis connection
try:
    r = redis.Redis(host="redis", port=6379, db=0)
    r.ping()
    logger.info("LLM Worker connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    logger.error(f"LLM Worker could not connect to Redis: {e}")
    r = None

# Initialize Ollama client
client = ollama.Client(host=OLLAMA_HOST)

def ensure_model_pulled():
    """Ensure the required model is available in Ollama (Background thread)."""
    global model_ready
    while not model_ready:
        try:
            logger.info(f"Checking for model {MODEL_NAME}...")
            # Check if model exists first
            models_response = client.list()
            models_list = models_response.get('models', []) if isinstance(models_response, dict) else getattr(models_response, 'models', [])
            
            for m in models_list:
                # Handle both dict and object formats from different ollama library versions
                name = m.get('name', '') if isinstance(m, dict) else getattr(m, 'model', getattr(m, 'name', ''))
                if name == MODEL_NAME or name.startswith(MODEL_NAME + ":"):
                    logger.info(f"Model {MODEL_NAME} is already available.")
                    model_ready = True
                    return

            logger.info(f"Model {MODEL_NAME} not found. Starting pull...")
            client.pull(MODEL_NAME)
            logger.info(f"Model {MODEL_NAME} successfully pulled.")
            model_ready = True
        except Exception as e:
            logger.error(f"Failed to check/pull model {MODEL_NAME}: {e}. Retrying in 30s...")
            time.sleep(30)

def generate_response(text_input: str) -> str:
    """
    Generates a response using local Ollama (Qwen 2.5).
    Optimized for conversational, real-time responses.
    """
    if not model_ready:
        logger.warning(f"Model {MODEL_NAME} is not ready yet.")
        return "Please wait a moment, I am still preparing my thoughts (local model is loading)."

    try:
        # We use a system prompt to keep responses concise for voice output
        response = client.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': 'You are a helpful voice assistant. Give concise, natural responses as if in a spoken conversation. Keep responses brief (1-3 sentences).'},
            {'role': 'user', 'content': text_input},
        ])
        return response['message']['content']
    except Exception as e:
        logger.error(f"Ollama API call failed: {e}")
        return "I'm sorry, I'm having trouble thinking right now."


def process_realtime_requests():
    """
    Listens for real-time LLM requests via Redis pubsub.
    Processes text and sends responses back.
    """
    if not r:
        logger.error("Cannot start real-time processor - no Redis connection")
        return
    
    pubsub = r.pubsub()
    pubsub.subscribe("realtime_llm")
    logger.info("LLM Worker listening for real-time requests...")
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    session_id = data.get("session_id")
                    text_input = data.get("text_input")
                    
                    if not session_id or not text_input:
                        continue
                    
                    logger.info(f"Processing real-time request for session {session_id} ({len(text_input)} chars)")
                    
                    # Generate LLM response
                    start_time = time.time()
                    llm_response = generate_response(text_input)
                    latency = (time.time() - start_time) * 1000
                    
                    # Send response to client
                    r.publish(f"response:{session_id}", json.dumps({
                        "type": "llm_response",
                        "text": llm_response
                    }))
                    
                    # Send to TTS worker (only if model was ready, otherwise it's just a status text)
                    if model_ready:
                        tts_payload = {
                            "session_id": session_id,
                            "text_to_speech": llm_response
                        }
                        r.publish("realtime_tts", json.dumps(tts_payload))
                    
                    logger.info(f"LLM response sent for session {session_id}: {llm_response[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error processing real-time LLM request: {e}")
    
    except KeyboardInterrupt:
        logger.info("Real-time processor shutting down...")
    finally:
        pubsub.close()


def process_batch_jobs():
    """
    [LEGACY] Listens for batch jobs on the llm_jobs queue.
    """
    if not r:
        logger.error("Exiting LLM worker due to no Redis connection.")
        return

    logger.info("LLM Worker listening for batch jobs...")
    try:
        while True:
            job_data = r.brpop("llm_jobs", timeout=1)

            if job_data:
                job_payload = json.loads(job_data[1])
                job_id = job_payload.get("job_id")
                text_input = job_payload.get("text_input")

                logger.info(f"LLM Worker processing batch job {job_id}")

                try:
                    llm_response = generate_response(text_input)

                    if model_ready:
                        # Push the result to the new 'tts_jobs' queue for the next stage
                        tts_payload = {"job_id": job_id, "text_to_speech": llm_response}
                        r.lpush("tts_jobs", json.dumps(tts_payload))
                        logger.info(f"LLM Worker completed job {job_id}. Pushed to TTS queue.")
                    else:
                        # If model not ready, store the error/status in result
                        r.set(f"result:{job_id}", json.dumps({
                            "job_id": job_id,
                            "status": "failed",
                            "error": "Local model still loading"
                        }))

                except Exception as e:
                    error_payload = {
                        "job_id": job_id,
                        "status": "failed",
                        "error": str(e),
                    }
                    if job_id:
                        r.set(f"result:{job_id}", json.dumps(error_payload))

                    logger.error(f"LLM Worker job {job_id} failed with error: {e}")

    except KeyboardInterrupt:
        logger.info("Batch processor shutting down...")


if __name__ == "__main__":
    # Start model pull in background
    pull_thread = threading.Thread(target=ensure_model_pulled, daemon=True)
    pull_thread.start()
    
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
        logger.info("LLM Worker shutting down...")
