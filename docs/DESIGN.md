# Interface design

Built with Tailwind CSS v4 and shadcn/ui (new-york style, Radix primitives, lucide icons). This replaces the earlier "port the prototype" approach; the prototype remains the reference for the call screen's content, not its styling.

## Principles
- **Two voices.** Their words are cool, quiet glass on deep ink. Your words are marigold. Numbers, prices and times in their captions get a marigold chip. This one idea runs through the call screen, the transcript, and the login demo.
- **Built for the audience.** Many users are older, have low literacy or read Devanagari. Large touch targets (44px and up), high contrast, no meaning carried by colour alone, plain sentence-case copy, and a "Larger text" setting (scales the root font size).
- **Spend boldness once.** The login hero types a short captioned call on its own. Everything else stays plain: one list card per section with divided rows, not stacks of cards.

## Tokens
| | Light | Dark |
|---|---|---|
| Background | cool paper `oklch(0.975 0.004 270)` | deep ink `oklch(0.17 0.035 270)` |
| Primary | ink `oklch(0.26 0.06 270)` | marigold `oklch(0.83 0.15 75)` |
| Accent (your voice) | marigold `oklch(0.82 0.15 75)` | same |
| Danger | `oklch(0.58 0.22 27)` | `oklch(0.68 0.2 25)` |
| Live | `oklch(0.62 0.17 150)` | `oklch(0.75 0.17 150)` |

Theme follows the system (class strategy via `next-themes`); the live call screen is always dark.

## Type
Atkinson Hyperlegible Next for the interface (made for readability), Bricolage Grotesque for headings, Noto Sans Devanagari for Hindi and Marathi. Scale: 14 / 16 / 18 / 20 body and captions, 24 to 48 headings. Captions are 20px.

## Structure
Phones: one column with a bottom tab bar (Calls, Contacts, Me). Wider screens: the same column under a top bar. The call screen is full height with a dock for typing and four tools (Phrases, Keypad, Ask again, End).

## Languages
- The app is available in 12 languages: English, Hindi, Hinglish (Hindi in English letters), Marathi, Bengali, Tamil, Telugu, Kannada, Gujarati, Punjabi, Malayalam, Odia. The first onboarding step is the language picker; it can be changed any time in Me (and on the login screen).
- Strings live in `apps/web/src/i18n/locales/en.json` and are loaded per language on demand. The other 11 files are machine translations made with `scripts/translate_locales.py` and **need native-speaker review before launch**. Run the script again after adding English strings.
- Live captions arrive at once in the language the other person speaks; the translation follows (`caption.translation`) with the original underneath. The caption language can be switched during the call (`read.set`); the last 5 captions are translated again.
- Typing: any Indian script works with the phone keyboard. Text in another script than the call's is translated and confirmed once. People typing English letters see a suggestion in their own script.
- The other person's language comes from the contact (or the "They speak" choice when starting a call).
