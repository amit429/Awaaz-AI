# Things only Amit can do

Do these alongside the build. Paste keys into `.env` files, never into git.

## Day 1 (Sat 24 Oct), start the slow ones first
- [ ] **Plivo:** sign up, enable Indian outbound calling, complete KYC, buy one number. Ask support to confirm bidirectional audio streaming is enabled for India and send a sample of the stream messages.
- [ ] **Exotel:** sign up, start KYC, start WhatsApp Business onboarding, submit `welcome_v1` and `approval_v1` templates.
- [ ] **Twilio:** create an account and join the WhatsApp sandbox from your phone (demo fallback).
- [ ] **Bolna:** API key, confirm credits; connect your Deepgram, Sarvam and Cartesia accounts on the Providers page.
- [ ] **Keys:** Deepgram, Sarvam, Cartesia, LLM. Ask Kalpa Labs whether a direct TTS API exists outside Bolna.
- [ ] **Platform:** Supabase project (Mumbai region if offered), Vercel, Render (Starter instance), GitHub repo.
- [ ] Ask Bolna support how custom LLM endpoints handle slow responses (the kill-switch path).

## Day 2–3
- [ ] Create the Bolna task agents (`task-hi`, `task-mr`, `task-en`) from `specs/agents/task_agent.md`.
- [ ] Recruit testers: contact a Pune deaf association, a laryngectomee club or ENT/audiology clinic, and older relatives with hearing loss. Get written consent for test calls and recordings.
- [ ] Book a native Hindi and Marathi reviewer (1–2 hours) for disclosure lines, templates and prompts.
- [ ] Line up two friendly “other side” numbers (a pharmacy owner, a clinic receptionist) who agree to receive test calls.

## Day 4–6
- [ ] Record stock voice samples; if a tester agrees, collect old voice notes for cloning (with the consent sentence).
- [ ] Run three real calls per language with testers; note hang-ups and caption errors.

## Day 7–8
- [ ] Record the demo video (script in `docs/PRD.md`).
- [ ] Submit on the Buildathon site before noon on 31 Oct: name, 200-character line, live link, video.
