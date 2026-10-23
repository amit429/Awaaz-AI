# Spike: Bolna as the phone line (custom LLM endpoint)

Date: 2026-10-24. One real call to a verified number (~2 min). Agent: Sarvam saaras:v4 (hi) + Sarvam bulbul:v3 voice, custom LLM = our `/v1/llm`.

## What worked
- Bolna default number shows an Indian caller ID (+91 80 3573 xxxx). A phone spam filter blocked the first attempt; unblocking fixed it.
- Disclosure line spoken as the welcome message.
- Callee speech reached our endpoint as text (captions) and typed replies were spoken back (they appear as `assistant:` turns in Bolna's transcript).
- Cost: total 2.18 wallet units for the call (transcriber 1.21, synthesizer 0.97, platform and LLM 0).
- Trial accounts can only call numbers verified in Settings, Verified Phone Numbers.

## Problems (design-relevant)
1. **Fragmented turns.** Bolna (endpointing 500 ms) splits one sentence into several user turns, each calling our endpoint. We cannot tell a finished turn from a fragment, so typed replies attach to the wrong fragment and the wait/hold logic fires repeatedly.
2. **Speech we did not authorise.** After our "Ek minute, please hold" fallback, Bolna itself said "Hey, are you still there" (its idle prompt). Violates rule 2 (nothing spoken without a user action, except disclosure and keeper). Disabling it is unverified.
3. **Language lock.** Transcriber is fixed to Hindi; English speech came back in Devanagari ("आई विल रीड"). Needs auto language or per-call language.
4. **Number accuracy.** Caption showed "₹120" and "₹30" where the callee script said "चार सौ बीस" (420): to confirm with the speaker. Numbers are safety-critical.
5. **No raw audio.** Own-voice, clear voice, normal audio, hold tone, audio-level digit blocking are impossible on this path.
6. No precise latency measured (typed replies were queued by hand).

## Verdict
Bolna is a viable phone line for Call for me. As the live relay it covers basic typed speech plus captions but not the product rules or the non-typing modes. The full relay needs a leg we control (Twilio Media Streams + Sarvam streaming STT/TTS), which needs a Twilio upgrade.
