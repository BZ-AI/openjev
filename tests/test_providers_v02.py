import httpx
import pytest

from openjev import Choice, Noul, OpenJev, Score
from openjev.providers import JevProvider, LayaProvider


class FakeLaya:
    def __init__(self):
        self.calls = []

    def predict(self, state, questions, **kwargs):
        self.calls.append((state, questions, kwargs))
        return {
            "answers": {
                "intent": {
                    "type": "choice",
                    "choice": "billing",
                    "probabilities": {"billing": 0.8, "tech": 0.2},
                    "confidence": 0.77,
                },
                "refund": {"type": "noul", "noul": 0.91},
                "risk": {
                    "type": "score",
                    "score": 1.1,
                    "probabilities": {"0": 0.1, "1": 0.7, "2": 0.2},
                    "confidence": 0.66,
                },
            },
            "latency_ms": 12.5,
            "routing": {"model": "multilingual"},
        }


def test_laya_provider_adapts_native_typed_answers():
    backend = FakeLaya()
    engine = OpenJev(LayaProvider(backend=backend, checkpoint="multilingual"))

    result = engine.evaluate(
        state={"message": "退款"},
        questions={
            "intent": Choice(criteria={"billing": "refunds", "tech": "errors"}),
            "refund": Noul(instructions="Does the user request a refund?"),
            "risk": Score(criteria=["low", "medium", "high"]),
        },
    )

    assert result.answers["intent"].choice == "billing"
    assert result.answers["intent"].confidence == pytest.approx(0.77)
    assert result.answers["refund"].probability == pytest.approx(0.91)
    assert result.answers["refund"].confidence == pytest.approx(0.91)
    assert result.answers["risk"].confidence == pytest.approx(0.66)
    assert result.usage.output_tokens == 0
    assert result.usage.latency_ms == pytest.approx(12.5)
    assert result.debug["provider_debug"][0]["routing"]["model"] == "multilingual"
    sent_questions = backend.calls[0][1]
    assert "criteria" not in sent_questions["refund"]


def test_jev_provider_adapts_systemone_wire_format():
    captured = {}

    def handler(request: httpx.Request):
        captured["json"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "model": "jev-test",
                "answers": {
                    "intent": {
                        "type": "choice",
                        "choice": "tech",
                        "probabilities": {"billing": 0.1, "tech": 0.9},
                        "confidence": 0.88,
                    },
                    "refund": {"type": "noul", "noul": 0.2},
                },
                "usage": {"input_tokens": 33, "output_tokens": 0},
                "latency_ms": None,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = JevProvider(
        api_key="test-key",
        model="jev-test",
        base_url="https://example.test",
        client=client,
    )
    result = OpenJev(provider).evaluate(
        state="login is broken",
        questions={
            "intent": Choice(criteria={"billing": "refunds", "tech": "errors"}),
            "refund": Noul(instructions="refund requested?"),
        },
    )

    assert result.answers["intent"].choice == "tech"
    assert result.answers["intent"].confidence == pytest.approx(0.88)
    assert result.answers["refund"].value is False
    assert result.usage.input_tokens == 33
    assert result.usage.latency_ms is not None
    assert '"model":"jev-test"' in captured["json"].replace(" ", "")
