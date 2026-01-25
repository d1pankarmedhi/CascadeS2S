import os
import soundfile as sf
from voxcpm import VoxCPM

def test_voxcpm():
    print("Loading VoxCPM 1.5 model...")
    try:
        model = VoxCPM("openbmb/VoxCPM1.5")
        print("Model loaded successfully!")
        
        text = "Hello, this is a test of the VoxCPM text to speech system."
        print(f"Synthesizing: '{text}'")
        
        wav = model.generate(text=text)
        
        output_path = "test_output.wav"
        sf.write(output_path, wav, model.tts_model.sample_rate)
        
        if os.path.exists(output_path):
            print(f"Success! Audio saved to {output_path}")
            print(f"File size: {os.path.getsize(output_path)} bytes")
        else:
            print("Failed to save audio file.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_voxcpm()
