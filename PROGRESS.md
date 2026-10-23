# Progress

## Done
- M1-01 repo created from handover; provider decision recorded in `docs/DECISIONS.md`
- M1-03 API skeleton (settings, CORS, health)
- M0-02 mu-law and resampling with tests (relay/audio.py)
- M1-02 Supabase project `awaaz` created, schema migrated (17 tables, RLS, realtime, buckets)
- M1-04 provider interfaces + scripted fake callee, TTS/LLM/telephony mocks (tests)
- Speech bake-off done: Sarvam alone meets latency and language needs (docs/DECISIONS.md)
- M1-03 JWT auth (JWKS, optional HS256 fallback) with tests

## Doing
- M1-01 monorepo layout

## Blocked
- Live keys (Twilio, Deepgram, Cartesia, Sarvam, Bolna, LLM, Supabase) not yet provided; mock and simulator first

## Unverified
- See `docs/DECISIONS.md`
- Bolna spike: first real call done (see docs/SPIKE-bolna.md); typed speech and captions work, turn fragmentation and unauthorised idle prompts are open problems
