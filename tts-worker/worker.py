import os
import time
from concurrent import futures
import grpc
import torch
import numpy as np

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

logger = setup_logger("tts_worker")

device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")

try:
    from pocket_tts import TTSModel
    model = TTSModel.load_model()
    voice_state = model.get_state_for_audio_prompt("alba")
    logger.info("Pocket TTS model and voice state loaded successfully!")
except Exception as e:
    model = None
    voice_state = None
    logger.error(f"Error loading Pocket TTS model: {e}")

def synthesize_speech_bytes(text: str) -> bytes:
    if not model or not voice_state:
        return b""
    try:
        audio = model.generate_audio(voice_state, text)
        import io
        import soundfile as sf
        buffer = io.BytesIO()
        sf.write(buffer, audio.numpy(), model.sample_rate, format='WAV')
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        return b""

class TTSServiceServicer(voice_pb2_grpc.TTSServiceServicer):
    def SynthesizeStream(self, request_iterator, context):
        session_id = None
        
        for request in request_iterator:
            if session_id is None:
                session_id = request.session_id
                
            if request.end_stream or not context.is_active():
                break
                
            if request.text:
                start_time = time.time()
                audio_bytes = synthesize_speech_bytes(request.text)
                if audio_bytes:
                    yield voice_pb2.AudioChunk(
                        session_id=session_id,
                        data=audio_bytes
                    )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    voice_pb2_grpc.add_TTSServiceServicer_to_server(TTSServiceServicer(), server)
    server.add_insecure_port("[::]:50053")
    logger.info("TTS Worker gRPC server starting on port 50053...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
