"""Compare a scripted call against what the system captured (dev tooling for spikes)."""

import re
from difflib import SequenceMatcher
from statistics import median

_PUNCT = re.compile(r"[।.,?!₹\"'’“”\-…()]")


def norm(text: str) -> str:
    return " ".join(_PUNCT.sub(" ", text.lower()).split())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def facts_found(heard: str, facts: list[list[str]]) -> int:
    h = norm(heard)
    return sum(any(norm(alt) in h for alt in group) for group in facts)


def match_lines(lines: list[dict], captions: list[dict], threshold: float = 0.3) -> list[dict]:
    """Greedy in-order alignment of script lines to caption turns (a turn is used once)."""
    used: set[int] = set()
    out = []
    for line in lines:
        best, best_i = 0.0, -1
        for i, c in enumerate(captions):
            if i in used:
                continue
            s = similarity(line["say_hi"], c["text"])
            if s > best:
                best, best_i = s, i
        if best_i >= 0 and best >= threshold:
            used.add(best_i)
            c = captions[best_i]
            out.append(
                {
                    "id": line["id"],
                    "heard": c["text"],
                    "similarity": round(best, 2),
                    "facts": f"{facts_found(c['text'], line['facts'])}/{len(line['facts'])}",
                    "fragments": c.get("fragments", 1),
                }
            )
        else:
            out.append(
                {
                    "id": line["id"],
                    "heard": None,
                    "similarity": 0.0,
                    "facts": f"0/{len(line['facts'])}",
                    "fragments": 0,
                }
            )
    return out


def timing_summary(events: list[dict]) -> dict:
    """Delays and counts from the bridge event log."""
    say_to_spoken, last_say = [], None
    for e in events:
        if e["type"] == "say":
            last_say = e["t"]
        elif e["type"] == "spoken" and last_say is not None:
            say_to_spoken.append(e["t"] - last_say)
            last_say = None
    count = lambda k: sum(1 for e in events if e["type"] == k)
    return {
        "replies_spoken": count("spoken"),
        "say_to_spoken_median_s": round(median(say_to_spoken), 2) if say_to_spoken else None,
        "say_to_spoken_max_s": round(max(say_to_spoken), 2) if say_to_spoken else None,
        "keeper_lines": count("keeper"),
        "superseded_requests": count("superseded"),
        "timeouts": count("timeout"),
        "requests": count("request"),
    }
