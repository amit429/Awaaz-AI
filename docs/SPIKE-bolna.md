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

## Call 2 (16-line script, Sarvam saaras:v4 hi, endpointing 1200 ms), 2026-10-24
Call ran 4 min 20 s before the callee hung up; lines L12-L16 were not reached (the one person was both shopkeeper and typist, about 20-30 s per exchange). Cost 3.82 wallet units.

### Fixed since call 1
- Every typed reply spoken exactly once, in order (11 assistant lines in Bolna's transcript: welcome plus 10 replies). Keeper line fired 3 times, only after 5 s of typing, followed by the reply in the same response. No "are you still there".
- 34 requests for 10 turns (fragments); older requests are cancelled by Bolna before our supersede check, so no reply attached to a stale request.
- Captions grow inside one bubble as fragments arrive (up to 7 fragments per turn), which reads like live captioning.

### Recognition on real phone audio (the serious finding)
| Line | Said | Captured | Verdict |
|---|---|---|---|
| L02 | Telma chalis | तिलमा चालीस | name wrong, number right |
| L03 | chaar sau bees rupaye (420) | "कुल्लू। चार। परसों। ₹20" | **price wrong** |
| L04 | chhah baje (6) | "4 बजे" | **time wrong**; 30 and long sentence ok |
| L06 | flat chaar sau do (402) | dropped | **number lost** |
| L07 | 9876543210 digit by digit | "नौ आठ सात 6 बाकी 4 तीन दो 1010" | **garbled** |
| L09 | English "...seven pm" | "ओके योर ऑर्डर इज कन्फर्मड इट विल रीच पी एम" | English in Devanagari, "seven" lost |
| L10 | barah taareekh, das baje | "बराबर तरीक", "10 बजे" | date wrong, time right |
| L11 | paanch sau (500) | ₹500 | ok |
Numeric facts correct: about 5 of 12. The synthetic bake-off (clean TTS audio) was far too optimistic about numbers. This is the main product risk: a wrong price or time shown to a deaf user.

### Next experiment
Same script, same agent, only the transcriber swapped (Deepgram nova-3 hi/multi vs Sarvam saaras:v4), with scripted instant typist replies so the run is fast and measures recognition only.
