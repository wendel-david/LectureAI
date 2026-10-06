from openai import OpenAI
from dotenv import load_dotenv
from SETTINGS import SettingsMap, InstructionsMap


load_dotenv()

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
