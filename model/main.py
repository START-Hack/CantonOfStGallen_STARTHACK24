import sounddevice as sd
from scipy.io.wavfile import write
import websockets
import asyncio
import requests
import base64
import json
from tempfile import NamedTemporaryFile
import azure.cognitiveservices.speech as speechsdk
import os
import wave
import pywav
import time
import modelbit
from openai import OpenAI
from pydub import AudioSegment
from model_openai import LanguageModelYosef



# Configuration
DURATION = 5  # seconds
SAMPLING_RATE = 8000 # Hz
WHISPER_API_ENDPOINT = os.getenv('WHISPER_API_ENDPOINT')
WHISPER_API_KEY = os.getenv('WHISPER_API_KEY')
MISTRAL_API_ENDPOINT = os.getenv('MISTRAL_API_ENDPOINT')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SPEECH_KEY = os.getenv('SPEECH_KEY')
SERVICE_REGION = os.getenv('SERVICE_REGION')
SILENCE_THRESHOLD_SECONDS = 2  # Amount of time to wait for new data before assuming silence

def record_audio(duration, sampling_rate):
    print("Recording...")
    audio_data = sd.rec(int(duration * sampling_rate), samplerate=sampling_rate, channels=1, dtype='int16')
    sd.wait()
    print("Recording stopped.")
    return audio_data

def save_audio_wav(decoded_audio, sampling_rate, num_channels=1, sample_width=2):
    # Create a new temporary file for the WAV data
    filename = 'recorded.wav'
    # with wave.open('recorded.wav','wb') as wav_file:
    #     wav_file.setnchannels(num_channels)  # Mono
    #     wav_file.setsampwidth(sample_width)  # Sample width in bytes, 2 for 16-bit audio
    #     wav_file.setframerate(sampling_rate)
    #     wav_file.writeframes(decoded_audio)
    wave_write = pywav.WavWrite(filename, channels=num_channels, samplerate=sampling_rate, bitspersample=sample_width, audioformat=7)
    
    wave_write.write(decoded_audio)
        
    return filename



def save_audio_pcmu(decoded_audio, sample_rate, num_channels, file_path='recorded.pcmu'):
    # Assuming `decoded_audio` is a byte string of raw PCM data.
    # Create an AudioSegment from the raw PCM audio data
    audio = AudioSegment(
        data=decoded_audio,
        sample_width=2,  # Bytes per sample. Ensure this matches your input data.
        frame_rate=sample_rate,
        channels=num_channels
    )

    # Export the audio in the desired codec/format
    audio.export(file_path, format="ulaw")

    print(f"Audio saved to {file_path} in PCMU format.")
    return file_path


def transcribe_audio(audio_path):
    client = OpenAI()
    audio = open(audio_path, 'rb')
        
    transcript = client.audio.transcriptions.create(
        file=audio,
        model='whisper-1',
        response_format='text',
    )
    
    return transcript

def generate_response(transcription_text):
    model = LanguageModelYosef(api_key=OPENAI_API_KEY)
    return model.get_response(transcription_text, 5)

def synthesize_speech(text):
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SERVICE_REGION)
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    speech_config.speech_synthesis_voice_name = 'de-CH-LeniNeural'
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    result = speech_synthesizer.speak_text_async(text).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesis failed with reason: {result.reason}")
        
async def process_audio_stream(base64_audio):
    # Assuming `save_audio`, `transcribe_audio`, and `generate_response` are defined elsewhere
    # Save the audio payload to a file
    # file_path = save_audio(audio_payload, SAMPLING_RATE)
    b64_audio_string = process_base64_audio_data(base64_audio)
    audio_path = save_audio_wav(b64_audio_string, SAMPLING_RATE)
    # audio_path = save_audio_pcmu(b64_audio_string, SAMPLING_RATE, 1)
    transcription_response = transcribe_audio(audio_path)
    print(f"Transcription: {transcription_response}")
    # Generate a response based on the transcription
    openai_response = generate_response(transcription_response)
    print(f"Response: {openai_response}")
    synthesize_speech(openai_response)  # Synthesize speech from the response text
        
        
def process_base64_audio_data(msg_list):
    print(f"Processing {len(msg_list)} audio chunks...")
    message_parsed = [json.loads(msg) for msg in msg_list]
    messages_sorted = sorted(message_parsed, key=lambda x: int(x['chunk']))
    
    try:
        combined_chunks = b''.join(base64.b64decode(msg['payload']) for msg in messages_sorted)
    except Exception as e:
        print(f"Error processing base64 audio: {e}")
        return None
    return combined_chunks

def test_default():
    audio_data = record_audio(DURATION, SAMPLING_RATE)
    audio_path = save_audio_wav(audio_data, SAMPLING_RATE)
    transcribe_response = transcribe_audio(audio_path)
    print(f"Transcription: {transcribe_response}")
    response_text = generate_response(transcribe_response)
    print(f"Response: {response_text}")
    synthesize_speech(response_text)
    


async def audio_stream_handler(websocket):
    msg_list = []
    last_audio_time = time.time()
    
    try:
        async for message in websocket:
            print(f"Message received: {message}")
            current_time = time.time()

            if message != 'end_of_speech':
                msg_list.append(message)

            if message == 'end_of_speech' or (message == '' and current_time - last_audio_time >= SILENCE_THRESHOLD_SECONDS):
                # Either end of speech detected or silence threshold reached
                if msg_list:
                    await process_audio_stream(msg_list)
                    msg_list.clear()  # Clear the buffer after processing
                last_audio_time = current_time
    except websockets.ConnectionClosed:
        print("Connection closed unexpectedly.")
        # Process any remaining audio data before closing
        if msg_list:
            await process_audio_stream(msg_list)
            print("base64", msg_list)
    except Exception as e:
        print(f"Error processing message: {e}")
        # Handle other exceptions if necessary

    print("Handler finished.")

        
                    
async def start_websocket_server():
    port = 8080  # This should match the port you've exposed with ngrok
    server = await websockets.serve(audio_stream_handler, "0.0.0.0", port)
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_websocket_server())
    # test_default()
