from Modules.TranscriberModule import Transcriber
from Modules.Utils import Utils
from Modules.AIModule import AIEngine
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import os

_worker_transcriber = None


def _init_worker():
    global _worker_transcriber
    _worker_transcriber = Transcriber()


def _transcribe_in_worker(path):
    return _worker_transcriber.transcribe_audio(path)


def main():
    audio_path = Path("./audios/mlk2.flac")

    tools = Utils()
    engine = AIEngine()

    chunks = tools.split_audio(tools.convert_to_flac(audio_path))

    max_workers = min(len(chunks), os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=max_workers, initializer=_init_worker) as executor:
        results = list(executor.map(_transcribe_in_worker, chunks))

    transcript = " ".join(results)

    with open("transcribe.txt", "w") as f:
        f.write(transcript)

    engine.call_llm(transcript, "summarize")


def main_testing():
    engine = AIEngine()

    with open("transcribe.txt", "r") as f:
        transcript = f.read()

    response = engine.call_llm(transcript, "questions")
    print(response.output_text)


if __name__ == "__main__":
    main_testing()