from app.relay.entities import extract_entities


def found(text):
    return [(e.type, e.text) for e in extract_entities(text)]


def test_pharmacy_money_and_time():
    assert found("हाँ, मिल जाएगी। ₹420 होंगे, शाम 6 बजे तक तैयार।") == [
        ("money", "₹420"),
        ("time", "शाम 6 बजे"),
    ]


def test_marathi_date_and_time_words():
    assert found("तुमच्या ऑपरेशनची तारीख बारा आहे, सकाळी नऊ वाजता.") == [
        ("date", "बारा"),
        ("time", "सकाळी नऊ वाजता"),
    ]


def test_phone_and_english_time():
    assert found("Call me on 98220 12345 after 5 pm") == [
        ("phone", "98220 12345"),
        ("time", "5 pm"),
    ]


def test_weekday_and_money_words():
    assert found("Delivery Thursday, 950 rupees") == [("date", "Thursday"), ("money", "950 rupees")]


def test_devanagari_digits_normalised_and_spans_valid():
    text = "₹४२० होंगे"
    (e,) = extract_entities(text)
    assert e.type == "money" and text[e.start : e.end] == "₹४२०" and e.value == 420.0


def test_quantity_and_no_false_positives():
    assert found("10 goli chahiye") == [("quantity", "10 goli")]
    assert found("नमस्ते, कैसे हैं आप?") == []


def test_phone_value_is_ten_digits():
    (e,) = extract_entities("+91 98220 12345")
    assert e.value == "9822012345"
