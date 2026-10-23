# Build plan — tickets for Claude Code

Work top to bottom, one ticket at a time: implement, test, commit as `<ID>: <summary>`, update `PROGRESS.md`.
**[mock]** = must work with `MOCK_PROVIDERS=true`. **[sim]** = works with the callee simulator (real STT/TTS, no telephony). **[live]** = needs real telephony keys; if missing, finish mock/sim and move on.

## M0 — Audio spike (Sat 24 Oct, first half). Do this before anything else.

| ID | Ticket | Acceptance |
|---|---|---|
| M0-01 | Minimal FastAPI with `POST /v1/plivo/answer/{leg}` (bidirectional stream XML) and `WS /v1/media/plivo/{leg}` that echoes audio back | Calling your own phone through Plivo, you hear your voice echoed **[live]** |
| M0-02 | μ-law ↔ PCM16 and 8k ↔ 16k resampling (`relay/audio.py`) with unit tests | Round-trip error within tolerance |
| M0-03 | Cartesia (or Sarvam) TTS streamed into the call as 20 ms frames | Typed text in a terminal is heard on the phone **[live]** |
| M0-04 | Deepgram Flux STT on the inbound stream with end-of-turn events printed | Speaking on the phone prints final captions within ~1 s **[live]** |
| M0-05 | Write findings (formats, quirks, latency) to `docs/SPIKE-audio.md` | Kill-switch decision recorded |

## M1 — Skeleton (Sat 24 Oct)

| ID | Ticket | Acceptance |
|---|---|---|
| M1-01 | Monorepo layout per IMPLEMENTATION §6; copy docs/specs/design | README explains running both apps |
| M1-02 | Supabase migration + seed (presets, task templates, stock voices) | `db push` succeeds |
| M1-03 | FastAPI app factory, config, CORS, health, JWT auth (JWKS + HS256 fallback), audit, jobs poller | Tests green |
| M1-04 | Provider interfaces + mocks (Plivo leg → scripted fake callee from `specs/fixtures/callee_*.json`) | Imports never need keys in mock mode |
| M1-05 | PWA shell: Vite + React + TS, tokens/app CSS from prototype, Icons component, auth (email magic link or Google), routes | Home screen matches prototype **[mock]** |
| M1-06 | Onboarding: preset choice → `comm_profiles`, name, languages, voice (stock) | New user reaches Home in < 90 s **[mock]** |

## M2 — Live call console (Sun 25 Oct)

| ID | Ticket | Acceptance |
|---|---|---|
| M2-01 | `POST /v1/calls` → profile resolution (request → contact override → profile) → `calls` row → `RelaySession` | Unit tests for resolution |
| M2-02 | `WS /v1/relay/{id}` with JWT, event validation against `specs/protocol/relay-events.schema.json`, ping, replay buffer | Contract tests |
| M2-03 | Session: disclosure line (from `specs/messages/disclosure_lines.json`), `user.say` → TTS → other leg, persist turns | Pharmacy script runs end to end **[mock] [sim]** |
| M2-04 | Captions: partial/final, translate (if read ≠ call language), entities (`relay/entities.py` per `specs/data/entity_patterns.md`) | Golden tests on the four entity examples |
| M2-05 | Keeper timer, ask again, end call, call states | Keeper fires after 5 s typing, max every 8 s |
| M2-06 | Call screen UI: feed bubbles, chips (tap to save), hear toggles, dock, tools, sheets (phrases, keypad), scam alert component | Matches prototype **[mock]** |
| M2-07 | Callee simulator: `WS /v1/dev/callee/{session}` + `/dev/callee/:id` page (mic + speaker) | Real two-way audio between two tabs **[sim]** |
| M2-08 | Plivo live adapter wired into the session (from M0) | Real call to a test phone works **[live]** |

## M3 — Talk modes (Mon 26 Oct)

| ID | Ticket | Acceptance |
|---|---|---|
| M3-01 | Smart replies (`specs/prompts/smart_replies.md`), cancel stale requests | 3 replies within 1.5 s **[sim]** |
| M3-02 | Phrases: defaults from `specs/data/phrases_default.json`, per-contact phrases, use counts | Phrase sheet works |
| M3-03 | Help me say: `draft.request` → `draft.ready` → Say it / Edit | Nothing spoken before tap |
| M3-04 | My voice: AudioWorklet capture (16 kHz) → binary frames → resample → other leg; user STT for transcript | Other side hears the user live with < 400 ms delay **[sim]** |
| M3-05 | `mode.set` mid-call switching; dock shows profile modes | Switching keeps the call alive |
| M3-06 | Translation preview: `say.preview` / `say.confirm` when type language ≠ call language | Preview shown before speaking |

