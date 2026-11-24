from app.parser import parse_intent, extract_number, Intent

def test_user_examples():
    test_cases = [
        ('குறள் 150 சொல்லு', Intent.KURAL_BY_NUMBER, 150),
        ('திருக்குறள் அதிகாரம் 12 சொல்லு', Intent.ADHIKARAM_BY_NUMBER, 12),
        ('அகர முதல எழுத்தெல்லாம் சொல்லு', Intent.KURAL_BY_TEXT, None),
        ('அறத்துப்பால் முதல் அதிகாரம் சொல்லு', Intent.ADHIKARAM_BY_NUMBER, 1),
        ('இதற்கு பொருள் சொல்லு', Intent.MEANING, None),
        ('அடுத்த குறள்', Intent.NEXT, None),
        ('முந்தைய குறள்', Intent.PREVIOUS, None),
        ('மீண்டும் சொல்லு', Intent.REPEAT, None),
        ('நிறுத்து', Intent.STOP, None),
        ('அறத்துப்பால்', Intent.PAAL, None),
        ('பொருட்பால்', Intent.PAAL, None),
        ('காமத்துப்பால்', Intent.PAAL, None),
        ('நூற்று ஐம்பது', Intent.KURAL_BY_NUMBER, 150),
        ('பன்னிரண்டு', Intent.KURAL_BY_NUMBER, 12),
        ('பன்னிரெண்டு', Intent.KURAL_BY_NUMBER, 12),
        ('ஆயிரத்து முந்நூற்று முப்பது', Intent.KURAL_BY_NUMBER, 1330),
        ('௧௫௦', Intent.KURAL_BY_NUMBER, 150),
        ('one fifty', Intent.KURAL_BY_NUMBER, 150),
    ]

    for text, exp_intent, exp_num in test_cases:
        res = parse_intent(text)
        assert res.intent == exp_intent, f"Failed for {text}: got {res.intent}, expected {exp_intent}"
        if exp_num is not None:
            assert res.number == exp_num, f"Failed number for {text}: got {res.number}, expected {exp_num}"
