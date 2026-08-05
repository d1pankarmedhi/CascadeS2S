import grpc
import sys
import os
import asyncio

current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, "utils")):
    sys.path.append(current_dir)
from utils import voice_pb2, voice_pb2_grpc

async def test_tts():
    channel = grpc.aio.insecure_channel('localhost:50053')
    stub = voice_pb2_grpc.TTSServiceStub(channel)
    
    async def request_generator():
        yield voice_pb2.TextChunk(session_id="test-session", text="Hello world")
        yield voice_pb2.TextChunk(session_id="test-session", end_stream=True)
        
    print("Sending request to TTS worker...")
    try:
        response_iterator = stub.SynthesizeStream(request_generator())
        async for response in response_iterator:
            if response.data:
                print(f"Received audio chunk: {len(response.data)} bytes")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())

