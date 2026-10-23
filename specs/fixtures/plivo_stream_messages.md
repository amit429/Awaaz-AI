# Plivo audio stream messages (assumed; ⚠️ VERIFY against Plivo docs)

Answer XML (bidirectional, μ-law 8 kHz):
```xml
<Response>
  <Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-mulaw;rate=8000">wss://API_HOST/v1/media/plivo/LEG_ID?s=SECRET</Stream>
</Response>
```
Inbound (Plivo → API):
```json
{ "event": "start", "start": { "callId": "…", "streamId": "…" } }
{ "event": "media", "media": { "payload": "<base64 mu-law 20ms>", "timestamp": "…" } }
{ "event": "stop" }
```
Outbound (API → Plivo):
```json
{ "event": "playAudio", "media": { "contentType": "audio/x-mulaw", "sampleRate": 8000, "payload": "<base64>" } }
{ "event": "clearAudio" }
```
