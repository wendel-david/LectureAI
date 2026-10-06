import json

from openai import OpenAI
from dotenv import load_dotenv
from SETTINGS import SettingsMap, InstructionsMap, QuizMap


load_dotenv()

QUIZ_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "correct_index": {"type": "integer"},
                    "explanation": {"type": "string"},
                },
                "required": ["question", "options", "correct_index", "explanation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "questions"],
    "additionalProperties": False,
}

class AIEngine():
    def __init__(self):
        self.client = OpenAI()

    def call_llm(self, transcript: str, instruction: str = "summarize"):
        instruction_text = InstructionsMap.get(instruction, instruction)

        response = self.client.responses.create(
            model=SettingsMap["model"],
            input=f"{instruction_text}\n\n{transcript}"
        )
        return response

    def generate_quiz(self, transcript: str, focus: str = None) -> dict:
        """Ask for a quiz as structured JSON: a short title plus question, options, correct_index, explanation."""
        instruction_text = InstructionsMap[QuizMap["instruction"]]
        prompt = f"{instruction_text}\n\nLecture transcript:\n{transcript}"
        if focus:
            prompt += f"\n\n{QuizMap['focused_quiz']}\n\n{focus}"

        response = self.client.responses.create(
            model=SettingsMap["model"],
            input=prompt,
            text={"format": {"type": "json_schema", "name": "quiz", "schema": QUIZ_SCHEMA, "strict": True}},
        )

        quiz = json.loads(response.output_text)
        questions = [
            q for q in quiz["questions"]
            if len(q["options"]) >= 2 and 0 <= q["correct_index"] < len(q["options"])
        ]
        if not questions:
            raise ValueError("The AI returned a quiz with no valid questions")
        return {"title": quiz["title"], "questions": questions}

    def generate_review(self, transcript: str, missed: str) -> str:
        response = self.client.responses.create(
            model=SettingsMap["model"],
            input=f"{QuizMap['review']}\n\nLecture transcript:\n{transcript}\n\nQuestions the student got wrong:\n{missed}",
        )
        return response.output_text
