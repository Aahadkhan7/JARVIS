import os
from pathlib import Path

import sounddevice as sd
import soundfile as sf
from groq import Groq


AUDIO_FILE = (
    Path(__file__).parent.parent
    / "data"
    / "voice_input.wav"
)

TTS_FILE = (
    Path(__file__).parent.parent
    / "data"
    / "jarvis_response.wav"
)

SAMPLE_RATE = 16000
RECORD_SECONDS = 5


def record_audio():
    print("\n🎤 Listening...")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
    )

    sd.wait()

    sf.write(
        AUDIO_FILE,
        audio,
        SAMPLE_RATE
    )

    print("Recording complete.")


def transcribe_audio():
    client = Groq(
        api_key=os.getenv("GROQ_API_KEY")
    )

    with open(
        AUDIO_FILE,
        "rb"
    ) as audio_file:

        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            response_format="text",
        )

    return transcription.strip()


def speak(text):
    client = Groq(
        api_key=os.getenv("GROQ_API_KEY")
    )

    response = client.audio.speech.create(
        model="canopylabs/orpheus-v1-english",
        voice="troy",
        input=text,
        response_format="wav",
    )

    response.write_to_file(TTS_FILE)

    audio, sample_rate = sf.read(TTS_FILE)

    sd.play(
        audio,
        sample_rate
    )

    sd.wait()


def listen():
    record_audio()

    text = transcribe_audio()

    return text