"""Bolna-as-phone-line spike. Usage (from apps/api): uv run python ../../scripts/bolna_spike.py <cmd>

  register        register our /v1/llm endpoint as a Bolna custom LLM
  agent           create the relay agent (Sarvam STT and TTS, our LLM, Bolna default number)
  call <number>   place a call to <number> (E.164)
Reads keys from .env in the current directory; saves ids to ../../.spike-state.json (gitignored).
"""

import json
import sys
from pathlib import Path

import httpx

ENV = dict(
    line.strip().split("=", 1)
    for line in Path(".env").read_text().splitlines()
    if "=" in line and not line.startswith("#")
)
STATE = Path("../../.spike-state.json")
BASE = ENV.get("BOLNA_API_BASE") or "https://api.bolna.ai"
HEAD = {"Authorization": f"Bearer {ENV['BOLNA_API_KEY']}", "Content-Type": "application/json"}
MODEL = "awaaz-relay"

DISCLOSURE = (
    "Namaste, main Rafiq bol raha hoon. Main bol nahi sakta, isliye ek assistant meri likhi "
    "baat padh raha hai. Aap normal baat kijiye."
)


def load() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save(d: dict) -> None:
    STATE.write_text(json.dumps(d, indent=2))


def show(r: httpx.Response) -> dict:
    print(r.status_code, r.text[:600])
    r.raise_for_status()
    return r.json()


def register() -> None:
    body = {
        "custom_model_name": MODEL,
        "custom_model_url": f"{ENV['PUBLIC_BASE_URL']}/v1/llm",
        "custom_model_key": ENV["WEBHOOK_SECRET"],
        "custom_model_family": "openai",
    }
    show(httpx.post(f"{BASE}/user/model/custom", headers=HEAD, json=body, timeout=60))


def agent() -> None:
    cfg = {
        "agent_config": {
            "agent_name": "Awaaz relay spike",
            "agent_welcome_message": DISCLOSURE,
            "tasks": [
                {
                    "task_type": "conversation",
                    "toolchain": {
                        "execution": "sequential",
                        "pipelines": [["transcriber", "llm", "synthesizer"]],
                    },
                    "tools_config": {
                        "llm_agent": {
                            "agent_type": "simple_llm_agent",
                            "agent_flow_type": "streaming",
                            "llm_config": {
                                "provider": "custom",
                                "family": "openai",
                                "base_url": f"{ENV['PUBLIC_BASE_URL']}/v1/llm",
                                "model": MODEL,
                                "max_tokens": 150,
                                "temperature": 0.2,
                            },
                        },
                        "synthesizer": {
                            "provider": "sarvam",
                            "provider_config": {
                                "voice": "Rahul",
                                "voice_id": "rahul",
                                "model": "bulbul:v3",
                                "language": "hi",
                                "speed": 1.0,
                            },
                            "stream": True,
                            "buffer_size": 100,
                        },
                        "transcriber": {
                            "provider": "sarvam",
                            "model": "saaras:v4",
                            "language": "hi",
                            "stream": True,
                            "endpointing": 500,
                        },
                        "input": {"provider": "plivo", "format": "wav"},
                        "output": {"provider": "plivo", "format": "wav"},
                    },
                    "task_config": {"call_terminate": 180, "hangup_after_silence": 40},
                }
            ],
        },
        "agent_prompts": {
            "task_1": {"system_prompt": "Relay agent. Replies come from the user's typed text."}
        },
    }
    out = show(httpx.post(f"{BASE}/v2/agent", headers=HEAD, json=cfg, timeout=60))
    save({**load(), "agent_id": out["agent_id"]})


def call(number: str) -> None:
    body = {"agent_id": load()["agent_id"], "recipient_phone_number": number}
    show(httpx.post(f"{BASE}/call", headers=HEAD, json=body, timeout=60))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"register": register, "agent": agent, "call": lambda: call(sys.argv[2])}[cmd]()
