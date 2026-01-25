import os
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

def test_qwen3():
    print("Loading Qwen3-TTS 1.7B-CustomVoice model...")
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    try:
        model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            device_map=device,
            dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        )
        print("Model loaded successfully!")
        
        text = "Hello, this is a test of the Qwen3 TTS CustomVoice system using Vivian speaker."
        print(f"Synthesizing: '{text}'")
        
        wavs, sr = model.generate_custom_voice(
            text=text,
            language="English",
            speaker="Vivian",
            instruct="",
        )
        
        output_path = "test_qwen3_output.wav"
        sf.write(output_path, wavs[0], sr)
        
        if os.path.exists(output_path):
            print(f"Success! Audio saved to {output_path}")
            print(f"File size: {os.path.getsize(output_path)} bytes")
        else:
            print("Failed to save audio file.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_qwen3()
