# Design hand-off

`ui-prototype.html` (v2) is the visual source of truth. Open it in a browser and use the top tabs, or `#call`, `#profile`, `#clear`, `#task`, `#whatsapp`, `#number`, `#face`, `#integrations`.

## Porting rules
- Copy the `:root` token blocks (light, dark media query, `[data-theme="dark"]`) into `apps/web/src/styles/tokens.css` unchanged; copy the rest into `app.css` and keep class names.
- Fonts: Geist (UI), Noto Sans Devanagari (Indian scripts), Atkinson Hyperlegible (easy-reading option). Load from Google Fonts.
- Icons: the inline SVG sprite at the top of `<body>`. Move it into `src/components/Icons.tsx` (one component, `name` prop). No emoji in UI.
- The call screen is always dark. Everything else follows the system theme.
- Prototype JavaScript is demo logic only; replace with the relay WebSocket client and Supabase data.

## Screen → route → components
| Prototype | Route | Components |
|---|---|---|
| Live call → Home | `/` | `QuickActions`, `ContactRow`, `RecentRow`, `TabBar` |
| Live call → call screen | `/call/:sessionId` | `CallBar`, `HearToggles`, `Feed` (`TheirBubble`, `YouBubble`, `Note`, `DraftCard`), `Replies`, `Dock` (`TalkModeSwitch`, `Composer`, `MicButton`, `HelpComposer`), `ToolsRow`, `Sheet` (phrases, keypad), `ScamAlert` |
| How I talk and hear | `/me/profile` | `PresetChips`, `OptionCard`, `LanguageSelects`, `Switch`, `ProfileSummary`, `CallPreview` |
| Clear voice | `/call/:sessionId` (hear mode `clear`) | `BigCaption`, `RoundControl` (Slower, Repeat, Louder) |
| Clear voice → after call | `/calls/:id` | `VoiceNote`, `FactRow`, reminders |
| Call for me | `/tasks`, `/tasks/new/:template`, `/tasks/:id` | `TaskTile`, `LimitRow`, `ProgressSteps`, `ApprovalCard`, `ResultCard` |
| WhatsApp | (WhatsApp, not the app) | Message formats in `specs/messages` |
| My own number | `/me/number` (P1/P2) | Settings rows; Android merge is P2 native |
| Face to face | `/face` (P1) | `SplitScreen` |
| Integrations | (documentation only) | — |
| Dev callee simulator | `/dev/callee/:sessionId` | Mic + speaker, minimal UI (dev only) |
