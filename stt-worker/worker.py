import json
import os
import time
import traceback
import threading

import redis
from logger import setup_logger
from ml_service.model import transcribe_audio_file, transcribe_audio_bytes

logger = setup_logger("stt_worker")

# --- Set up Redis connection ---
try:
    r = redis.Redis(host="redis", port=6379, db=0)
    r.ping()
    logger.info("STT Worker connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    logger.error(f"STT Worker could not connect to Redis: {e}")
    r = None

# Session audio buffers for real-time processing
session_buffers = {}


def process_realtime_audio():
    """
    Listens for real-time audio chunks via Redis pubsub.
    Processes audio chunks and sends transcriptions back.
    """
    if not r:
        logger.error("Cannot start real-time processor - no Redis connection")
        return
    
    pubsub = r.pubsub()
    pubsub.subscribe("realtime_audio")
    logger.info("STT Worker listening for real-time audio...")
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    session_id = data.get("session_id")
                    
                    if data.get("type") == "end_stream":
                        # Process accumulated buffer
                        if session_id in session_buffers and session_buffers[session_id]:
                            audio_bytes = session_buffers[session_id]
                            
                            logger.info(f"Processing end of stream for session {session_id}")
                            
                            # Transcribe accumulated audio
                            transcription = transcribe_audio_bytes(audio_bytes)
                            
                            if transcription:
                                # Send transcription to client
                                r.publish(f"response:{session_id}", json.dumps({
                                    "type": "transcription",
                                    "text": transcription
                                }))
                                
                                # Send to LLM worker
                                llm_payload = {
                                    "session_id": session_id,
                                    "text_input": transcription,
                                }
                                r.publish("realtime_llm", json.dumps(llm_payload))
                                
                                logger.info(f"Transcription sent for session {session_id}: {transcription[:50]}...")
                            
                            # Clear buffer
                            session_buffers[session_id] = b""
                    
                    else:
                        # Accumulate audio chunks
                        audio_chunk_hex = data.get("audio_chunk")
                        if audio_chunk_hex and session_id:
                            audio_chunk = bytes.fromhex(audio_chunk_hex)
                            
                            # Initialize buffer if needed
                            if session_id not in session_buffers:
                                session_buffers[session_id] = b""
                                logger.info(f"Initialized new buffer for session {session_id}")
                            
                            # Append to buffer
                            session_buffers[session_id] += audio_chunk
                            
                            # Log progress (every 10 chunks)
                            chunk_count = len(session_buffers[session_id]) // 8192 # Approximate
                            if chunk_count > 0 and chunk_count % 10 == 0:
                                logger.info(f"Session {session_id}: Buffer size {len(session_buffers[session_id])} bytes (~{len(session_buffers[session_id])/32000:.1f}s)")
                            
                except Exception as e:
                    logger.error(f"Error processing real-time audio: {e}")
                    traceback.print_exc()
    
    except KeyboardInterrupt:
        logger.info("Real-time processor shutting down...")
    finally:
        pubsub.close()


def process_batch_jobs():
    """
    [LEGACY] Listens for batch jobs on the transcription_jobs queue.
    """
    if not r:
        logger.error("Exiting worker due to no Redis connection.")
        return

    logger.info("STT Worker listening for batch jobs...")
    try:
        while True:
            job_data = r.brpop("transcription_jobs", timeout=1)

            if job_data:
                job_payload = json.loads(job_data[1])
                job_id = job_payload.get("job_id")
                file_path = job_payload.get("file_path")

                logger.info(
                    f"ASR worker processing batch job {job_id} for file: {file_path}"
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
                        r.set(f"result:{job_id}", json.dumps(error_payload))

                    logger.error(f"ASR Worker job {job_id} failed with error: {e}")
                finally:
                    if os.path.exists(file_path):
                        os.remove(file_path)

    except KeyboardInterrupt:
        logger.info("Batch processor shutting down...")


if __name__ == "__main__":
    # Run both real-time and batch processors in parallel
    realtime_thread = threading.Thread(target=process_realtime_audio, daemon=True)
    batch_thread = threading.Thread(target=process_batch_jobs, daemon=True)
    
    realtime_thread.start()
    batch_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("STT Worker shutting down...")

