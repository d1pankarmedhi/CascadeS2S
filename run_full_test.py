import subprocess
import time
import os

print("Starting API server...")
api_process = subprocess.Popen(
    ["uv", "run", "uvicorn", "api.main:app", "--port", "8005"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    env=dict(os.environ, PORT="8005")
)

time.sleep(3) # Wait for server to start

print("Starting test client against port 8005...")
with open("test_client.py", "r") as f:
    content = f.read().replace("8000", "8005")
with open("test_client_8005.py", "w") as f:
    f.write(content)

client_process = subprocess.Popen(
    ["uv", "run", "python", "test_client_8005.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

client_out, _ = client_process.communicate()
print("\n--- CLIENT OUTPUT ---")
print(client_out)

print("\nKilling API server...")
api_process.terminate()
api_out, _ = api_process.communicate()
print("\n--- API OUTPUT ---")
print(api_out)
