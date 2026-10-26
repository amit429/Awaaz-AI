# Relay session protocol (app <-> API)

Transport: one WebSocket per call, `wss://<api>/v1/relay/{session_id}?token=<supabase_jwt>`.

- **Text frames** carry JSON events with a `t` field (type). Schema: `relay-events.schema.json`.
- **Binary frames** carry audio. Byte 0 is the channel id, the rest is 16-bit little-endian PCM, mono, 16 kHz, 20 ms (640 bytes):
  - `0x01` app → server: user microphone (only in talk modes `voice` or `clarity`)
  - `0x02` server → app: other person audio (hear mode `audio`)
  - `0x03` server → app: clear-voice re-speak (hear mode `clear`); the app ducks channel 0x02 by 12 dB while 0x03 plays
  - `0x04` server → app: preview of the user’s own TTS (optional, for “hear what they hear”)

## Server → app

| t | Fields | When |
|---|---|---|
| `call.state` | `state` (`ringing`, `connected`, `ended`, `failed`), `reason?`, `elapsed_ms` | Call progress |
| `caption.partial` | `turn`, `text` | Interim transcript (≤ 5/s) |
| `caption.final` | `turn`, `text`, `lang`, `translated?`, `confidence`, `entities[]` | End of the other person’s turn |
| `you.final` | `turn`, `text`, `source`, `original?` | A user turn was spoken or transcribed (typed, reply, phrase, draft, voice, clarity). `original` is what the user typed when it was converted (Hinglish to native script) |
| `suggestions` | `turn`, `items[3]` | Smart replies for the latest turn |
| `draft.ready` | `draft_id`, `text`, `from_words`, `changed_meaning_risk?` | Help me say result; shown to the user, spoken only after they send `user.say` with source `draft` |
| `say.preview` | `preview_id`, `text`, `original` | Translation shown before speaking |
| `say.blocked` | `reason` (`scam_digits`, `empty`, `too_long`) | A say was refused |
| `say.queued` | — | The phone line is not listening right now (Bolna only asks after the other person speaks): the message is said when they speak next |
| `scam.warning` | `reason`, `turn` | OTP/PIN/CVV/remote-app request detected |
| `ivr.menu` | `options[]` (`digit`, `label`) | Phone menu parsed from captions |
| `keeper.spoken` | — | “Please hold” line was said to the other person |
| `respeak.started` / `respeak.ended` | `turn`, `rate` | Clear voice playback |
| `mode.updated` | `talk_modes[]`, `hear_modes[]` | After `mode.set` |
| `caption.translation` | `turn`, `lang`, `text` | The caption of `turn` in the reading language; follows `caption.final` (captions are never held back for translation) |
| `read.updated` | `lang` | After `read.set` |
| `error` | `code`, `message` | Recoverable errors |

## App → server

| t | Fields | Effect |
|---|---|---|
| `user.typing` | — | Resets keeper timer |
| `user.say` | `text`, `source` (`typed`, `reply`, `phrase`, `draft`, `voice`), `preview_id?` | Speak to the other person |
| `say.confirm` | `preview_id` | Confirm a translated preview |
| `draft.request` | `words` | Help me say |
| `user.ask_repeat` | — | Politely ask the other person to repeat |
| `user.respeak` | `turn?`, `rate?` | Clear voice: repeat to me (default last turn) |
| `user.dtmf` | `digits` | Send tones |
| `mode.set` | `talk_modes?`, `hear_modes?` | Switch mid-call |
| `read.set` | `lang` | Change the caption language mid-call; the last 5 captions are translated again |
| `call.end` | — | Hang up |
| `ping` | — | Keepalive every 15 s |

## Ordering and recovery

- `turn` numbers are monotonically increasing per call and match `turns.seq`.
- On reconnect, the app loads `turns` for the call from Supabase, then resumes events. The server buffers the last 20 events per session and replays any with `turn` greater than the app’s `last_turn` query parameter.
