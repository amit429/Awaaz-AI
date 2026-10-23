# Call summary

Schema: `specs/schemas/call_summary.schema.json`. Temperature 0.1.

## System
```
Summarise a phone call made through Awaaz for {user_name}. Read language: {read_lang}. Today: {today_iso}, timezone Asia/Kolkata.
- agreed: what both sides agreed, in plain English, short.
- facts: every price, time, date, phone number, address or reference number mentioned, exactly as said, with ISO values where possible.
- next_steps: what {user_name} needs to do.
- summary_read_lang: 2–4 simple sentences in {read_lang} for a voice note. Repeat important numbers and dates.
- reminders: at most 3, only for dated actions (e.g. the evening before an appointment).
Copy numbers exactly. Never guess missing information. Return JSON only.
```

## User
```
CONTACT: {contact_name}
TRANSCRIPT (speaker: text):
{turns}
```
