# Fixtures

- `callee_*.json`: scripts for the mock fake callee. Each line is spoken after the user’s next turn; `repeat_on` patterns make it repeat the current line.
- `bolna_task_result.json`: assumed Bolna webhook payload for a completed task (⚠️ VERIFY shape; replace with a real scrubbed payload when available).
- `wa_*.json`: normalised inbound WhatsApp messages (provider adapters convert raw payloads into this shape).
- `plivo_stream_messages.md`: assumed Plivo audio stream messages (⚠️ VERIFY).
All data is fictional.
