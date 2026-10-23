"""Bolna-as-phone-line spike. Usage (from apps/api): uv run python ../../scripts/bolna_spike.py <cmd>

  register        register our /v1/llm endpoint as a Bolna custom LLM
  agent [sarvam|deepgram]  create the relay agent (Sarvam STT and TTS, our LLM, Bolna default number)
  call <number> [sarvam|deepgram]  place a call to <number> (E.164)
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


TRANSCRIBERS = {
    "sarvam": {
        "provider": "sarvam",
        "model": "saaras:v4",
        "language": "hi",
        "stream": True,
        "endpointing": 1200,
    },
    "deepgram": {
        "provider": "deepgram",
        "model": "nova-3",
        "language": "hi",
        "stream": True,
        "endpointing": 1200,
    },
}


def agent(stt: str = "sarvam", live: bool = False) -> None:
    cfg = {
        "agent_config": {
            "agent_name": f"Awaaz relay spike ({stt})",
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
                        "transcriber": TRANSCRIBERS[stt],
                        "input": {"provider": "plivo", "format": "wav"},
                        "output": {"provider": "plivo", "format": "wav"},
                    },
                    "task_config": {
                        "call_terminate": 420,
                        "hangup_after_silence": 120,
                        "check_if_user_online": False,
                        "number_of_words_for_interruption": 3,
                        "incremental_delay": 800,
                    },
                }
            ],
        },
        "agent_prompts": {
            "task_1": {"system_prompt": "Relay agent. Replies come from the user's typed text."}
        },
    }
    if live:  # the product relay agent: per-call disclosure and call id via /call user_data
        webhook = f"{ENV['PUBLIC_BASE_URL']}/v1/webhooks/bolna?s={ENV['WEBHOOK_SECRET']}"
        cfg["agent_config"]["agent_name"] = "Awaaz relay (live)"
        cfg["agent_config"]["agent_welcome_message"] = "{disclosure}"
        cfg["agent_config"]["webhook_url"] = webhook
        cfg["agent_prompts"] = {
            "task_1": {"system_prompt": "[[awaaz:call={call_id}]] Relay agent."}
        }
    out = show(httpx.post(f"{BASE}/v2/agent", headers=HEAD, json=cfg, timeout=60))
    if live:
        env_path = Path(".env")
        lines = [
            f"BOLNA_RELAY_AGENT_ID={out['agent_id']}"
            if x.startswith("BOLNA_RELAY_AGENT_ID=")
            else x
            for x in env_path.read_text().splitlines()
        ]
        env_path.write_text("\n".join(lines) + "\n")
        print("BOLNA_RELAY_AGENT_ID updated in .env")
    else:
        save({**load(), "agent_id": out["agent_id"], f"agent_{stt}": out["agent_id"]})


def call(number: str, stt: str | None = None) -> None:
    state = load()
    body = {
        "agent_id": state[f"agent_{stt}"] if stt else state["agent_id"],
        "recipient_phone_number": number,
    }
    show(httpx.post(f"{BASE}/call", headers=HEAD, json=body, timeout=60))


if __name__ == "__main__":
    cmd = sys.argv[1]
    arg = sys.argv[3] if len(sys.argv) > 3 else None
    {
        "register": register,
        "agent": lambda: agent(sys.argv[2] if len(sys.argv) > 2 else "sarvam"),
        "relay-agent": lambda: agent("sarvam", live=True),
        "call": lambda: call(sys.argv[2], arg),
    }[cmd]()
