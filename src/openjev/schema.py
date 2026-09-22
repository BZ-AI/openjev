from __future__ import annotations

from typing import Any

from .types import Choice, Noul, Question, Score


def response_schema(questions: dict[str, Question]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, question in questions.items():
        required.append(name)
        if isinstance(question, Noul):
            properties[name] = {
                "type": "object",
                "additionalProperties": False,
                "required": ["probability"],
                "properties": {
                    "probability": {"type": "number", "minimum": 0, "maximum": 1}
                },
            }
        elif isinstance(question, Choice):
            labels = list(question.criteria)
            properties[name] = {
                "type": "object",
                "additionalProperties": False,
                "required": ["probabilities"],
                "properties": {
                    "label": {"type": "string", "enum": labels},
                    "probabilities": {
                        "type": "object",
                        "required": labels,
                        "additionalProperties": False,
                        "properties": {
                            label: {"type": "number", "minimum": 0} for label in labels
                        },
                    },
                },
            }
        elif isinstance(question, Score):
            labels = [str(index) for index in range(len(question.criteria))]
            properties[name] = {
                "type": "object",
                "additionalProperties": False,
                "required": ["probabilities"],
                "properties": {
                    "probabilities": {
                        "type": "object",
                        "required": labels,
                        "additionalProperties": False,
                        "properties": {
                            label: {"type": "number", "minimum": 0} for label in labels
                        },
                    }
                },
            }
        else:
            raise TypeError(f"unsupported question type: {type(question).__name__}")

    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }

