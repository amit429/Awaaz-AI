import asyncio

from app.providers.mocks import FakeCallee
from app.relay import registry
from app.relay.legs import MockLeg
from app.relay.session import RelaySession
from app.services.profiles import Modes
from app.services.replies import ReplyContext, build_prompt, suggest
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


CTX = ReplyContext(
    user_name="Rafiq",
    contact_name="Sharma Medical",
    contact_notes="BP medicine is Telma 40",
    typed=["Telma 40 chahiye"],
)
TURNS = [("other", "हाँ, मिल जाएगी। ₹420 होंगे।")]


def test_prompt_carries_the_context():
    p = build_prompt(CTX, TURNS)
    assert "Rafiq" in p and "Sharma Medical" in p and "Telma 40" in p and "₹420" in p
    assert "Hindi in English letters" in p and "them: हाँ, मिल जाएगी" in p


async def test_valid_output_is_cleaned_and_limited():
    llm = SeqLlm(
        [
            {
                "items": [
                    "Theek hai, rakh dijiye",
                    "  Ghar bhej sakte hain? ",
                    "Phir se boliye",
                    "extra",
                ]
            }
        ]
    )
    out = await suggest(llm, CTX, TURNS)
    assert out == ["Theek hai, rakh dijiye", "Ghar bhej sakte hain?", "Phir se boliye"]  # capped at 3


async def test_digit_runs_and_empty_items_never_become_suggestions():
    llm = SeqLlm([{"items": ["OTP hai 482913", "", "Theek hai"]}])
    assert await suggest(llm, CTX, TURNS) == ["Theek hai"]


async def test_one_retry_then_nothing():
    assert await suggest(SeqLlm([{"items": []}, {"items": ["Haan"]}]), CTX, TURNS) == ["Haan"]
    assert await suggest(SeqLlm([{"items": []}, {"nope": 1}]), CTX, TURNS) == []
    assert await suggest(SeqLlm([RuntimeError("down")]), CTX, TURNS) == []


async def test_session_emits_suggestions_for_the_latest_turn_only():
    store = InMemoryStore()
    await store.create_call({"id": "c1", "user_id": "u1"})
    llm = SeqLlm([{"items": ["Theek hai", "Ghar bhej do", "Phir se boliye"]}])
    s = RelaySession(
        call_id="c1",
        user_id="u1",
        store=store,
        name="Rafiq",
        preset="mute",
        call_lang="hi-IN",
        modes=Modes(["type", "replies"], ["captions"]),
        leg=MockLeg(FakeCallee.from_fixture("pharmacy"), reply_delay=0.01),
        llm=llm,
    )
    registry.add(s)
    q = s.subscribe()
    await s.start()
    seen = []
    for _ in range(30):
        seen.append(await asyncio.wait_for(q.get(), 2))
        if seen[-1]["t"] == "suggestions":
            break
    assert seen[-1] == {
        "t": "suggestions",
        "turn": 2,
        "items": ["Theek hai", "Ghar bhej do", "Phir se boliye"],
    }
    await s.end()
    registry.clear()


async def test_no_suggestions_unless_replies_mode_is_on():
    store = InMemoryStore()
    await store.create_call({"id": "c2", "user_id": "u1"})
    llm = SeqLlm([{"items": ["x"]}])
    s = RelaySession(
        call_id="c2",
        user_id="u1",
        store=store,
        name="R",
        preset=None,
        call_lang="hi-IN",
        modes=Modes(["type"], ["captions"]),
        leg=MockLeg(FakeCallee.from_fixture("pharmacy"), reply_delay=0.01),
        llm=llm,
    )
    q = s.subscribe()
    await s.start()
    await asyncio.sleep(0.2)
    assert llm.prompts == []
    assert q.qsize() > 0
    await s.end()
