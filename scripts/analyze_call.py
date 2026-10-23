"""Analyse a scripted call. Run from apps/api after the call:
  uv run python ../../scripts/analyze_call.py ../../docs/test-scripts/bolna-call-2.json [execution_id]
Reads captions and timing from the running dev server; optionally Bolna's transcript.
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, ".")
from app.relay.call_analysis import match_lines, timing_summary  # noqa: E402

env = dict(
    line.strip().split("=", 1)
    for line in Path(".env").read_text().splitlines()
    if "=" in line and not line.startswith("#")
)
script = json.loads(Path(sys.argv[1]).read_text())
log = httpx.get(
    "http://localhost:8000/v1/dev/log", headers={"Authorization": f"Bearer {env['WEBHOOK_SECRET']}"}
).json()

rows = match_lines(script["lines"], log["captions"])
print(f"{'ID':4} {'sim':>5} {'facts':>5} {'frag':>4}  heard")
for r in rows:
    print(
        f"{r['id']:4} {r['similarity']:5.2f} {r['facts']:>5} {r['fragments']:4}  {r['heard'] or '-- NOT CAPTURED --'}"
    )
heard = [r for r in rows if r["heard"]]
print(f"\nlines captured: {len(heard)}/{len(rows)}")
print(f"mean similarity (captured): {sum(r['similarity'] for r in heard) / max(1, len(heard)):.2f}")
print(f"mean fragments per turn: {sum(r['fragments'] for r in heard) / max(1, len(heard)):.1f}")
print("timing:", json.dumps(timing_summary(log["events"])))
if len(sys.argv) > 2:
    d = httpx.get(
        f"https://api.bolna.ai/executions/{sys.argv[2]}",
        headers={"Authorization": f"Bearer {env['BOLNA_API_KEY']}"},
    ).json()
    print(
        "\nBolna: status",
        d.get("status"),
        "| cost",
        d.get("total_cost"),
        "| hangup",
        (d.get("telephony_data") or {}).get("hangup_reason"),
    )
