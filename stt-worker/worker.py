import os
import time
import traceback
from concurrent import futures
import grpc
import re

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
from ml_service.model import transcribe_audio_file, transcribe_audio_bytes, calculate_energy

logger = setup_logger("stt_worker")

class STTServiceServicer(voice_pb2_grpc.STTServiceServicer):
    def TranscribeStream(self, request_iterator, context):
        session_id = None
        audio_buffer = b""
        
        SILENCE_THRESHOLD = 0.008
        SILENCE_DURATION_S = 0.5
        SPEECH_THRESHOLD = 0.015

        state = {
            "is_speaking": False,
            "silence_start": None,
            "barge_in_checked": False,
            "speech_start_time": None,
            "heuristic_checked": False,
            "current_transcript": ""
        }

        try:
            for request in request_iterator:
                if session_id is None:
                    session_id = request.session_id
                    logger.info(f"Started new gRPC stream for session {session_id}")
                
                if request.end_stream:
                    if audio_buffer:
                        trigger_time = time.time()
                        transcription = transcribe_audio_bytes(audio_buffer).strip()
                        stt_latency_ms = (time.time() - trigger_time) * 1000
                        if transcription:
                            yield voice_pb2.STTEvent(
                                session_id=session_id,
                                text=transcription,
                                is_final=True,
                                stt_latency_ms=stt_latency_ms
                            )
                    break
                
                if request.data:
                    audio_buffer += request.data
                    energy = calculate_energy(request.data)
                    current_time = time.time()

                    if energy > SPEECH_THRESHOLD:
                        if not state["is_speaking"]:
                            logger.info(f"Session {session_id}: Speech detected (energy: {energy:.4f})")
                            state["speech_start_time"] = current_time
                            state["barge_in_checked"] = False
                            state["heuristic_checked"] = False
                        state["is_speaking"] = True
                        state["silence_start"] = None
                        
                        # Semantic Barge-In check after 0.5s of speech
                        time_speaking = current_time - state["speech_start_time"]
                        if time_speaking >= 0.5 and not state["barge_in_checked"]:
                            state["barge_in_checked"] = True
                            quick_transcript = transcribe_audio_bytes(audio_buffer).strip()
                            cleaned = re.sub(r'[^\w\s]', '', quick_transcript.lower())
                            backchannels = {"yeah", "uhhuh", "right", "mhm", "ok", "okay", "ah", "oh"}
                            if cleaned in backchannels or not cleaned:
                                yield voice_pb2.STTEvent(session_id=session_id, restore_audio=True)
                                logger.info(f"Session {session_id}: Detected backchannel '{quick_transcript}'")
                            else:
                                yield voice_pb2.STTEvent(session_id=session_id, interrupt=True)
                                logger.info(f"Session {session_id}: Detected barge-in '{quick_transcript}'")
                                
                    elif energy < SILENCE_THRESHOLD and state["is_speaking"]:
                        if state["silence_start"] is None:
                            state["silence_start"] = current_time
                            logger.info(f"Session {session_id}: Silence started...")
                        else:
                            silence_duration = current_time - state["silence_start"]
                            
                            if silence_duration >= 0.4 and not state["heuristic_checked"]:
                                state["heuristic_checked"] = True
                                state["current_transcript"] = transcribe_audio_bytes(audio_buffer).strip()
                                
                            transcript = state["current_transcript"]
                            fast_trigger = transcript.endswith(('?', '.', '!'))
                            thinking_trigger = transcript.lower().endswith(('um', 'uh', 'so')) or not fast_trigger
                            
                            should_trigger = False
                            if fast_trigger and silence_duration >= 0.4:
                                should_trigger = True
                            elif thinking_trigger and silence_duration >= 2.0:
                                should_trigger = True
                            elif silence_duration >= 2.5:
                                should_trigger = True
                                
                            if should_trigger:
                                logger.info(f"Session {session_id}: Auto-triggering response (silence: {silence_duration:.1f}s)")
                                
                                trigger_time = time.time()
                                final_transcription = transcript if state["heuristic_checked"] else transcribe_audio_bytes(audio_buffer).strip()
                                stt_latency_ms = (time.time() - trigger_time) * 1000
                                
                                if final_transcription:
                                    yield voice_pb2.STTEvent(
                                        session_id=session_id,
                                        text=final_transcription,
                                        is_final=True,
                                        stt_latency_ms=stt_latency_ms
                                    )
                                
                                audio_buffer = b""
                                state["is_speaking"] = False
                                state["silence_start"] = None
                                state["barge_in_checked"] = False
                                state["heuristic_checked"] = False

        except Exception as e:
            logger.error(f"Error in STT stream: {e}")
            traceback.print_exc()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    voice_pb2_grpc.add_STTServiceServicer_to_server(STTServiceServicer(), server)
    server.add_insecure_port("[::]:50051")
    logger.info("STT Worker gRPC server starting on port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
