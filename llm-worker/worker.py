import os
import time
import threading
from concurrent import futures
import grpc
from dotenv import load_dotenv
import ollama

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if os.path.exists(os.path.join(parent_dir, "utils")):
    sys.path.append(parent_dir)
else:
    sys.path.append(current_dir)
from utils import voice_pb2, voice_pb2_grpc
from utils.logger import setup_logger

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODEL_NAME = "qwen2.5:0.5b"
logger = setup_logger("llm_worker")

model_ready = False
client = ollama.Client(host=OLLAMA_HOST)

def ensure_model_pulled():
    global model_ready
    while not model_ready:
        try:
            logger.info(f"Checking for model {MODEL_NAME}...")
            models_response = client.list()
            models_list = models_response.get('models', []) if isinstance(models_response, dict) else getattr(models_response, 'models', [])
            
            for m in models_list:
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

class LLMServiceServicer(voice_pb2_grpc.LLMServiceServicer):
    def GenerateStream(self, request_iterator, context):
        session_id = None
        text_input = ""
        
        for request in request_iterator:
            if session_id is None:
                session_id = request.session_id
            if request.text:
                text_input += request.text + " "
            
            if request.end_stream:
                break
                
        if not text_input.strip() or not model_ready:
            yield voice_pb2.LLMEvent(session_id=session_id, stream_finished=True)
            return

        logger.info(f"Generating for session {session_id}: {text_input}")
        start_time = time.time()
        
        try:
            stream = client.chat(
                model=MODEL_NAME,
                messages=[
                    {'role': 'system', 'content': 'You are a helpful voice assistant. Give concise, natural responses as if in a spoken conversation in English. Keep responses brief (1-3 sentences).'},
                    {'role': 'user', 'content': text_input.strip()},
                ],
                stream=True,
            )

            for chunk in stream:
                # context.is_active() checks if client disconnected
                if not context.is_active():
                    break
                content = chunk['message']['content']
                yield voice_pb2.LLMEvent(
                    session_id=session_id,
                    text_chunk=content,
                    llm_latency_ms=(time.time() - start_time) * 1000
                )
                
            yield voice_pb2.LLMEvent(session_id=session_id, stream_finished=True)
            logger.info(f"Generation complete for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error in LLM stream: {e}")

def serve():
    threading.Thread(target=ensure_model_pulled, daemon=True).start()
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    voice_pb2_grpc.add_LLMServiceServicer_to_server(LLMServiceServicer(), server)
    server.add_insecure_port("[::]:50052")
    logger.info("LLM Worker gRPC server starting on port 50052...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
