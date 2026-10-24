# Incoming calls, your own number, and the app question

Status: design, 24 October 2026. Nothing here is built yet. Facts marked **VERIFY** were not confirmed against live documentation.

## 1. The three situations

| | Situation | Who rings | Who answers |
|---|---|---|---|
| A | Someone calls the user's **Awaaz number** (a number we give them) | Awaaz line | An Awaaz agent, with the user watching in the app |
| B | Someone calls the user's **normal SIM number** | The user's phone | Nobody, unless calls are forwarded to the Awaaz number |
| C | The user is **already on a normal call** and wants Awaaz in it | — | Awaaz joins as a third party |

Outbound calls (the user calls someone) already work through the Awaaz line, and the caller sees the Awaaz number. Everything below is about inbound and about the user's own number.

## 2. Path A: an Awaaz number per user (inbound through Bolna)

### What Bolna gives us
- Numbers can be **bought in the Bolna dashboard** for India (Plivo 080/022, or Vobiz after KYC) at **$5 a month per number**, plus per-minute call charges. There is no purchase API in the docs: numbers are bought by hand, then attached to an agent. **VERIFY** whether an API exists.
- A number is linked to **one agent**; when someone dials it, that agent answers by itself (dashboard "Inbound Calling", or the Set Inbound Agent API).
- **VERIFY:** whether an agent whose LLM is a custom endpoint (our server) can be used for inbound, and whether the caller's number is available to us during the call (the execution record has `telephony_data.from_number`, but we need it at the first request).

### Flow

```mermaid
sequenceDiagram
  participant C as Caller
  participant B as Bolna agent (per user)
  participant S as Awaaz API
  participant U as User (app / WhatsApp)
  C->>B: dials Rafiq's Awaaz number
  B->>C: "You've reached Rafiq's line. An assistant helps him. One moment."
  C->>B: "Hello?"
  B->>S: POST /v1/llm/chat/completions  [system prompt carries [[awaaz:user=RAFIQ]]]
  S->>S: find or create the inbound RelaySession for that user
  S-->>U: push: "Incoming call from +91 98xxx" (+ WhatsApp)
  U->>S: opens the call, sees captions, types a reply
  S-->>B: streams the typed reply as the "LLM answer"
  B->>C: speaks it
  Note over S,U: no answer in about 25 s: the agent says "Rafiq can't take the call, leave a message"; the message is captioned and kept
```

### What we add
1. **One Bolna agent per user number**, created by our script when a number is assigned. Its system prompt carries `[[awaaz:user=<id>]]`, so the first request tells us whose line is ringing (same trick as `[[awaaz:call=<id>]]` for outbound). Its welcome message is the disclosure for inbound: "This is {name}'s line. {name} {disability_phrase}. An assistant reads out their replies."
2. **Inbound sessions**: `create_relay_call` gains an "inbound" mode (no number to dial, leg already live). The relay session, captions, typing, scam shield and smart replies are the same code as outbound.
3. **Alerting** (section 5) and **message taking**.
4. **DB**: `awaaz_numbers` gets `bolna_phone_number_id` and `bolna_agent_id`; `calls.direction = 'inbound'` already exists.

### Limits to be honest about
- Per-user numbers cost $5 a month each, so a real product needs a pricing model or pooled numbers. For the hackathon: **buy one or two numbers** and assign them to testers.
- Bolna wallet is about 471 units (roughly $5). A number needs a top-up.
- Spam callers will reach the user's agent too. Message taking and the scam shield matter more on inbound.

## 3. Path B: the user's own SIM number, no app, no number to buy

Every Indian carrier supports **call forwarding**. If the user forwards their SIM number to their Awaaz number:
- **When busy, unanswered or unreachable** (conditional forwarding): missed calls land on Awaaz, the agent takes the call or a message. The caller dialled the **real number** and never knows. This is the "missed-call forwarding" feature in the plan.
- **Always** (unconditional): every call goes to Awaaz and the user's phone never rings; the app is the whole interface. This suits a deaf user who cannot use a ringing phone anyway.

Standard codes (GSM; carrier-dependent, **VERIFY** per carrier): `*67*<number>#` busy, `*61*<number>#` unanswered, `*62*<number>#` unreachable, `*21*<number>#` always, `##002#` cancel. Jio uses `*401*<number>#` and `*402*...` style codes. A "Set up forwarding" screen should show the right code for the user's carrier with a copy button (iOS blocks `tel:` links containing `#` in some cases).

Trade-offs: the forwarded leg may use the user's own talk time or minutes; some plans bill forwarding; the original caller ID is normally preserved by the carrier (**VERIFY** that Bolna sees it).

## 4. Path C: Awaaz inside a normal call ("merge")

A normal SIM call can become a conference with a third participant: the Awaaz number. That keeps the user's real number as the caller ID and the user's carrier call as the main audio.

