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

## 2026-10-24: Caption translation (bake-off)
8 call lines (6 Hindi, 2 Marathi to English): prices, times, dates, medicines, an OTP request; 27 entities. Engines: Sarvam `sarvam-translate:v1`, `gemini-3.5-flash-lite` plain, and the same with call context (contact notes plus "keep numbers as digits, keep medicine names in Latin").
- Entities kept: Sarvam 25/27, Gemini plain 26/27, Gemini with context 26/27 (two of the misses are scorer artefacts, "10 AM" vs "morning"). Median latency 0.72 / 0.84 / 0.84 s.
- The only real failure: Sarvam turned "तेलमा चालीस" into "Forty will be available in oil". Gemini kept "Telma 40" (with notes).
- Decision: translate captions with **Gemini plus call context** (contact notes, call type), Sarvam translate as fallback on error or quota. Original text is always shown with a translation. Hinglish is a display transliteration only, never a pivot for translation.
- Caveats: n=8, one entity trap; watch Gemini free-tier quota during live calls. The upstream error is speech recognition ("तेलमा"): mitigate with original text, low-confidence shading and ask-to-repeat.

## 2026-10-24: Typed text to speech, less friction
- Same language as the call (any script or spelling, e.g. Hinglish, Devanagari): converted to native script (Sarvam transliterate, numbers in spoken form) and spoken with no confirmation; the feed shows what was said and the original.
- Different language (English, Marathi in Latin letters, ...): translated (Gemini) and shown; one Enter sends. Keeps the rule that translated or drafted text is spoken only after the user confirms. Relaxing that rule is a product decision for Amit.
- Language detection: Gemini (`hindi_roman`/`marathi_roman`/`english`/`other`). Sarvam text-lid was unusable ("Theek hai" as Punjabi, "Thank you" as Tamil).
- Latency: prepare is about 1.4 s from a laptop (Sarvam transliterate 1.3 s, Gemini 1.0 s, in parallel). Over the 1.2 s budget, so the console prepares while the user types (700 ms pause) and caches by text. Re-measure on Render.

## 2026-10-24: Twilio upgrade skipped; Bolna is the live phone leg
- No Twilio voice upgrade. Live calls go through a Bolna agent whose custom LLM is our server (the spike path), so a call supports typed speech and captions. Own-voice, clear-voice and normal-audio modes are demonstrated in the browser callee simulator (Sarvam streaming), not on a phone line.
- The relay session talks to an `OtherLeg` (mock script, Bolna phone leg, browser simulator). Twilio Media Streams stays a documented future leg.
- WhatsApp (Twilio sandbox) gets a live-relay mode: "call <number>" starts a call; captions arrive as messages; text typed in the chat is spoken (same conversion and confirmation rules); "end" hangs up.
- Limits: Bolna trial only calls verified numbers; Twilio trial WhatsApp sandbox (join code per tester, daily message cap).

