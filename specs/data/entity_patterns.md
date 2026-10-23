# Entity extraction rules (captions)

Run on every final caption. Normalise Devanagari digits (०-९ → 0-9) first. Return spans for highlighting.

| Type | Patterns (examples) |
|---|---|
| money | `₹\s?\d[\d,]*`, `\d[\d,]*\s?(rs|rupees|rupaye|रुपये|रुपए)` |
| time | `\d{1,2}(:\d{2})?\s?(am|pm|baje|बजे|वाजता)`, `(सुबह|शाम|दोपहर|रात|सकाळी|संध्याकाळी)\s?\d{1,2}\s?(बजे|वाजता)?`, Hindi/Marathi number words + बजे/वाजता (`नौ`, `नऊ`, `दस`, `बारा`…) |
| date | `\d{1,2}\s?(tarikh|तारीख|nov|november|नवंबर|नोव्हेंबर…)`, weekday names in hi/mr/en (`शुक्रवार`, `शुक्रवारी`, `friday`), `kal`/`कल`/`उद्या`, `parso` |
| phone | `(\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}`, landlines `0\d{2,4}[\s-]?\d{6,8}` |
| quantity | `\d+\s?(goli|गोली|tablet|patta|पत्ता|strip|kg|litre)` |
| otp_request | from scam rules |

Unit test cases:
- “हाँ, मिल जाएगी। ₹420 होंगे, शाम 6 बजे तक तैयार।” → money ₹420; time शाम 6 बजे
- “तुमच्या ऑपरेशनची तारीख बारा आहे, सकाळी नऊ वाजता.” → date बारा; time सकाळी नऊ वाजता
- “Call me on 98220 12345 after 5 pm” → phone; time
- “Delivery Thursday, 950 rupees” → date; money
