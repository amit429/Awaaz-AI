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
- Dev tunnel: ngrok static domain ruby-doorway-numbness.ngrok-free.dev (run: ngrok http --url=ruby-doorway-numbness.ngrok-free.dev 8000). Webhook URLs in Twilio point here for local dev.
- Twilio trial uses a shared US number (+1 737 xxx 8034). Unverified: voice webhook and Media Streams on a shared number; trial preamble ("press a key") for the callee; whether Indian phones answer a US caller ID. Test in M0-01, then decide on upgrading.
- WhatsApp sandbox: Twilio shared trial number +1 737 250 8034, join code `twilio-trial`. `TWILIO_WA_FROM=whatsapp:+17372508034`. Voice and WhatsApp share this one number. Each tester must send the join message (72-hour join window).

## 2026-10-24: Models (benchmarked)
- LLM: `gemini-3.5-flash-lite` (smart-replies JSON task, p50 1.04 s; `gemini-3.1-flash-lite` p50 1.15 s is the fallback; full Flash models 2.3-2.6 s, too slow; `gemini-2.5-flash-lite` unavailable to new accounts).
- Captions hi/en: Deepgram `flux-general-multi` (connects on /v2/listen). `flux-general-hi` does not exist. Marathi: Deepgram `nova-3` (lists `mr`) or Sarvam Saaras; decide after a Marathi test.
- TTS: Cartesia `sonic-3`. Sarvam credits: ~$100; Bolna wallet ~471 (about $5).
- Telephony: Bolna as the phone line first (custom LLM endpoint spike). Twilio media-stream path kept as full-feature fallback; Twilio voice from the shared trial number is blocked by the trial (see above).

## 2026-10-24: Speech provider = Sarvam only (bake-off)
Principle: one provider per function unless a measured requirement forces a second. Sponsor status is not a reason.
Method: 11 phone-quality clips (Gemini TTS voices, downsampled to 8 kHz mu-law with light noise; hi 5, mr 5, en 1) and 3 sentences per language for TTS. Small sample; real phone audio still to be tested.

| Requirement | Sarvam | Deepgram | Cartesia |
|---|---|---|---|
| STT hi/mr/en content | accurate; writes digits and ₹ (`₹420`, `6 बजे`), good for entity chips | accurate (nova-3 incl. Marathi); Flux-multi has no Marathi, ended turns early at commas in English | n/a |
| STT streaming latency | transcript 0.34-0.52 s after speech ends; START/END_SPEECH events; 8 kHz input | Flux EOT 0.49 s (hi) | n/a |
| TTS first audio | **0.19-0.24 s streaming WS** (mulaw 8 kHz output, pace 0.5-2.0); REST is slow (1.2-1.7 s) | n/a | 0.14-0.31 s |
| TTS Marathi intelligibility | good (error 0.22) | n/a | **poor** (error 0.95, garbled) |
| Voice cloning | docs list a voice-cloning API (to verify) | n/a | yes (Pro plan) |

Decision: **Sarvam for STT, TTS and translation.** Deepgram and Cartesia are not used (keys stay in `.env`, unused). Revisit only if real phone audio shows Sarvam failing a requirement.
Implementation notes: STT `wss://api.sarvam.ai/speech-to-text/ws` (`saaras:v3`, `vad_signals=true`, base64 JSON audio, `flush`); TTS `wss://api.sarvam.ai/text-to-speech/ws?model=bulbul:v3` (config then text then flush; `output_audio_codec=mulaw`).
Clear voice: Bulbul `pace` 0.5-2.0 replaces Cartesia speed control. Voice cloning (P1): check Sarvam's cloning API before touching Cartesia.