| Variant | How | Works on | Cost |
|---|---|---|---|
| **Manual merge** | User is on a call, taps **Add call**, dials their Awaaz number, taps **Merge** | Android and iPhone, no app | Zero development: we only show the instructions and the console |
| **Automatic merge** | A native Android app set as the **default phone app** (`InCallService`) places and merges the Awaaz call itself | Android only | A native app; Play Store restricts default-dialer apps |
| **iOS automatic** | Not possible: CallKit cannot merge or read audio, and iOS offers no equivalent | — | — |

Rules from the plan hold: we never read audio from the user's normal call (Android and iOS block it) and never spoof caller ID. The merge works only because Awaaz is **another participant** the user dials.

Technical notes: the Awaaz leg hears everyone in the conference (mixed), speaks to everyone, and can show captions of the other person to the user. With Bolna as the leg, the agent's interruption handling may be confused by two voices, so a short demo with the user silent is safest. Conference support depends on the carrier (VoLTE conference is common on Jio and Airtel).

**Recommended demo:** manual merge. It needs nothing but the console and a purchased number, and it shows "AI joins your normal call" convincingly.

## 5. How the user is alerted (the hard part for deaf users)

A ringing phone is useless to a deaf user. Alerts need to be **visual and tactile**, and redundant:

| Channel | Reliable when | Notes |
|---|---|---|
| **Web Push** (PWA) | App installed to the home screen, notifications allowed | Android Chrome: works, `requireInteraction` keeps it on screen, vibration pattern supported. iOS 16.4 and later: works only for an installed home-screen app, **no vibration pattern**, can be silenced by Focus modes |
| **WhatsApp message** | WhatsApp installed (almost everyone) | Familiar and reliable. The first message outside the 24-hour window must be a **template** (Meta approval, usually quick for a utility template) |
| **In-app** | App open | Flashing screen and full-screen "Incoming call" card |
| **Smartwatch / flashlight** | Native app only | Roadmap |

Escalation: push and WhatsApp at once; if nobody opens the call within about 25 seconds the agent switches to message taking.

## 6. Web app (PWA) or native app?

| Need | PWA | Native app |
|---|---|---|
| Live console, typing, captions, onboarding | Yes | Yes |
| Alerts for incoming calls | Push notification (can be missed or silenced) | **Full-screen incoming-call UI**: Android `CallStyle` notifications with a full-screen intent; iOS **CallKit** with a **PushKit VoIP push** (needs a paid Apple Developer account) |
| Wake from a killed or sleeping state | Not guaranteed | High-priority FCM / VoIP push |
| Strong vibration or flash patterns, watch haptics | Limited, none on iOS | Yes |
| Auto-merge into a normal call | No | Android only (default dialer) |
| Microphone for "My voice" | Yes, foreground | Yes, plus background routes |
| Distribution | A link, instant | App stores, review time |

**Recommendation**
1. **P0 (31 October): installable PWA plus WhatsApp.** Everything outbound works, inbound alerts go through Web Push and WhatsApp, message taking covers misses. Add an "Install Awaaz" prompt, since push on iOS needs it.
2. **P1: personal number with inbound relay**, the forwarding helper screen, and the manual-merge guide.
3. **P2 (roadmap, documented): a native Android app** (Kotlin): `InCallService` default dialer for automatic merge, `CallStyle` full-screen alerts, FCM high-priority push, flashlight and vibration patterns. A thin **Capacitor** shell around the existing web app is the cheapest first step: it can add native notifications while keeping one UI. **iOS** native adds CallKit incoming-call UI but cannot merge calls.

A PWA is therefore enough to *demonstrate and ship* the product; a native app is what makes incoming calls *feel like real calls* and enables automatic merge.

## 6b. Safety and legal

- The **disclosure** applies to inbound too (the per-user welcome message).
- Unconditional forwarding sends spam to the user; prefer conditional forwarding, plus the scam shield and a caller-number display.
- Recording: audio is not stored by default; message taking stores only the text transcript unless the user saves it.
- Indian numbers: Bolna's provider handles number KYC; we never display the user's own number as the caller ID of Awaaz-placed calls.

## 7. What to build and in what order

1. Buy **one number** in Bolna ($5), and ask Bolna support the **VERIFY** questions (custom LLM on inbound, caller number, purchase API).
2. `inbound` mode in the relay session; per-number agent script; first-request routing by user token.
3. Web Push (VAPID, `pywebpush`, a `push_subscriptions` table) and WhatsApp alert.
4. Message taking and the "missed call" row in history with the transcript.
5. "My number" screen: shows the number, forwarding codes with copy buttons, and the manual-merge guide.
6. Document the native Android app as the roadmap; no code before 31 October.

## 8. Questions for Bolna support
- Can an inbound agent use a custom LLM endpoint? Does the endpoint receive the caller's number?
- Is there an API to buy or release numbers? India numbers: lead time and KYC?
- How are conference calls (three parties) handled by the agent?
- Per-minute inbound pricing for India numbers.
