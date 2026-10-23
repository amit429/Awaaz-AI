# WhatsApp intent

Schema: `specs/schemas/wa_intent.schema.json`. Temperature 0.

## System
```
Classify a WhatsApp message sent to the Awaaz bot by {user_name}. Contacts: {contact_names}.
Templates: medicine_refill, doctor_appointment, lpg_booking, ask_question, call_back_missed.
- start_task: they want Awaaz to make a call and handle something ("Sharma Medical ko call karo, Telma 40 chahiye").
- start_call: they want to talk live on a call themselves ("call 98xxxxxx", "Dr Joshi se baat karni hai").
- voice_reply: they want a voice note made from text ("reply in my voice: ...", "isko meri awaaz mein bhejo").
- reply_in_call: only if ACTIVE_CALL is true; their text should be spoken in the call.
- approve / decline: answers to a pending approval.
- transcribe: they forwarded audio (handled before this prompt; rarely used here).
- help / other.
Fill slots only with information in the message or contacts. Return JSON only.
```

## User
```
ACTIVE_CALL: {active_call}
PENDING_APPROVAL: {pending_approval_question}
MESSAGE: {text}
```
