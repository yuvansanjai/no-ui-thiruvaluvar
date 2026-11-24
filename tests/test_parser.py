import pytest
from app.parser import parse_intent, extract_number, Intent, normalize_tamil_text

TEST_UTTERANCES = [
    # Core user examples
    ("குறள் 150 சொல்லு", Intent.KURAL_BY_NUMBER, 150),
    ("திருக்குறள் அதிகாரம் 12 சொல்லு", Intent.ADHIKARAM_BY_NUMBER, 12),
    ("அகர முதல எழுத்தெல்லாம் சொல்லு", Intent.KURAL_BY_TEXT, None),
    ("அறத்துப்பால் முதல் அதிகாரம் சொல்லு", Intent.ADHIKARAM_BY_NUMBER, 1),
    ("இதற்கு பொருள் சொல்லு", Intent.MEANING, None),
    ("அடுத்த குறள்", Intent.NEXT, None),
    ("முந்தைய குறள்", Intent.PREVIOUS, None),
    ("மீண்டும் சொல்லு", Intent.REPEAT, None),
    ("நிறுத்து", Intent.STOP, None),
    ("அறத்துப்பால்", Intent.PAAL, None),
    ("பொருட்பால்", Intent.PAAL, None),
    ("காமத்துப்பால்", Intent.PAAL, None),

    # Number variations: words
    ("நூற்று ஐம்பது", Intent.KURAL_BY_NUMBER, 150),
    ("பன்னிரண்டு", Intent.KURAL_BY_NUMBER, 12),
    ("பன்னிரெண்டு", Intent.KURAL_BY_NUMBER, 12),
    ("ஆயிரத்து முந்நூற்று முப்பது", Intent.KURAL_BY_NUMBER, 1330),
    ("முதல் குறள்", Intent.KURAL_BY_NUMBER, 1),
    ("இரண்டாவது குறள்", Intent.KURAL_BY_NUMBER, 2),
    ("பத்தாவது குறள்", Intent.KURAL_BY_NUMBER, 10),
    ("இருபத்து ஐந்து", Intent.KURAL_BY_NUMBER, 25),
    ("ஐம்பதாவது குறள்", Intent.KURAL_BY_NUMBER, 50),
    ("நூறாவது குறள் சொல்லு", Intent.KURAL_BY_NUMBER, 100),
    ("இருநூற்று ஐம்பது", Intent.KURAL_BY_NUMBER, 250),
    ("ஐந்நூற்று நாற்பது", Intent.KURAL_BY_NUMBER, 540),
    ("தொள்ளாயிரத்து எண்பது", Intent.KURAL_BY_NUMBER, 980),
    ("ஆயிரம்", Intent.KURAL_BY_NUMBER, 1000),
    ("ஆயிரத்து இருநூறு", Intent.KURAL_BY_NUMBER, 1200),

    # Number variations: Tamil numerals
    ("௧௫௦", Intent.KURAL_BY_NUMBER, 150),
    ("௧", Intent.KURAL_BY_NUMBER, 1),
    ("௰௨", Intent.KURAL_BY_NUMBER, 12),

    # Number variations: English fallback
    ("one fifty", Intent.KURAL_BY_NUMBER, 150),
    ("twelve", Intent.KURAL_BY_NUMBER, 12),
    ("one hundred fifty", Intent.KURAL_BY_NUMBER, 150),

    # Spelling variations
    ("குறல் 10 சொல்லு", Intent.KURAL_BY_NUMBER, 10),
    ("திருகுறள் 50", Intent.KURAL_BY_NUMBER, 50),
    ("அதிகரம் 5 சொல்லு", Intent.ADHIKARAM_BY_NUMBER, 5),
    ("குரன் நோட்டேம்பது சொல்லும்", Intent.KURAL_BY_NUMBER, 150),

    # Adhikaram by number
    ("அதிகாரம் 100", Intent.ADHIKARAM_BY_NUMBER, 100),
    ("பொருட்பால் முதல் அதிகாரம்", Intent.ADHIKARAM_BY_NUMBER, 39),

    # Kural by text
    ("கற்க கசடற கற்பவை கற்றபின்", Intent.KURAL_BY_TEXT, None),
    ("துப்பார்க்குத் துப்பாய துப்பாக்கி", Intent.KURAL_BY_TEXT, None),
    ("மனத்துக்கண் மாசிலன் ஆதல்", Intent.KURAL_BY_TEXT, None),
    ("அறன்வரையான் அல்ல செயினும்", Intent.KURAL_BY_TEXT, None),

    # Control and queries
    ("விளக்கம் சொல்லு", Intent.MEANING, None),
    ("பொருள் என்ன", Intent.MEANING, None),
    ("அடுத்தது", Intent.NEXT, None),
    ("முந்தியது", Intent.PREVIOUS, None),
    ("மறுபடியும் சொல்லு", Intent.REPEAT, None),
    ("போதும்", Intent.STOP, None),
    ("வணக்கம்", Intent.GREETING, None)
]

def test_utterance_count():
    assert len(TEST_UTTERANCES) >= 30, f"Expected at least 30 utterances, got {len(TEST_UTTERANCES)}"

@pytest.mark.parametrize("query,expected_intent,expected_number", TEST_UTTERANCES)
def test_parse_intent(query, expected_intent, expected_number):
    result = parse_intent(query)
    assert result.intent == expected_intent, f"Failed for '{query}': got intent {result.intent}, expected {expected_intent}"
    if expected_number is not None:
        assert result.number == expected_number, f"Failed for '{query}': got number {result.number}, expected {expected_number}"

def test_extract_number_direct():
    assert extract_number("150") == 150
    assert extract_number("௧௫௦") == 150
    assert extract_number("நூற்று ஐம்பது") == 150
    assert extract_number("பன்னிரண்டு") == 12
    assert extract_number("பன்னிரெண்டு") == 12
    assert extract_number("ஆயிரத்து முந்நூற்று முப்பது") == 1330
    assert extract_number("one fifty") == 150
    assert extract_number("twelve") == 12
    assert extract_number("முதல்") == 1
    assert extract_number("ஒன்று") == 1
    assert extract_number("பத்து") == 10