## M4 — Hearing and profiles (Tue 27 Oct)

| ID | Ticket | Acceptance |
|---|---|---|
| M4-01 | Normal audio to app: other-leg audio → 16 kHz → binary 0x02 → playback worklet | Audible in app with headphones **[sim]** |
| M4-02 | Clear voice: final turn → TTS at speech rate (Kalpa or Cartesia speed) → 0x03; Repeat/Slower/Louder buttons; voice commands from `voice_commands.csv` | Re-speak < 2 s; “phir se” repeats **[sim]** |
| M4-03 | Profile screen: presets, talk/hear option cards, languages, voice, easy font, live preview | Matches prototype |
| M4-04 | Contact overrides (talk/hear per contact) | Used at call start |
| M4-05 | Summaries: `summarise_call` job → `summaries` → voice note (TTS in read language) → call detail screen with fact rows and reminders (ICS download) | Summary within 10 s of hang-up |

## M5 — Call for me + scam shield (Wed 28 Oct)

| ID | Ticket | Acceptance |
|---|---|---|
| M5-01 | Scam rules on every final caption (`scam_keywords.csv`), LLM second opinion on weight-1 matches, `scam.warning`, digit blocking, `scam_events` | `scam_eval.csv`: zero missed requests (false positives listed) |
| M5-02 | Tasks API + templates + limits; Bolna start call; webhook → `task_result` | Mock result fixture creates a result card **[mock]** |
| M5-03 | `needs_approval` / `check_approval` tools; approval card in app via realtime | Approve/decline flows work **[mock]** |
| M5-04 | Task UI: tiles, form with limits, progress, approval, result | Matches prototype |
| M5-05 | Bolna task agents live (human creates agents) | Gas booking test with a friendly number **[live]** |

## M6 — WhatsApp bot (Thu 29 Oct)

| ID | Ticket | Acceptance |
|---|---|---|
| M6-01 | WA adapters (`log`, `twilio_sandbox`, `exotel`), webhook normalisation to fixture shape, `wa_users`, 24-hour window tracking | Fixtures parse |
| M6-02 | Intent routing (`wa_intent`) → start task; approvals via buttons; task results and summaries sent back | `wa_text_task.json` starts a task **[mock]** |
| M6-03 | Voice note → text (download media, STT, reply with transcript and quick replies) | `wa_voice_note.json` round-trips **[sim/live]** |
| M6-04 | Text → voice note in the user’s voice (TTS → OGG/Opus → upload → send) | Voice note plays in WhatsApp **[live]** |
| M6-05 | P1: live relay in chat (captions as messages, text replies spoken) | Optional |

## M7 — Polish, real users, demo (Fri 30 – Sat 31 Oct)

| ID | Ticket | Acceptance |
|---|---|---|
| M7-01 | `scripts/latency_probe.py` against the simulator; tune pacing | Budget met or documented |
| M7-02 | Deploy: Render Starter, Vercel, Supabase prod; Plivo/Bolna/WA URLs | Production call works |
| M7-03 | Real tester calls (3+) with consent; record hang-ups and caption errors | Numbers in `PROGRESS.md` |
| M7-04 | Public demo page (type a message, Awaaz calls your phone) with rate limit | Judges can try it |
| M7-05 | README with architecture, sponsor table, safety, results | Ready to submit |

## P1 backlog (only if ahead)
Speak clearly for me; voice cloning with consent; personal Awaaz numbers + incoming calls + message taking; missed-call forwarding; face to face mode; vibration cues; SOS card; clear voice on a phone leg.

## Never cut
Disclosure line, user approval before any AI-drafted or translated speech, scam shield, task limits and approvals, cost guards.

## Kill switch
If M0 fails by Sunday night: build type-to-speak via Bolna custom LLM endpoint (spike), make Call for me + WhatsApp the hero. If that fails by Monday: switch to Bhasha OPD.
