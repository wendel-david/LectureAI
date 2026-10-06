def score(questions: list, answers: list) -> int:
    return sum(1 for q, a in zip(questions, answers) if a == q["correct_index"])


def missed_questions(questions: list, answers: list) -> list:
    return [(q, a) for q, a in zip(questions, answers) if a != q["correct_index"]]


def format_missed(questions: list, answers: list) -> str:
    lines = []
    for i, (q, a) in enumerate(missed_questions(questions, answers), start=1):
        chosen = q["options"][a] if a is not None else "(no answer)"
        lines.append(
            f"{i}. {q['question']}\n"
            f"   Student answered: {chosen}\n"
            f"   Correct answer: {q['options'][q['correct_index']]}"
        )
    return "\n".join(lines)
