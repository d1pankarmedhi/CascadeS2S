import grpc
import sys
import os
import asyncio

current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, "utils")):
    sys.path.append(current_dir)
from utils import voice_pb2, voice_pb2_grpc

async def test_llm():
    channel = grpc.aio.insecure_channel('localhost:50052')
    stub = voice_pb2_grpc.LLMServiceStub(channel)
    
    async def request_generator():
        yield voice_pb2.TextChunk(session_id="test-session", text="Hello, how are you?")
        yield voice_pb2.TextChunk(session_id="test-session", end_stream=True)
        
    print("Sending request to LLM worker...")
    try:
        response_iterator = stub.GenerateStream(request_generator())
        async for response in response_iterator:
            if response.text_chunk:
                print(f"Received chunk: {response.text_chunk}")
            if response.stream_finished:
                print("Stream finished.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
