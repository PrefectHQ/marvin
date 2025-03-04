import os
import sys
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

    frames = [stream.read(chunk) for _ in range(0, int(sample_rate / chunk * seconds))]

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


def talk_to_agent(agent_name: str, instructions: str, speaking_time: int):
    """Run a conversation loop with the AI."""
    print("Starting conversation with AI. Press Ctrl+C to exit.")
    print("When you're ready to speak, press Enter.")

    agent = marvin.Agent(
        name=agent_name,
        model="openai:gpt-4o-audio-preview",
        instructions=instructions,
    )
    with marvin.Thread(str(uuid4())):
        try:
            while True:
                input("\nPress Enter to start recording your message...")
                audio_file = record_audio(seconds=speaking_time)

                result = marvin.run(
                    [
                        BinaryContent(
                            data=Path(audio_file).read_bytes(), media_type="audio/wav"
                        )
                    ],
                    agents=[agent],
                )

                os.system(f"say '{result.replace("'", "'\\''")}'")

                os.unlink(audio_file)

        except KeyboardInterrupt:
            print("\nEnding conversation.")


if __name__ == "__main__":
    # uv run --extra audio examples/talk_to_marvin.py
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "Yoda"
    instructions = (
        sys.argv[2]
        if len(sys.argv) > 2
        else (
            "you're not an AI, you're really yoda from star wars - "
            "you're really old and have a special cadence to your speech"
        )
    )
    speaking_time = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    talk_to_agent(
        agent_name=agent_name, instructions=instructions, speaking_time=speaking_time
    )
