"""Machine-translate the app's English strings (apps/web/src/i18n/locales/en.json) into the other
languages. Output is a starting point: native speakers should review it before launch.

Run from apps/api:  uv run python ../../scripts/translate_locales.py [lang ...]
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "apps/web/src/i18n/locales"
ENV = dict(
    line.strip().split("=", 1)
    for line in (ROOT / "apps/api/.env").read_text().splitlines()
    if "=" in line and not line.startswith("#")
)
MODEL = "gemini-3.5-flash"

TARGETS = {
    "hi": "Hindi in Devanagari script",
    "hi-Latn": "Hinglish: everyday Hindi written in English letters, the way people type on WhatsApp (for example 'Call shuru karein', 'Aap kaise sunte hain')",
    "mr": "Marathi in Devanagari script",
    "bn": "Bengali in Bengali script",
    "ta": "Tamil in Tamil script",
    "te": "Telugu in Telugu script",
    "kn": "Kannada in Kannada script",
    "ml": "Malayalam in Malayalam script",
    "gu": "Gujarati in Gujarati script",
    "pa": "Punjabi in Gurmukhi script",
    "or": "Odia in Odia script",
}

PROMPT = """Translate the values of this JSON object, the interface text of Awaaz, a phone-calling app for people who cannot hear or speak in India, into {target}.

Rules:
- Return the same JSON structure with exactly the same keys. Translate only the values.
- Keep every placeholder like {{{{name}}}} exactly as it is.
- Keep these words unchanged: Awaaz, OTP, PIN, UPI, CVV, ISL, BP, Google, Telma 40.
- Use simple, warm, everyday words that an older person with little schooling understands. Prefer common spoken words over formal or Sanskritised ones. Keep labels short like an app's buttons.
- Keep emoji out. Keep punctuation natural for the language.

JSON:
{source}"""


def flatten(d: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def problems(src: dict, got: dict) -> list[str]:
    a, b = flatten(src), flatten(got)
    issues = [f"missing {k}" for k in a if k not in b] + [f"extra {k}" for k in b if k not in a]
    for k, v in a.items():
        if k in b and set(re.findall(r"\{\{\w+\}\}", v)) != set(re.findall(r"\{\{\w+\}\}", str(b[k]))):
            issues.append(f"placeholder {k}")
    return issues


async def translate(client: httpx.AsyncClient, lang: str, source: dict) -> None:
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(target=TARGETS[lang], source=json.dumps(source, ensure_ascii=False, indent=1))}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={ENV['LLM_API_KEY']}"
    for attempt in range(2):
        r = await client.post(url, json=body)
        if r.status_code != 200:
            print(lang, "HTTP", r.status_code, r.text[:120])
            continue
        try:
            got = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, ValueError) as exc:
            print(lang, "bad output", exc)
            continue
        issues = problems(source, got)
        if not issues:
            (LOCALES / f"{lang}.json").write_text(json.dumps(got, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(lang, "ok", f"(attempt {attempt + 1})")
            return
        print(lang, "issues:", issues[:5])
    print(lang, "FAILED")


async def main() -> None:
    source = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
    langs = sys.argv[1:] or list(TARGETS)
    async with httpx.AsyncClient(timeout=180) as client:
        await asyncio.gather(*(translate(client, lang, source) for lang in langs))


asyncio.run(main())
