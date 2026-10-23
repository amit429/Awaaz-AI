# Awaaz — PRD addendum v2

23 October 2026. Adds the decisions made after PRD v0.1 and the v2 UI prototype. Where this addendum and `PRD.md` differ, this addendum wins.

## 1. Talk and hear are separate, configurable choices

Every user sets **how I talk** and **how I hear** independently, picks a starting preset, and can override per contact and switch during a call.

### How I talk

| Option | Who it serves | Phase |
|---|---|---|
| My own voice | Deaf people who speak; hard-of-hearing users | P0 (in-app audio) |
| Type, Awaaz speaks (cloned or stock voice) | People who can’t speak; deaf people who prefer typing | P0 |
| Phrases and smart replies | Everyone typing | P0 |
| Help me say it (a few words → one polite sentence, approved before speaking) | Slow typists, low literacy, anxiety | P0 |
| Speak clearly for me (user speaks; Awaaz re-says it clearly) | Unclear speech after stroke, deaf speech, dysarthria | P1 |
| Sign language via human interpreter | ISL users | P2 (partner) |

### How I hear

| Option | Phase |
|---|---|
| Live captions with highlighted numbers, dates, prices | P0 |
| Normal audio (speech-boosted, in-app) | P0 |
| Translate for me (read and type in my language) | P0 |
| Spoken summary after the call | P0 |
| Clear voice (each sentence repeated slower and louder, only to me) | P0 in-app, P1 on a phone leg |
| Vibration cues (they started / stopped talking) | P1 |

### Presets

| Preset | Talk (default first) | Hear |
|---|---|---|
| I can’t speak | Type, phrases, help me say | Normal audio, summary |
| Deaf, I can speak | My voice, help me say, type | Captions, vibration, summary |
| Deaf, I prefer typing | Type, phrases, help me say | Captions, vibration, translate |
| Hard of hearing | My voice | Clear voice, normal audio, summary |
| My speech is unclear | Speak clearly, my voice, phrases | Normal audio, summary |
| I don’t read much | My voice, phrases | Clear voice, summary |

## 2. Call paths

| Situation | Path | Caller sees | Phase |
|---|---|---|---|
| User calls any number | Awaaz line (cloud call) | Awaaz number | P0 |
| Someone calls the user’s Awaaz number | Rings the app; message taking | — | P1 |
| Normal calls on the user’s SIM | Awaaz joins as a third line and merges (native Android default phone app; manual on iPhone) | User’s own number | P2 |
| Missed SIM calls | Carrier forwarding to the Awaaz number → captioned message | — | P1 |
| WhatsApp chats and voice notes | Awaaz bot | — | P0 |
| WhatsApp calls with Awaaz | WhatsApp Business Calling API; “call me via Awaaz” links | — | P2 |
| Personal WhatsApp calls between friends | Not accessible to any app; use the Awaaz link, face to face mode on a second device, or built-in phone captions | — | Not possible |
| In person | Face to face split screen | — | P1 |
| Phone menus | Keypad with spoken options listed; Call for me | — | P0 |
| Video calls | Desktop captions from tab audio | — | P2 |
| Emergency | SOS card + family alert; no automated 112 | — | P1 |

**Caller ID:** Awaaz never displays the user’s personal number on calls it places. Indian rules prohibit CLI spoofing. Keeping the user’s own number is only possible through the merge path.

**Call audio access:** apps cannot read normal phone call audio on Android or iOS. The merge path works because Awaaz is a separate participant on the call.

## 3. WhatsApp bot (P0)

- Start calls and tasks by text or voice note (“Sharma Medical ko call karo, Telma 40 chahiye”).
- Approve task decisions with buttons.
- Receive call summaries and task results, including voice notes.
- Forward any voice note to get it as text.
- Type a reply and get a voice note in the user’s own voice to forward.
- P1: live relay inside the chat (captions as messages, replies by text).

## 4. Updated scope for 31 October

P0: Awaaz line outbound with Type, Phrases/Smart replies, Help me say and My voice; captions, normal audio, translate, clear voice (in-app), summaries; profiles and presets; Call for me (gas, medicine); scam shield; WhatsApp bot (tasks, approvals, summaries, voice notes).

P1: Speak clearly for me, voice cloning, incoming calls on personal numbers, missed-call forwarding, live relay in WhatsApp chat, face to face, vibration cues, SOS.

P2: Android merge app, WhatsApp calling, sign language interpreter partners, desktop captions, accessible business lines.

## 5. Additional success metrics

- Share of calls using each talk mode and hear mode (validates the configurable design).
- Mid-call mode switches per call.
- WhatsApp-only users vs app users.
- Voice notes transcribed and voice-note replies sent per week.
