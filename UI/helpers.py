import re
from datetime import datetime, timedelta, timezone


def _local(created_at: str) -> datetime:
    """SQLite stores CURRENT_TIMESTAMP in UTC; convert to local time."""
    return datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc).astimezone()


def format_date(created_at: str) -> str:
    return _local(created_at).strftime("%d/%m/%Y · %H:%M")


def format_relative(created_at: str) -> str:
    dt = _local(created_at)
    today = datetime.now().astimezone().date()
    if dt.date() == today:
        return f"Hoje · {dt:%H:%M}"
    if dt.date() == today - timedelta(days=1):
        return f"Ontem · {dt:%H:%M}"
    return dt.strftime("%d/%m/%Y · %H:%M")


def instruction_label(instruction: str) -> str:
    return instruction.replace("_", " ").capitalize()


# How each InstructionsMap entry is presented: card title, card subtitle, icon, history label.
# Instructions not listed here still work and get a generic card.
ACTIONS = {
    "summarize": ("Resumir", "Visão geral da aula", "lines", "Resumo"),
    "bullet_points": ("Tópicos", "Pontos principais", "list", "Tópicos"),
    "action_items": ("Tarefas", "O que fazer depois", "check-square", "Tarefas"),
    "questions": ("Quiz", "Teste o que aprendeu", "help", "Quiz"),
}


def action_info(instruction: str):
    label = instruction_label(instruction)
    return ACTIONS.get(instruction, (label, "Comando personalizado", "sparkles", label))


def transcript_paragraphs(text: str, sentences_per_paragraph: int = 5) -> list:
    """Whisper returns one long block; split it into paragraphs for reading."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [
        " ".join(sentences[i:i + sentences_per_paragraph])
        for i in range(0, len(sentences), sentences_per_paragraph)
    ]
