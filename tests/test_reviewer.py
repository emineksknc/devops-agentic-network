"""Reviewer kararliligi: gerekcesiz FAILED retry, cift bozukta durust fail-closed."""
import asyncio

from src.agents.reviewer_agent import ReviewerAgent

DIFF = "--- Dosya: app.ts ---\n+const x = 1;"


class FakeLLM:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    async def generate_response(self, *a, **k):
        self.calls += 1
        return self.outputs.pop(0)


def test_reasonless_failed_retries_to_passed():
    r = ReviewerAgent(model_client=FakeLLM([
        '{"review_status": "FAILED", "affected_file": null, "affected_symbol": null, "review_comment": ""}',
        '{"review_status": "PASSED", "affected_file": null, "affected_symbol": null, "review_comment": "Sabit."}',
    ]))
    out = asyncio.run(r.run("t", context={"code_changes": DIFF}))
    assert out["review_status"] == "PASSED"
    assert r.llm.calls == 2


def test_double_garbage_is_honest_fail_closed():
    r = ReviewerAgent(model_client=FakeLLM(["bozuk", "yine bozuk"]))
    out = asyncio.run(r.run("t", context={"code_changes": DIFF}))
    assert out["review_status"] == "FAILED"
    assert "2 deneme" in out["review_comment"]


def test_invalid_status_retries():
    r = ReviewerAgent(model_client=FakeLLM([
        '{"review_status": "BELKI"}',
        '{"review_status": "PASSED", "review_comment": "Temiz."}',
    ]))
    out = asyncio.run(r.run("t", context={"code_changes": DIFF}))
    assert out["review_status"] == "PASSED"
