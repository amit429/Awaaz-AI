# Progress

## Done
- M1-01 repo created from handover; provider decision recorded in `docs/DECISIONS.md`
- M1-03 API skeleton (settings, CORS, health)
- M0-02 mu-law and resampling with tests (relay/audio.py)
- M1-02 Supabase project `awaaz` created, schema migrated (17 tables, RLS, realtime, buckets)
- M1-04 provider interfaces + scripted fake callee, TTS/LLM/telephony mocks (tests)
- Speech bake-off done: Sarvam alone meets latency and language needs (docs/DECISIONS.md)
- M2-05 keeper timer (relay/keeper.py, shared with the dev bridge), M2-03 disclosure lines, M2-01 profile resolution, M2-04 entities, all with tests
- M2-01/02/03 relay core (mock): POST /v1/calls, WS /v1/relay/{id} with JWT, RelaySession (disclosure, say, captions with entities, keeper, ask again, mode.set, end, reconnect replay, scam digit block hook), in-memory store, contract tests against relay-events.schema.json
- Typed speech in the relay: same-language converted and spoken, translations need say.confirm; dev-only /v1/dev/token
- Web app shell (Vite PWA, prototype tokens and icons) with Home and live Call screens wired to the relay; reducer tests (vitest). Smoke test against the live API: Hinglish send to spoken 1.7 s, English preview 3.3 s (to optimise with prepare-while-typing)
- Telephony decision: Twilio upgrade skipped; Bolna is the live phone leg (BolnaLeg, per-call routing by call-id token, status webhook). WhatsApp live relay on the Twilio sandbox (bot, webhook with secret and signature, dev endpoints). 92 API tests
- WhatsApp: Twilio trial cannot push free-form messages (21654); switched to Meta Cloud API adapter (needs Meta app setup: token, phone id, app secret, verify token)
- Web app screens: onboarding (2 steps), Me (how I talk and hear, easy font), Phrases, Contacts (add, edit, delete, call), Home (favourites, recents, practice calls), call detail with transcript. Backed by the settings API on Supabase. 12 web tests, 114 API tests
- Sign in with Google or email and password (Supabase), session gating, sign out; real Supabase tokens verified by the API (ES256 JWKS). Needs Google provider and URL config in the Supabase dashboard
- Help me say it (draft shown, spoken only after Say it); architecture for incoming calls, own number, merge and app choice written down in docs/ARCHITECTURE-incoming.md (design only)
- Deployed: API on Render free plan (Singapore, Python 3.14.8, https://awaaz-api-jv6d.onrender.com), web on Vercel (https://awaaz-web-amit-personal-projects.vercel.app), Supabase keep-alive ping every 10 min (pg_cron), production Bolna relay agent and model registered. One-call-at-a-time and daily-minutes guards. Dev endpoints return 404 in production
- Scam shield (rules from specs, zero missed requests on scam_eval.csv, LLM second opinion, warning, digit block, scam_events) and smart replies (Gemini, cancelled when stale); scam alert on the call screen. 128 API tests, 14 web tests
- Disclosure uses the name "Friend" until onboarding stores a profile (M1-06)
- M1-03 JWT auth (JWKS, optional HS256 fallback) with tests

## Doing
- M1-01 monorepo layout

## Blocked
- Live keys (Twilio, Deepgram, Cartesia, Sarvam, Bolna, LLM, Supabase) not yet provided; mock and simulator first

## Unverified
- See `docs/DECISIONS.md`
- Bolna spike: first real call done (see docs/SPIKE-bolna.md); typed speech and captions work, turn fragmentation and unauthorised idle prompts are open problems

## Unverified / limited (2026-10-24)
- Twilio trial: shared number cannot be used for live voice; upgrade needed (voice from +1 737 number to Indian phones, caller ID spam filtering untested).
- Bolna trial: only calls verified numbers.
- Number recognition on real phone audio with Sarvam (via Bolna) is poor; Deepgram not measured on a comparable run.
- Gemini free-tier quota under live load.
- Prepare-before-speak latency about 1.4 s from a laptop; re-measure on Render.
