import asyncio

from app.providers.mocks import FakeCallee
from app.relay.legs import MockLeg
from app.relay.session import RelaySession
from app.services.drafts import make_draft
from app.services.profiles import Modes
from app.store import InMemoryStore


class SeqLlm:
    def __init__(self, outputs):
        self.outputs, self.prompts = list(outputs), []

    async def complete_json(self, prompt, *, schema):
        self.prompts.append(prompt)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


KW = {
    "words": "30 month",
    "call_lang": "hi-IN",
    "type_lang": "hi-Latn",
    "last_caption": "Telma 40, कितनी गोली चाहिए?",
    "contact_notes": "Telma 40",
}


async def test_draft_carries_context_and_returns_one_sentence():
    llm = SeqLlm(
        [
            {
                "text": " Mujhe 30 goliyan chahiye, ek mahine ki. ",
                "lang": "hi",
                "changed_meaning_risk": False,
            }
        ]
    )
    d = await make_draft(llm, **KW)
    assert d and d.text == "Mujhe 30 goliyan chahiye, ek mahine ki." and not d.risk
    assert (
        "30 month" in llm.prompts[0]
        and "Telma 40, कितनी" in llm.prompts[0]
        and "Hindi in English letters" in llm.prompts[0]
    )


async def test_unsafe_or_bad_drafts_are_retried_then_dropped():
    bad = {"text": "OTP 482913 hai", "lang": "hi", "changed_meaning_risk": False}
    ok = {"text": "Theek hai.", "lang": "hi", "changed_meaning_risk": True}
    assert (await make_draft(SeqLlm([bad, ok]), **KW)).risk is True
    assert await make_draft(SeqLlm([bad, bad]), **KW) is None
    assert await make_draft(SeqLlm([RuntimeError("down")]), **KW) is None
    assert (
        await make_draft(
            SeqLlm([{"text": "x" * 300, "lang": "hi", "changed_meaning_risk": False}] * 2), **KW
        )
        is None
    )


async def _session(llm):
    store = InMemoryStore()
    await store.create_call({"id": "c1", "user_id": "u1"})
    s = RelaySession(
        call_id="c1",
        user_id="u1",
        store=store,
        name="Rafiq",
        preset="mute",
        call_lang="hi-IN",
        modes=Modes(["type", "help"], ["captions"]),
        leg=MockLeg(FakeCallee.from_fixture("pharmacy"), reply_delay=0.01),
        llm=llm,
    )
    q = s.subscribe()
    await s.start()
    return s, q


async def _until(q, t):
    for _ in range(40):
        ev = await asyncio.wait_for(q.get(), 2)
        if ev["t"] == t:
            return ev
    raise AssertionError(t)


async def test_draft_request_emits_draft_and_speaks_nothing():
    llm = SeqLlm(
        [
            {"items": ["a"]},
            {"text": "Mujhe 30 goliyan chahiye.", "lang": "hi", "changed_meaning_risk": False},
        ]
    )
    s, q = await _session(llm)
    await _until(q, "caption.final")
    await s.handle({"t": "draft.request", "words": "30 goli"})
    ev = await _until(q, "draft.ready")
    assert (
        ev["text"] == "Mujhe 30 goliyan chahiye."
        and ev["from_words"] == "30 goli"
        and ev["draft_id"]
    )
    assert all(t["speaker"] != "user" for t in await s.store.get_turns("c1"))  # nothing spoken yet
    await s.end()


async def test_draft_is_unavailable_without_the_ai_service():
    s, q = await _session(None)
    await s.handle({"t": "draft.request", "words": "30 goli"})
    assert (await _until(q, "error"))["code"] == "not_available"
    await s.end()
