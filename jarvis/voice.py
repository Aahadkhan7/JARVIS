import time
from pathlib import Path

import sounddevice as sd
import soundfile as sf
from groq import Groq

from .config import GROQ_API_KEY


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

VOICE_INPUT_PATH = DATA_DIR / "voice_input.wav"
VOICE_OUTPUT_PATH = DATA_DIR / "jarvis_response.wav"


# ============================================================
# AUDIO SETTINGS
# ============================================================

SAMPLE_RATE = 16000
CHANNELS = 1

# Voice recording duration
RECORD_SECONDS = 5


# ============================================================
# LISTEN
# ============================================================

def listen():

    try:

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        print()
        print("JARVIS is listening...")
        print("Speak now...")

        recording = sd.rec(
            int(
                RECORD_SECONDS
                * SAMPLE_RATE
            ),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32"
        )

        sd.wait()

        sf.write(
            VOICE_INPUT_PATH,
            recording,
            SAMPLE_RATE
        )

        print("Processing your voice...")

        with open(
            VOICE_INPUT_PATH,
            "rb"
        ) as audio_file:

            transcription = (
                client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    response_format="json",
                    temperature=0
                )
            )

        text = (
            getattr(
                transcription,
                "text",
                ""
            )
            or ""
        ).strip()

        if not text:

            print(
                "JARVIS: I could not hear you."
            )

            return None

        print(
            f"You: {text}"
        )

        return text

    except Exception as error:

        print(
            "Voice input error: "
            f"{error}"
        )

        return None


# ============================================================
# SPEAK
# ============================================================

def speak(text):

    if not text:
        return

    try:

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        text = str(text).strip()

        if not text:
            return

        # Orpheus currently accepts a maximum
        # of 200 characters per request.
        chunks = []

        while len(text) > 200:

            split_at = text.rfind(
                " ",
                0,
                200
            )

            if split_at <= 0:

                split_at = 200

            chunks.append(
                text[:split_at].strip()
            )

            text = text[
                split_at:
            ].strip()

        if text:

            chunks.append(text)

        for chunk in chunks:

            response = (
                client.audio.speech.create(
                    model="canopylabs/orpheus-v1-english",
                    voice="troy",
                    input=chunk,
                    response_format="wav"
                )
            )

            response.write_to_file(
                str(VOICE_OUTPUT_PATH)
            )

            data, sample_rate = sf.read(
                str(VOICE_OUTPUT_PATH)
            )

            sd.play(
                data,
                sample_rate
            )

            sd.wait()

            time.sleep(0.1)

    except Exception as error:

        error_text = str(error)

        if "429" in error_text:

            print(
                "TTS temporarily unavailable. "
                "Continuing in text mode."
            )

            return

        print(
            "TTS error: "
            f"{error}"
        )

        return