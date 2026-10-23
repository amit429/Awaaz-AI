# Decisions log

## 2026-10-23: Twilio replaces Plivo, Exotel and Kalpa
- Plivo India numbers and domestic calling are for India-registered businesses only (GST, incorporation or Udyam). India does not support Verified Caller ID. An individual cannot get a number.
- Exotel WhatsApp Business onboarding is slow (KYC, Meta verification, templates).
- Decision: Twilio for voice (Media Streams, trial calls to verified numbers) and the WhatsApp sandbox. Clear voice uses Cartesia with speed control instead of Kalpa.
- Unverified: caller ID shown on Indian destinations; DTMF during a Media Stream (needs a call update); sandbox interactive buttons; Twilio upgrade cost for calling unverified numbers.
- Tunnel: ngrok with one static domain for webhooks and media WebSockets.

## 2026-10-23: Supabase project
- Project `awaaz` (ref `gxqbsjemdgnekigfjdgv`, ap-south-1) in amit429's Org, created via MCP.
- Migrations applied: `0001_init` (specs/db/001_init.sql) and `0002_pin_function_search_path`.
- `audit_log`, `jobs`, `wa_users` have RLS and no policies on purpose (service role only).
- `seed.sql` not applied yet: stock voices need real Cartesia/Sarvam voice ids. The `kalpa` and `plivo` rows are dropped.
- Still needed from Amit: `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_JWT_SECRET` (dashboard, Project Settings, API) in `apps/api/.env`.
