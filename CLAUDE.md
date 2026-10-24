# CLAUDE.md — Awaaz

You are implementing **Awaaz**: phone calls for people who can’t hear or speak. Each user chooses how they talk (type, own voice, phrases, “help me say it”) and how they hear (captions, clear voice, normal audio, translation, summaries), and Awaaz relays an ordinary phone call between those choices. Built for the Bolna Buildathon; deadline **Saturday 31 October 2026, noon IST**. Owner: Amit (React/TypeScript, Python/FastAPI). He works a day job; expect short weekday check-ins.

## Read these first, in order
1. `README.md`
2. `docs/PRD.md` (product v0.1) then `docs/PRD-ADDENDUM-v2.md` (talk/hear profiles, call paths, WhatsApp, own number). The addendum wins over the PRD.
3. `docs/IMPLEMENTATION.md` — the technical source of truth. It wins over both PRD documents on anything technical.
4. `tasks/PLAN.md` — your ordered work queue. **Start with M0 (audio spike).**
5. `design/ui-prototype.html` + `design/README.md` — visual source of truth. Port it; don’t redesign.
6. `specs/` — contracts: SQL, relay protocol, JSON schemas, prompts, agent spec, data, fixtures, messages.
7. `tasks/HUMAN-CHECKLIST.md` — what Amit does (KYC, accounts, testers). Don’t wait on it; use mock and simulator modes.

## Fixed stack (ask Amit before changing)
- `apps/web`: React 18 + TypeScript + Vite PWA, React Router, TanStack Query, Supabase JS, plain CSS from the prototype, AudioWorklets for audio.
- `apps/api`: Python 3.12 or newer (tested on 3.12 and 3.14; production runs 3.14), FastAPI, Pydantic v2, asyncio, httpx, websockets; one Render Starter instance (sessions live in memory).
- Supabase (Postgres + RLS, Auth, Realtime, Storage).
- Telephony: **Bolna** is the live phone leg (custom-LLM relay agent; Twilio upgrade skipped, see `docs/DECISIONS.md` and `docs/SPIKE-bolna.md`). Calls from the app and from WhatsApp use the same `OtherLeg` abstraction. Incoming calls and own-number design: `docs/ARCHITECTURE-incoming.md`.
- WhatsApp: **Meta WhatsApp Cloud API** (free test number). The Twilio trial cannot push free-form messages; its adapter stays for a paid account.
- Auth and data: Supabase Auth (Google and email/password), Postgres via the API's service role.
- Speech: **Sarvam only** (Saaras v3 streaming STT, Bulbul v3 streaming TTS, translation). Deepgram and Cartesia dropped after a bake-off (see `docs/DECISIONS.md`); add a second provider only for a measured requirement.
- Call for me: Bolna agents. LLM behind one adapter with JSON-schema output.
- No WebRTC SFU, no Redis, no Next.js for v1.

## How to work
- Current plan and decisions: `tasks/PLAN.md` (revision at the top), `docs/DECISIONS.md`, `PROGRESS.md`.
- **Three run modes:** `MOCK_PROVIDERS=true` (scripted fake callee, text only), **callee simulator** (`/dev/callee/:id`, real STT/TTS, no telephony), **live** (Bolna phone leg). Every feature must work in mock mode; audio features must work with the simulator before going live.
- One ticket at a time; tests; commit `<ID>: <summary>`; keep `PROGRESS.md` (done / doing / blocked / unverified).
- Provider code only in `apps/api/app/providers/`. Relay logic only in `apps/api/app/relay/`.
- **⚠️ VERIFY** items: check current provider docs (use web fetch if available) before writing live adapters; otherwise isolate the assumption in one function with a fixture test and list it under “Unverified” in `PROGRESS.md`.
- Validate every LLM output and every WebSocket event against `specs/schemas` and `specs/protocol`.
- Audio: 20 ms frames, strict pacing, μ-law 8 kHz on telephony, PCM16 16 kHz to/from the app. Python 3.13 has no `audioop`; use NumPy or `audioop-lts`.
- Secrets only in `.env` (see `env/`). Mask phone numbers in logs (last 4 digits).
- Ask Amit when a product decision isn’t covered, a live key is missing after the mock/sim version is done, or a provider behaves differently enough to change the design.

## Non-negotiable rules
1. Every relay and task call starts with the disclosure line (an assistant is involved, on whose behalf). Not configurable.
2. Nothing is spoken on a call without a user action, except the disclosure, the keeper line and the user’s own live voice.
3. AI-drafted (Help me say) and translated text is shown to the user and spoken only after they confirm.
4. Clear voice repeats the other person’s exact words (translated only if the user asked); never alter numbers, dates, names or medicines.
5. Scam shield: after an OTP/PIN/CVV/UPI PIN/remote-app request, never speak 4–8 digit runs on that call; warn the user; log the event. Zero missed requests on `specs/data/scam_eval.csv`.
6. Task agent: no payments, no credentials, approvals for anything outside limits, “calling on behalf of”.
7. Never spoof caller ID or try to read normal phone-call audio; both are illegal or blocked. Calls show the Awaaz number.
8. Voice cloning only of the account holder, with a stored consent sentence; voices never exported.
9. Audio not stored by default; unsaved turns purged after 30 days; family sharing only with consent.
10. Cost guards: `MAX_CALL_MINUTES`, `DAILY_MINUTES_PER_USER`. All demo data fictional.

## Conventions
- Python: ruff, type hints, pytest + pytest-asyncio. TypeScript: strict, no `any` in new code.
- Times stored UTC, shown IST. Phone numbers E.164.
- UI copy: sentence case, curly apostrophes (’), no emoji in the app UI (icons from the sprite).

## Definition of done
- Pharmacy (type to speak), bank scam (shield) and clinic (clear voice) scenarios pass on real calls.
- A gas booking via Call for me completes with an approval from WhatsApp.
- A voice note round-trips on WhatsApp (to text, and a reply in the user’s voice).
- Latency budget in IMPLEMENTATION §9.4 met or documented; README complete; `PROGRESS.md` lists anything unverified or cut.
