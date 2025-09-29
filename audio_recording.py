import wave
import threading
import subprocess
from pathlib import Path
import tempfile

import pyaudio
from openai import OpenAI

from settings import OPENAI_API_KEY


def record_audio(
    recording_directory: Path | str,
    chunk=1024,
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
) -> Path:
    recording_directory = Path(recording_directory)
    wav_file_path = recording_directory / "output.wav"
    pa = pyaudio.PyAudio()

    stream = pa.open(
        format=format, channels=channels, rate=rate, frames_per_buffer=chunk, input=True
    )
    frames = []

    def record_audio():
        while not stop.is_set():
            data = stream.read(chunk)
            frames.append(data)

    stop = threading.Event()
    t = threading.Thread(target=record_audio)
    t.start()
    input()
    stop.set()
    t.join()

    stream.stop_stream()
    stream.close()
    pa.terminate()

    wf = wave.open(str(wav_file_path), "wb")
    wf.setnchannels(channels)
    wf.setsampwidth(pa.get_sample_size(format=format))
    wf.setframerate(rate)
    wf.writeframes(b"".join(frames))
    wf.close()

    return wav_file_path


def convert_to_mp3(file_path: Path | str) -> Path:
    file_path = Path(file_path)
    output_file_path = file_path.parent / "output.mp3"
    subprocess.run(
        ["ffmpeg", "-i", str(file_path), str(output_file_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return output_file_path


### Transcribe and interactive logic
def get_transcription(file_path) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)
    audio_file = open(file_path, "rb")
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=audio_file
    )
    transcription_text = transcription.text
    return transcription_text


def interactive_transcribe() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        input("Press enter to start recording")
        record_again = True
        while record_again == True:
            wav_file_path = record_audio(recording_directory=tmpdir)
            mp3_file_path = convert_to_mp3(file_path=wav_file_path)

            transcription = get_transcription(file_path=mp3_file_path)
            print("Transcription:")
            print(transcription)

            choice = input("Press enter to approve, r to record again")
            record_again = False if choice == "" else True

    return transcription
