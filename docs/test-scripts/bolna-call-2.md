# Bolna call 2: test script

You play the shopkeeper (say the Hindi line, then wait for the reply to be spoken or about 10 s). The typist types the reply in the console (Hinglish, preview, Say this).

| ID | Say (Hindi) | Say (Roman) | Typist replies | Tests |
|---|---|---|---|---|
| L01 | हाँ जी, शर्मा मेडिकल, बोलिए। | Haan ji, Sharma Medical, boliye. | Namaste, mujhe Telma 40 ki goli chahiye. | short opening |
| L02 | जी, टेल्मा चालीस मिल जाएगी, कितनी गोली चाहिए? | Ji, Telma chalis mil jayegi, kitni goli chahiye? | Das din ki chahiye. | medicine name + number word |
| L03 | दस दिन की गोलियाँ, कुल चार सौ बीस रुपये होंगे। | Das din ki goliyan, kul chaar sau bees rupaye honge. | Theek hai, kya aaj mil jayegi? | price in words. TYPIST: wait 12 s before sending the reply (hold test) |
| L04 | हाँ आज शाम छह बजे तक तैयार रहेगी, लेकिन अगर आप होम डिलीवरी चाहते हैं तो उसके तीस रुपये एक्स्ट्रा लगेंगे और डिलीवरी सात बजे तक पहुँच जाएगी। | Haan aaj shaam chhah baje tak taiyaar rahegi, lekin agar aap home delivery chahte hain to uske tees rupaye extra lagenge aur delivery saat baje tak pahunch jayegi. | Delivery chahiye, Rajiv Nagar, Pune. | one long sentence (about 30 words), 3 numbers |
| L05 | आपका पता... (2 second pause) ...पूरा बताइए, घर का नंबर भी। | Aapka pata... (2 second pause) ...poora bataiye, ghar ka number bhi. | Flat 402, Rajiv Nagar, Kothrud. | pause in the middle of a sentence (fragmenting) |
| L06 | फ्लैट चार सौ दो, ठीक है। और आपका फोन नंबर बताइए। | Flat chaar sau do, theek hai. Aur aapka phone number bataiye. | Mera number 9 8 7 6 5 4 3 2 1 0 hai. | number in words |
| L07 | नौ आठ सात छह पाँच चार तीन दो एक शून्य, सही है? | Nau aath saat chhah paanch chaar teen do ek shoonya, sahi hai? | Haan, sahi hai. | phone number digit by digit |
| L08 | ठीक है। | Theek hai. | Shukriya. | very short utterance |
| L09 | Okay, your order is confirmed, it will reach by seven pm. | (say it in English) | Thank you. | English inside a Hindi-set recognizer |
| L10 | डॉक्टर साहब बारह तारीख को सुबह दस बजे मिलेंगे, दवाई के साथ पर्ची ज़रूर लाइएगा। | Doctor sahab barah taareekh ko subah das baje milenge, dawai ke saath parchi zaroor laiyega. | Parchi le aaunga. | date and time |
| L11 | आपका BP चेक करना है तो clinic में आइए, fees पाँच सौ रुपये है। | Aapka BP check karna hai to clinic mein aaiye, fees paanch sau rupaye hai. | Fees thodi kam ho sakti hai? | mixed Hindi and English words |
| L12 | नहीं जी, फीस तो फिक्स है, लेकिन पहली बार आने वाले मरीज़ों को पचास रुपये की छूट मिलती है, यानी चार सौ पचास। | Nahi ji, fees to fix hai, lekin pehli baar aane wale mareezon ko pachaas rupaye ki chhoot milti hai, yaani chaar sau pachaas. | Theek hai, 450 chalega. | long sentence with 3 numbers |
| L13 | एक ज़रूरी बात, आपके फोन पर एक OTP आएगा, वो मुझे बता दीजिए। | Ek zaroori baat, aapke phone par ek OTP aayega, wo mujhe bata dijiye. | Nahi, main OTP share nahi karunga. | scam line (the final product must warn and block digits) |
| L14 | हाँ। ठीक है। बिल्कुल। धन्यवाद। | Haan. Theek hai. Bilkul. Dhanyavaad. | (nothing) | rapid short phrases, one after another |
| L15 | (stay silent 20 seconds, then) हैलो, आप सुन रहे हैं? | (stay silent 20 seconds, then) Hello, aap sun rahe hain? | Haan, main yahin hoon. | long silence; TYPIST: type slowly for more than 5 s (keeper line) before sending |
| L16 | ठीक है, आपका दिन शुभ हो, नमस्ते। | Theek hai, aapka din shubh ho, namaste. | Namaste. | goodbye |
