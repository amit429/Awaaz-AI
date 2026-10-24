"""After-call summary: what was agreed, the facts to remember, next steps, and a short note that
can be read aloud in the user's reading language."""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.providers.base import Llm
from app.services.languages import name_of
from app.specs import load_json

SCHEMA = load_json("schemas/call_summary.schema.json")


FACT_TYPES = {"money", "time", "date", "phone", "address", "reference", "other"}


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%A %d %B %Y, %H:%M")


def _clean(out: dict[str, Any]) -> dict[str, Any]:
    for f in out.get("facts", []):
        if f.get("type") not in FACT_TYPES:
            f["type"] = "other"
        f.setdefault("iso", None)
    return out


def _transcript(turns: list[dict[str, Any]]) -> str:
    lines = []
    for t in turns:
        who = "Other person" if t["speaker"] == "other" else "User"
        if t.get("source") in ("disclosure", "keeper"):
            continue
        lines.append(f"{who}: {t['text']}")
    return "\n".join(lines)


def fallback(turns: list[dict[str, Any]]) -> dict[str, Any]:
    """Plain summary without a model: the other person's last lines and the numbers they said."""
    said = [t for t in turns if t["speaker"] == "other"]
    facts = []
    for t in said:
        for e in t.get("entities") or []:
            kind = e.get("type") if e.get("type") in ("money", "time", "date", "phone") else "other"
            facts.append({"type": kind, "label": kind, "value": e.get("text", ""), "iso": None})
    note = " ".join(t["text"] for t in said[-3:])[:480]
    return {
        "title": "Call summary",
        "agreed": [t["text"][:140] for t in said[-2:]],
        "facts": facts[:8],
        "next_steps": [],
        "summary_read_lang": note,
        "reminders": [],
    }


async def summarise(turns: list[dict[str, Any]], read_lang: str, llm: Llm | None) -> dict[str, Any]:
    if not any(t["speaker"] == "other" for t in turns):
        return {**fallback(turns), "agreed": [], "facts": [], "summary_read_lang": ""}
    if llm is None:
        return fallback(turns)
    prompt = (
        "Summarise this phone call for a person who could not hear it well. Be faithful: never "
        "change a number, date, name or medicine, and add nothing that was not said. "
        f"Write title, agreed, next_steps and summary_read_lang in {name_of(read_lang)}. "
        "summary_read_lang is 2 to 4 short sentences to be read aloud. Use reminders only when a "
        f"time was agreed (ISO 8601, India time; today is {_today()}).\n\nCall:\n"
        + _transcript(turns)
    )
    try:
        out = await llm.complete_json(prompt, schema=SCHEMA)
        if out.get("summary_read_lang") is None:
            return fallback(turns)
        return _clean({**fallback([]), **out})
    except Exception:  # noqa: BLE001 - a summary is optional; never fail the screen
        return fallback(turns)
