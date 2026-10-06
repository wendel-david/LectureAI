from Core.TranscriberModule import Transcriber
from Core.Utils import Utils
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import os
import tempfile

_worker_transcriber = None


def _init_worker():
    global _worker_transcriber
    _worker_transcriber = Transcriber()


def _transcribe_in_worker(path):
    return _worker_transcriber.transcribe_audio(path)


def transcribe_file(audio_path: Path) -> str:
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    tools = Utils()

    with tempfile.TemporaryDirectory() as tmp:
        chunks = tools.split_audio(audio_path, output_dir=Path(tmp))
        if not chunks:
            raise ValueError(f"No audio could be extracted from {audio_path.name}")

        max_workers = min(len(chunks), os.cpu_count() or 1)
        with ProcessPoolExecutor(max_workers=max_workers, initializer=_init_worker) as executor:
            results = list(executor.map(_transcribe_in_worker, chunks))

    return " ".join(r.strip() for r in results)
