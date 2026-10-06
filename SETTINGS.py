SettingsMap = {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000,
}


TranscriberMap = {
    "model" :"openai/whisper-tiny"
}


InstructionsMap = {
    "summarize": "Summarize the following transcript in a concise paragraph.",
    "bullet_points": "Summarize the following transcript as a bulleted list of key points.",
    "action_items": "Extract any action items or follow-up tasks mentioned in the following transcript.",
    "questions" : "Generate a quiz covering every topic of the lecture, make it multiple choice, and don't make it too easy, the options must make the student think about before choosing, try creating them of the student become in beetween 2 or more options.  "
}

QuizMap = {
    "instruction": "questions",
    "review": "The student just took a quiz about the lecture below and got the questions listed at the end wrong. Write a study review in markdown that re-teaches the concepts behind each mistake: explain why the correct answer is right and why the student's answer is wrong, using the lecture content. Group related mistakes, keep it clear and concise, and write in the same language as the lecture.",
    "focused_quiz": "Focus the new quiz on the concepts behind the questions the student got wrong (listed below). Write new questions that test the same concepts from different angles; do not repeat the same questions.",
}
