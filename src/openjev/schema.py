from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import Choice, Noul, Question, Score


def output_schema(questions: Mapping[str, Question]) -> dict[str, Any]:
    if not questions:
        raise ValueError("At least one question is required.")

    properties: dict[str, Any] = {}

    for qid, question in questions.items():
        if isinstance(question, Noul):
            properties[qid] = {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Probability that the answer is yes/true.",
            }
        elif isinstance(question, Choice):
            labels = list(question.criteria)
            properties[qid] = {
                "type": "object",
                "additionalProperties": False,
                "required": labels,
                "properties": {
                    label: {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": _to_text(question.criteria[label]),
                    }
                    for label in labels
                },
            }
        elif isinstance(question, Score):
            labels = [str(i) for i in range(len(question.criteria))]
            properties[qid] = {
                "type": "object",
                "additionalProperties": False,
                "required": labels,
                "properties": {
                    label: {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": _to_text(question.criteria[int(label)]),
                    }
                    for label in labels
                },
            }
        else:
            raise TypeError(f"Unsupported question type: {type(question)!r}")

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["answers"],
        "properties": {
            "answers": {
                "type": "object",
                "additionalProperties": False,
                "required": list(questions),
                "properties": properties,
            }
        },
    }


def provider_payload(state: Any, questions: Mapping[str, Question]) -> dict[str, Any]:
    return {
        "state": state,
        "questions": {
            qid: {
                "type": q.type,
                "instructions": q.instructions,
                "criteria": q.criteria,
            }
            for qid, q in questions.items()
        },
        "answer_contract": {
            "noul": "Return one probability in [0,1] for yes/true.",
            "choice": "Return one probability for every allowed label.",
            "score": "Return one probability for every ordered score level.",
            "rules": [
                "Answer every question exactly once.",
                "Do not add labels not present in the question.",
                "For choice/score, probabilities should sum to 1.",
                "Return JSON only.",
            ],
        },
    }


def _to_text(value: Any) -> str:
    if value is None:
        return "No additional description."
    if isinstance(value, str):
        return value
    return repr(value)
