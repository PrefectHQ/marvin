import os
import tempfile
import wave
from pathlib import Path
from uuid import uuid4

import pyaudio
from pydantic_ai import BinaryContent

import marvin


def record_audio(seconds=5, sample_rate=16000):
    """Record audio from the microphone for the specified number of seconds."""
    chunk = 1024
    audio_format = pyaudio.paInt16
    channels = 1

    p = pyaudio.PyAudio()

    print(f"Recording for {seconds} seconds...")

    stream = p.open(
        format=audio_format,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk,
    )

    frames = []

    for i in range(0, int(sample_rate / chunk * seconds)):
        data = stream.read(chunk)
        frames.append(data)

    print("Recording finished.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wf = wave.open(temp_file.name, "wb")
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(audio_format))
    wf.setframerate(sample_rate)
    wf.writeframes(b"".join(frames))
    wf.close()

    return temp_file.name


def talk_to_ai():
    """Run a conversation loop with the AI."""
    print("Starting conversation with AI. Press Ctrl+C to exit.")
    print("When you're ready to speak, press Enter.")

    agent = marvin.Agent(
        model="openai:gpt-4o-audio-preview",
        instructions="talk like a pirate",
    )
    with marvin.Thread(str(uuid4())):
        try:
            while True:
                input("\nPress Enter to start recording your message...")
                audio_file = record_audio(seconds=3)

                audio = BinaryContent(
                    data=Path(audio_file).read_bytes(), media_type="audio/wav"
                )

                result = marvin.run(
                    ["what do you say to this?", audio],
                    agents=[agent],
                )

                escaped_result = result.replace("'", "'\\''")
                os.system(f"say '{escaped_result}'")

                os.unlink(audio_file)

        except KeyboardInterrupt:
            print("\nEnding conversation.")


if __name__ == "__main__":
    talk_to_ai()
