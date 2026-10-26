QUESTION_BANK = {
    "technical": [
        {"question": "Explain the difference between a list and a tuple in Python.", "focus": ["accuracy", "examples", "trade-offs"]},
        {"question": "How would you evaluate a classification model beyond accuracy?", "focus": ["precision", "recall", "F1", "class imbalance"]},
        {"question": "What is the difference between REST and RPC-style APIs?", "focus": ["resource modeling", "methods", "trade-offs"]},
        {"question": "Explain overfitting and two ways to reduce it.", "focus": ["generalization", "validation", "regularization"]},
    ],
    "hr": [
        {"question": "Tell me about yourself and the kind of role you are targeting.", "focus": ["structure", "relevance", "specificity"]},
        {"question": "Describe a time you received feedback and acted on it.", "focus": ["context", "action", "learning"]},
        {"question": "Why are you interested in this role?", "focus": ["role research", "motivation", "evidence"]},
    ],
    "behavioral": [
        {"question": "Tell me about a difficult project and how you handled obstacles.", "focus": ["situation", "actions", "result", "reflection"]},
        {"question": "Describe a disagreement in a team and how you resolved it.", "focus": ["listening", "communication", "outcome"]},
    ],
}

def get_questions(category: str, role: str, limit: int = 5):
    category = category.lower()
    questions = QUESTION_BANK.get(category, QUESTION_BANK["technical"])
    return [
        {**q, "role_context": role, "category": category, "source": "local practice bank"}
        for q in questions[:max(1, min(limit, len(questions)))]
    ]

def evaluate_answer(question: str, answer: str, role: str) -> dict:
    words = [w for w in answer.split() if w.strip()]
    answer_lower = answer.lower()
    signal_terms = ["because", "for example", "result", "learned", "trade-off", "first", "then"]
    signals = sum(1 for term in signal_terms if term in answer_lower)
    length_score = min(len(words) / 80, 1.0) * 40
    structure_score = min(signals / 3, 1.0) * 30
    specificity_score = min(len(set(words)) / 35, 1.0) * 30
    score = round(length_score + structure_score + specificity_score)
    suggestions = []
    if len(words) < 35:
        suggestions.append("Add more detail: explain the context, your action, and the outcome.")
    if signals < 2:
        suggestions.append("Use a clear structure and include a concrete example or reasoning.")
    if len(set(words)) < 20:
        suggestions.append("Include specific technical details, decisions, or measurable results where relevant.")
    if not suggestions:
        suggestions.append("Good level of detail for practice. Verify technical accuracy and make the outcome explicit.")
    return {
        "practice_score": score,
        "rubric": {
            "answer_detail": round(length_score),
            "structure_signals": round(structure_score),
            "vocabulary_variety": round(specificity_score),
        },
        "suggestions": suggestions,
        "disclaimer": "This is a transparent heuristic for practice, not an objective or validated hiring assessment.",
    }
