from Core.AIModule import AIEngine
from Core.DatabaseModule import Database
from Core.PipelineModule import transcribe_file
from SETTINGS import SettingsMap, TranscriberMap
from pathlib import Path


def generate_output(db: Database, engine: AIEngine, transcription, instruction: str):
    response = engine.call_llm(transcription["text"], instruction)
    db.add_output(transcription["id"], instruction, response.output_text, SettingsMap["model"])
    return response.output_text


def main():
    audio_path = Path("./audios/mlk2.flac")

    engine = AIEngine()
    transcript = transcribe_file(audio_path)

    with Database() as db:
        lecture_id = db.add_lecture(audio_path.stem, audio_path)
        transcription_id = db.add_transcription(lecture_id, transcript, TranscriberMap["model"])
        generate_output(db, engine, db.get_transcription(transcription_id), "summarize")


def main_testing():
    engine = AIEngine()

    with Database() as db:
        transcription = db.get_latest_transcription()
        if transcription is None:
            print("No transcriptions in the database yet. Run main() first.")
            return

        print(generate_output(db, engine, transcription, "questions"))


if __name__ == "__main__":
    main_testing()
