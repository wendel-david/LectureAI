from pathlib import Path
from transformers import pipeline
from SETTINGS import TranscriberMap

class Transcriber:
    def __init__(self):
        self.transcriber = pipeline(
            task="automatic-speech-recognition",
            model=TranscriberMap["model"],
        )

    def transcribe_audio(self, path: Path):
        if not path:
            raise FileNotFoundError("There is no file to use")

        result = self.transcriber(str(path))

        if result['text'] is not None:
            return result['text']
        else:
            raise SystemError("Could not Transcribe the Audio")

        
        