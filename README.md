# Awaaz — handover folder

Awaaz makes phone calls possible for people who can’t hear or speak: it speaks what you type in your own voice, captions replies, repeats clearly, and can make the whole call for you. Bolna Buildathon entry, deadline 31 October 2026.

**Claude Code: start with `CLAUDE.md`, then `tasks/PLAN.md` M0.**

## Contents
```
awaaz-handover/
├── CLAUDE.md                     # Instructions for Claude Code
├── README.md
├── docs/
│   ├── PRD.md                    # Product requirements v0.1 (markdown)
│   ├── PRD-ADDENDUM-v2.md        # Talk/hear profiles, call paths, WhatsApp, own number (wins over PRD)
│   ├── IMPLEMENTATION.md         # Technical source of truth
│   ├── PRD.pdf, PRD-ADDENDUM-v2.pdf, IMPLEMENTATION.pdf, UI-SCREENS.pdf
│   └── prd-and-tech-design.html  # Original PRD page
├── design/
│   ├── ui-prototype.html         # Clickable UI v2 (visual source of truth)
│   └── README.md                 # Screen → route → component map
├── specs/
│   ├── db/                       # 001_init.sql (schema, RLS, realtime, storage), seed.sql
│   ├── protocol/                 # App <-> API relay WebSocket events (markdown + JSON Schema)
│   ├── schemas/                  # JSON Schemas for LLM and Bolna outputs
│   ├── prompts/                  # Smart replies, Help me say, summary, scam check, WhatsApp intent, translation
│   ├── agents/                   # Bolna task agent prompt + functions
│   ├── data/                     # Presets, task templates, scam rules + eval set, voice commands, entity rules, phrases
│   ├── fixtures/                 # Fake callee scripts, Bolna and WhatsApp payloads, Plivo stream messages
│   └── messages/                 # Disclosure/keeper lines, WhatsApp templates
├── tasks/
│   ├── PLAN.md                   # Tickets M0–M7 with acceptance criteria
│   └── HUMAN-CHECKLIST.md        # KYC, accounts, testers: Amit’s tasks
└── env/                          # api.env.example, web.env.example
```

## How to use it
1. Create an empty repo `awaaz`, copy this folder’s contents into it, commit.
2. In Claude Code: *“Read CLAUDE.md and follow it. Start with tasks/PLAN.md M0.”*
3. In parallel, work through `tasks/HUMAN-CHECKLIST.md`; KYC and WhatsApp approval are the slowest items.

## Caveats
- Items marked **⚠️ VERIFY** are unconfirmed third-party details. Check them on day 1.
- Hindi and Marathi text needs native-speaker review; Hindi verb forms are gendered.
- All names, numbers and conversations are fictional.