## 2026-10-24: WhatsApp via Meta Cloud API (Twilio trial cannot push messages)
- Twilio trial shared WhatsApp number: REST sends with a plain Body fail with 21654 "ContentSid Required"; the Content API is blocked on trial (20003). Only replies inside the inbound webhook (TwiML) work, which cannot push live captions.
- Decision: `WA_PROVIDER=meta_cloud` (WhatsApp Cloud API test number: free, free-form text within 24 h of the user's last message, up to 5 verified recipients). Adapter `providers/meta_wa.py`; webhook `GET/POST /v1/webhooks/wa/meta` (verify token, X-Hub-Signature-256).
- Twilio adapter stays for a paid account. Verified: bot logic end to end through the dev endpoint (`WA_PROVIDER=log`).

## 2026-10-24: Python 3.14 in production
- `requires-python = ">=3.12"`. The full API test suite (136 tests) passes on 3.12 and 3.14.6. Render defaults to 3.14.x and its build failed with the old 3.12-only pin (uv cannot download a managed Python there), so production runs the latest, `PYTHON_VERSION=3.14.8`.

## 2026-10-24: onboarding options that are built (and two that are not offered)
- Built: speak into the mic (Sarvam Saaras turns it into text, the user checks it, Awaaz says it), read aloud (browser voice, slower, exact words), vibration cues (Android and desktop Chrome; iOS Safari does not vibrate), after-call summary (Gemini, kept in `summaries`, can be listened to).
- **Own voice passed straight through** is not possible: the Bolna phone leg only speaks text we return, so there is no way to inject the user's audio. The mic option converts speech to text first. "Speak clearly for me" is the same flow, so the two options were merged.
- **Normal audio** (live call audio into the app) is not possible for the same reason: Awaaz never receives the other person's audio on a Bolna leg, only the transcript. Removed.
- **Sign language interpreter** needs a partner service; removed until there is one.
- Older profiles holding `clarity`, `sign` or `audio` still load; the app ignores them.

## 2026-10-25: live voice for people who can talk but not hear
- **Built:** the microphone streams to our server (`/v1/stt/ws`), which streams to Sarvam Saaras (WebSocket) and returns each finished sentence about 0.1 s after the speaker stops. The app sends it as `user.say` with source `voice`; Bolna speaks it with its text-to-speech. Captions of the other person come back as before. The user sees each sentence, can switch to "check before sending", and the scam shield, the "please hold" line and the disclosure still apply.
- **Sarvam facts learned:** the WebSocket accepts the key in the `api-subscription-key` header (the query-parameter form in their guide returns 403); audio goes in as `{"audio": {"data": base64, "encoding": "audio/wav", "sample_rate": 16000}}`; raw PCM needs `input_audio_codec=pcm_s16le`; `vad_signals=true` gives start and end of speech.
- **Not possible through Bolna:** passing the user's raw voice audio into the call. Bolna's agent is speech to text, our server, then text to speech; its docs show no audio input and no way to bridge a human in. Options for real voice: (1) a phone line we control (Twilio Voice SDK or Plivo browser calling, with the call audio forked to speech to text for captions; needs a paid, verified telephony account); (2) a consented clone of the user's voice used as Bolna's text-to-speech voice (ElevenLabs-type voices; rule 8 in CLAUDE.md applies).
- Read-aloud is paused while live voice is on, so the phone's speaker is not picked up by the microphone.

## 2026-10-25: making sending feel instant
Measured before the change (server time from "send" to the message appearing): native script 5 ms; Hindi in English letters 1.3 to 1.7 s; English or Marathi (needs translating) about 3 s. Causes: the receive loop handled one event at a time, so a slow message froze typing, pings and later messages; and a language model decided the language of every message typed in English letters.
Changes: (1) the app shows the message the moment it is sent (a dimmed "Sending…" bubble that the real one replaces); (2) the app asks the server to prepare the text 300 ms after typing stops (`say.prefetch`), so by the time send is pressed the work is done (183 to 475 ms measured, from 1.0 to 1.2 s); (3) obvious Hindi, Marathi or English is recognised from common words without the language model; (4) say, confirm and draft run in the background, in order, without blocking other events; (5) connections to Sarvam and Gemini are reused. Caption translation now arrives about 1.0 s after the caption and smart replies about 1.1 s after (were about 1.5 s and 3 s).
What remains: Sarvam transliteration with numbers spelled out takes about 1.2 s (0.66 s without spelling numbers out). Numbers are kept spelled out because a wrong number on a call is worse than a short wait.

## 2026-10-26: switching the caption language quickly
Bug: switching faster than a translation takes (about 1 s) lost the translation. The server dropped any translation that finished after the language had changed again, so the bubble kept showing the Hindi original, which looks like Marathi. Fix: every translation is kept and sent with its own language (the app files it under that language), translations are cached per line and language (switching back is instant), the same line is never translated twice into one language at the same time, and lines still waiting show "Translating to …" under the original. The caption language is now a one-tap list instead of a dropdown.

## 2026-10-26: fixes from real calls
Found by comparing Bolna's call transcripts with what the server stored for the calls placed between 17:49 and 18:05 UTC.
- **Typed messages not spoken.** Bolna asks our server what to say only right after the other person speaks, and we closed that request after one reply. A second message, sent while the other person waited silently, had nothing to carry it: it was never spoken and the other person hung up. The request now stays open after a reply (until they speak again, or 60 s with nothing to say), each reply ends with a full stop so Bolna speaks it at once, and if no request is open the app says the message will be said when they speak next (`say.queued`).
- **Their words missing from the chat.** Bolna sometimes sends the rest of a sentence after the first part was already shown as final; that part was dropped. Only the new part is now added as its own caption.
- **"Please hold" said too often.** It was allowed every 8 s and was said before almost every reply, once three times in a row. Now at most once every 20 s.
- **Scam openers not flagged.** The caller said the card would be blocked and named a bank but never asked for an OTP, so the shield stayed quiet by design. Openers (bank, police or courier impersonation, blocked card, account, SIM or electricity, KYC, lottery, refund, links) now raise a "this may be a scam" warning, confirmed by the language model when available and shown anyway when not; numbers are not read out from then on. A later code request shows its own warning.
- **Gendered Hindi.** The opening line said "Main sun nahi sakti" for a man. Lines are now gender-neutral by default ("Mujhe sunai nahi deta"); onboarding and Me ask how Awaaz should speak for the user, which picks masculine or feminine forms where Hindi needs them and is passed to drafts, smart replies and translations.
- **Live voice stopped after the first sentence.** Sarvam closed the stream (code 1011) and the server neither reopened it nor told the app. The server now reopens the stream (audio is queued meanwhile), and the app reconnects quietly if its connection drops.
- **Sign-in tokens in server logs.** WebSocket URLs carry the token; access logs now replace it (and the webhook secret) with ***.
