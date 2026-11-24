import re
from enum import Enum
from typing import Optional, Tuple, Dict, Any

class Intent(str, Enum):
    KURAL_BY_NUMBER = "kural_by_number"
    ADHIKARAM_BY_NUMBER = "adhikaram_by_number"
    KURAL_BY_TEXT = "kural_by_text"
    PAAL = "paal"
    MEANING = "meaning"
    NEXT = "next"
    PREVIOUS = "previous"
    REPEAT = "repeat"
    STOP = "stop"
    GREETING = "greeting"
    UNKNOWN = "unknown"

# Tamil digits map
TAMIL_DIGITS = {
    '௦': 0, '௧': 1, '௨': 2, '௩': 3, '௪': 4,
    '௫': 5, '௬': 6, '௭': 7, '௮': 8, '௯': 9,
    '௰': 10, '௱': 100, '௲': 1000
}

# English words to numbers
ENGLISH_UNITS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19
}

ENGLISH_TENS = {
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
    'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
}

# Tamil word mappings
TAMIL_ORDINALS = {
    'முதல்': 1, 'முதலாம்': 1, 'முதலாவது': 1,
    'இரண்டாம்': 2, 'இரண்டாவது': 2, 'ரெண்டாவது': 2,
    'மூன்றாம்': 3, 'மூன்றாவது': 3, 'மூணாவது': 3,
    'நான்காம்': 4, 'நான்காவது': 4, 'நாலாம்': 4, 'நாலாவது': 4,
    'ஐந்தாம்': 5, 'ஐந்தாவது': 5, 'அஞ்சாவது': 5,
    'ஆறாம்': 6, 'ஆறாவது': 6,
    'ஏழாம்': 7, 'ஏழாவது': 7,
    'எட்டாம்': 8, 'எட்டாவது': 8,
    'ஒன்பதாம்': 9, 'ஒன்பதாவது': 9,
    'பத்தாம்': 10, 'பத்தாவது': 10
}

TAMIL_UNITS = {
    'பூஜ்ஜியம்': 0, 'பூஜ்யம்': 0,
    'ஒன்று': 1, 'ஒன்னு': 1, 'ஒண்ணு': 1, 'ஒரு': 1,
    'இரண்டு': 2, 'ரெண்டு': 2, 'இரு': 2,
    'மூன்று': 3, 'மூணு': 3, 'மு': 3,
    'நான்கு': 4, 'நாலு': 4,
    'ஐந்து': 5, 'அஞ்சு': 5,
    'ஆறு': 6,
    'ஏழு': 7,
    'எட்டு': 8,
    'ஒன்பது': 9
}

TAMIL_TEENS = {
    'பத்து': 10,
    'பதினொன்று': 11, 'பதினொன்னு': 11,
    'பன்னிரண்டு': 12, 'பன்னிரெண்டு': 12, 'பண்ணிரண்டு': 12, 'பண்ணிரெண்டு': 12,
    'பதின்மூன்று': 13, 'பதிமூன்று': 13, 'பதின்மூணு': 13, 'பதிமூணு': 13,
    'பதினான்கு': 14, 'பதினாங்கு': 14, 'பதினாலு': 14,
    'பதினைந்து': 15, 'பதினஞ்சு': 15,
    'பதினாறு': 16,
    'பதினேழு': 17,
    'பதினெட்டு': 18,
    'பத்தொன்பது': 19
}

TAMIL_TENS = {
    'இருபது': 20, 'இருபத்து': 20, 'இருவது': 20,
    'முப்பது': 30, 'முப்பத்து': 30,
    'நாற்பது': 40, 'நாற்பத்து': 40, 'நாப்பது': 40,
    'ஐம்பது': 50, 'ஐம்பத்து': 50, 'அம்பது': 50, 'அம்பத்து': 50,
    'அறுபது': 60, 'அறுபத்து': 60,
    'எழுபது': 70, 'எழுபத்து': 70,
    'எண்பது': 80, 'எண்பத்து': 80, 'எம்பது': 80, 'எம்பத்து': 80,
    'தொண்ணூறு': 90, 'தொண்ணூற்று': 90, 'தொன்னூறு': 90, 'தொன்னூற்று': 90
}

TAMIL_HUNDREDS = {
    'நூறு': 100, 'நூற்று': 100, 'நூற்ற': 100, 'நூத்து': 100, 'நூத்த': 100,
    'நூற்றைம்பது': 150, 'நோட்டேம்பது': 150, 'நூத்தைம்பது': 150,
    'இருநூறு': 200, 'இருநூற்று': 200, 'இருநூற்ற': 200,
    'முந்நூறு': 300, 'முந்நூற்று': 300, 'முன்னூறு': 300, 'முன்னூற்று': 300,
    'நானூறு': 400, 'நானூற்று': 400,
    'ஐந்நூறு': 500, 'ஐந்நூற்று': 500, 'ஐநூறு': 500, 'ஐநூற்று': 500,
    'அறுநூறு': 600, 'அறுநூற்று': 600,
    'எழுநூறு': 700, 'எழுநூற்று': 700,
    'எண்ணூறு': 800, 'எண்ணூற்று': 800, 'எந்நூறு': 800, 'எந்நூற்று': 800,
    'தொள்ளாயிரம்': 900, 'தொள்ளாயிரத்து': 900, 'தொளாயிரம்': 900, 'தொளாயிரத்து': 900
}

TAMIL_THOUSANDS = {
    'ஆயிரம்': 1000, 'ஆயிரத்து': 1000
}


def normalize_tamil_text(text: str) -> str:
    """Normalize spelling variants and strip punctuation."""
    if not text:
        return ""
    t = text.lower()
    # Strip punctuation
    t = re.sub(r"[.,\/#!$%\^&\*;:{}=\-_`~()\"\'\?\।\॥…\—\–]", " ", t)

    # Normalize spelling & transcription variants
    # Only replace குறள if not already followed by pulli ்
    t = re.sub(r'குறள(?!்)', 'குறள்', t)
    t = t.replace("குறல்", "குறள்")
    t = t.replace("குரன்", "குறள்")
    t = t.replace("குரல்", "குறள்")
    t = t.replace("திருகுறள்", "திருக்குறள்")
    t = t.replace("திருக்குரல்", "திருக்குறள்")
    t = t.replace("திருகுரல்", "திருக்குறள்")
    t = t.replace("திருக்குரன்", "திருக்குறள்")
    t = t.replace("அதிகரம்", "அதிகாரம்")
    t = t.replace("அடிகாரம்", "அதிகாரம்")
    t = t.replace("சொல்லும்", "சொல்லு")
    t = t.replace("சொல்லுவ்", "சொல்லு")
    t = t.replace("சொல்லுவு", "சொல்லு")
    t = t.replace("பன்னிரெண்டு", "பன்னிரண்டு")
    t = t.replace("பண்ணிரண்டு", "பன்னிரண்டு")
    t = t.replace("முன்னூறு", "முந்நூறு")
    t = t.replace("முன்னூற்று", "முந்நூற்று")
    t = t.replace("ஐநூறு", "ஐந்நூறு")
    t = t.replace("ஐநூற்று", "ஐந்நூற்று")
    t = t.replace("தொளாயிரம்", "தொள்ளாயிரம்")
    t = t.replace("தொளாயிரத்து", "தொள்ளாயிரத்து")

    # Replace multiple spaces with single space
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_tamil_digits(token: str) -> Optional[int]:
    """Parse Tamil numeral string (e.g. ௧௫௦ -> 150 or classical ௱௫௰)."""
    # Check if string consists of Tamil digit characters
    if not token or not any(c in TAMIL_DIGITS for c in token):
        return None

    # Check for pure positional digits (like ௧௫௦)
    all_positional = all(c in '௦௧௨௩௪௫௬௭௮௯' for c in token)
    if all_positional:
        val = 0
        for c in token:
            val = val * 10 + TAMIL_DIGITS[c]
        return val

    # Classical Tamil numerals (௲=1000, ௱=100, ௰=10)
    total = 0
    current = 0
    for c in token:
        if c in '௧௨௩௪௫௬௭௮௯':
            current = TAMIL_DIGITS[c]
        elif c == '௰':
            total += (current if current > 0 else 1) * 10
            current = 0
        elif c == '௱':
            total += (current if current > 0 else 1) * 100
            current = 0
        elif c == '௲':
            total += (current if current > 0 else 1) * 1000
            current = 0
        elif c == '௦':
            current = 0
    total += current
    return total if total > 0 else None


def parse_english_number(tokens: list[str]) -> Optional[Tuple[int, int]]:
    """
    Parse English number words from tokens (e.g. ['one', 'fifty'] -> 150, ['twelve'] -> 12).
    Returns (value, number_of_tokens_consumed) or None.
    """
    total = 0
    consumed = 0
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i].lower()
        if tok in ENGLISH_UNITS:
            val = ENGLISH_UNITS[tok]
            if i + 1 < n and tokens[i+1].lower() == 'hundred':
                total += val * 100
                i += 2
                consumed = i
                continue
            elif i + 1 < n and tokens[i+1].lower() in ENGLISH_TENS:
                # e.g. "one fifty" -> 150
                total += val * 100 + ENGLISH_TENS[tokens[i+1].lower()]
                i += 2
                if i < n and tokens[i].lower() in ENGLISH_UNITS:
                    total += ENGLISH_UNITS[tokens[i].lower()]
                    i += 1
                consumed = i
                continue
            else:
                total += val
                i += 1
                consumed = i
                continue
        elif tok in ENGLISH_TENS:
            val = ENGLISH_TENS[tok]
            total += val
            i += 1
            if i < n and tokens[i].lower() in ENGLISH_UNITS:
                total += ENGLISH_UNITS[tokens[i].lower()]
                i += 1
            consumed = i
            continue
        elif tok == 'hundred':
            total = (total if total > 0 else 1) * 100
            i += 1
            consumed = i
            continue
        elif tok == 'thousand':
            total = (total if total > 0 else 1) * 1000
            i += 1
            consumed = i
            continue
        else:
            break

    if consumed > 0 and total > 0:
        return total, consumed
    return None


def clean_word_suffix(word: str) -> str:
    """Strip ordinal / case suffixes from number words (both independent and combining forms)."""
    w = word.strip()
    all_num_dicts = (TAMIL_UNITS, TAMIL_TEENS, TAMIL_TENS, TAMIL_HUNDREDS, TAMIL_THOUSANDS)

    # Check combining (dependent) vowel suffixes first (e.g. ாவது, ாம்), then independent (ஆவது, ஆம், வது)
    for suff in ('ாவது', 'ஆவது', 'வது', 'ாம்', 'ஆம்', 'வதுக்கு', 'க்கு', 'ற்கு'):
        if w.endswith(suff) and len(w) > len(suff):
            base = w[:-len(suff)]
            # Direct match
            if any(base in d for d in all_num_dicts):
                return base
            # Tamil sandhi restoration:
            # e.g. ஐம்பத -> ஐம்பது, நாற்பத -> நாற்பது, பத்த -> பத்து
            if any((base + 'ு') in d for d in all_num_dicts):
                return base + 'ு'
            # e.g. ஆயிரம -> ஆயிரம்
            if any((base + '்') in d for d in all_num_dicts):
                return base + '்'
            if len(base) > 1 and any((base[:-1] + 'ம்') in d for d in all_num_dicts):
                return base[:-1] + 'ம்'
    return w


def parse_tamil_words_to_number(tokens: list[str]) -> Optional[Tuple[int, int]]:
    """
    Parse consecutive Tamil number words from list of tokens.
    Handles compound phrases like:
    - 'நூற்று' 'ஐம்பது' -> 150
    - 'ஆயிரத்து' 'முந்நூற்று' 'முப்பது' -> 1330
    - 'பன்னிரண்டு' -> 12
    - 'முதல்' / 'முதலாம்' -> 1
    Returns (parsed_integer, consumed_token_count) or None.
    """
    if not tokens:
        return None

    # Check first token for ordinals (முதல், இரண்டாம்...)
    tok0 = tokens[0].strip()
    if tok0 in TAMIL_ORDINALS:
        return TAMIL_ORDINALS[tok0], 1

    total = 0
    current_thousands = 0
    current_hundreds = 0
    current_tens_units = 0
    consumed = 0

    i = 0
    n = len(tokens)

    while i < n:
        raw_tok = tokens[i].strip()
        tok = clean_word_suffix(raw_tok)

        if tok in TAMIL_THOUSANDS:
            mul = current_tens_units if current_tens_units > 0 else 1
            current_thousands = mul * 1000
            current_tens_units = 0
            consumed = i + 1
            i += 1
        elif tok in TAMIL_HUNDREDS:
            current_hundreds = TAMIL_HUNDREDS[tok]
            consumed = i + 1
            i += 1
        elif tok in TAMIL_TENS:
            current_tens_units += TAMIL_TENS[tok]
            consumed = i + 1
            i += 1
        elif tok in TAMIL_TEENS:
            current_tens_units += TAMIL_TEENS[tok]
            consumed = i + 1
            i += 1
        elif tok in TAMIL_UNITS:
            # Check if this unit is a multiplier before hundred or thousand
            if i + 1 < n and tokens[i+1].strip() in ('நூறு', 'நூற்று', 'ஆயிரம்', 'ஆயிரத்து'):
                current_tens_units = TAMIL_UNITS[tok]
            else:
                current_tens_units += TAMIL_UNITS[tok]
            consumed = i + 1
            i += 1
        elif raw_tok in TAMIL_ORDINALS:
            current_tens_units += TAMIL_ORDINALS[raw_tok]
            consumed = i + 1
            i += 1
        else:
            # Check if token is Arabic digits
            m = re.match(r'^(\d+)(வது|ஆவது|ஆம்)?$', raw_tok)
            if m:
                current_tens_units += int(m.group(1))
                consumed = i + 1
                i += 1
            else:
                break

    if consumed > 0:
        val = current_thousands + current_hundreds + current_tens_units
        if val > 0:
            return val, consumed
    return None


def extract_number(text: str) -> Optional[int]:
    """
    Extract a number from text in ANY form:
    1. Arabic digits (150, 150வது)
    2. Tamil numeral digits (௧௫௦)
    3. Tamil number words ("நூற்று ஐம்பது", "பன்னிரண்டு", "ஆயிரத்து முந்நூற்று முப்பது", "முதல்")
    4. English number words ("one fifty", "twelve")
    """
    normalized = normalize_tamil_text(text)
    tokens = normalized.split()

    # 1. Search for Arabic digits
    m = re.search(r'\b(\d+)(?:வது|ஆவது|ஆம்|th|st|nd|rd)?\b', normalized)
    if m:
        return int(m.group(1))

    # 2. Check for Tamil digits (௧௫௦)
    for tok in tokens:
        val = parse_tamil_digits(tok)
        if val is not None:
            return val

    # 3. Check for Tamil number words at any position
    for idx in range(len(tokens)):
        res = parse_tamil_words_to_number(tokens[idx:])
        if res is not None:
            return res[0]

    # 4. Check for English number words
    for idx in range(len(tokens)):
        res = parse_english_number(tokens[idx:])
        if res is not None:
            return res[0]

    return None


class IntentResult:
    def __init__(self, intent: Intent, number: Optional[int] = None, text: str = "", raw_query: str = ""):
        self.intent = intent
        self.number = number
        self.text = text
        self.raw_query = raw_query

    def __repr__(self):
        return f"<IntentResult intent={self.intent.value} number={self.number} text='{self.text}'>"


def parse_intent(query: str) -> IntentResult:
    """
    Parse spoken Tamil query into structured IntentResult.
    Handles all specified intents and normalization.
    """
    raw_query = query.strip()
    norm = normalize_tamil_text(raw_query)

    if not norm:
        return IntentResult(Intent.UNKNOWN, raw_query=raw_query)

    # 1. STOP intent
    if any(k in norm for k in ("நிறுத்து", "போதும்", "நில்", "ஸ்டாப்", "முடி", "stop")):
        return IntentResult(Intent.STOP, raw_query=raw_query)

    # 2. REPEAT intent
    if any(k in norm for k in ("மீண்டும் சொல்லு", "மறுபடியும் சொல்லு", "மீண்டும்", "மறுபடியும்", "இன்னொரு முறை", "repeat")):
        return IntentResult(Intent.REPEAT, raw_query=raw_query)

    # 3. NEXT / PREVIOUS intents
    if any(k in norm for k in ("அடுத்த குறள்", "அடுத்தது", "அடுத்து", "முன்னோக்கி", "next")):
        return IntentResult(Intent.NEXT, raw_query=raw_query)
    if any(k in norm for k in ("முந்தைய குறள்", "முந்தியது", "முந்தையது", "பின்னாடி", "முன்னாடி", "previous")):
        return IntentResult(Intent.PREVIOUS, raw_query=raw_query)

    # 4. MEANING intent
    if any(k in norm for k in ("இதற்கு பொருள்", "பொருள் சொல்லு", "விளக்கம் சொல்லு", "பொருள் என்ன", "பொருள் கூறு", "விளக்கம்", "பொருள்")):
        # Ensure it's not "பொருட்பால்"
        if "பொருட்பால்" not in norm and "பொருள்பால்" not in norm:
            return IntentResult(Intent.MEANING, raw_query=raw_query)

    # 5. GREETING intent
    if norm in ("வணக்கம்", "ஹலோ", "வணக்கம் சொல்லு", "ஹாய்", "வணக்கங்கள்"):
        return IntentResult(Intent.GREETING, raw_query=raw_query)

    # 6. Check for PAAL intent
    # Note: "அறத்துப்பால்", "பொருட்பால்", "காமத்துப்பால்", "இன்பத்துப்பால்"
    paal_match = None
    for p in ("அறத்துப்பால்", "பொருட்பால்", "காமத்துப்பால்", "இன்பத்துப்பால்"):
        if p in norm:
            paal_match = "காமத்துப்பால்" if p == "இன்பத்துப்பால்" else p
            break

    # 7. Check for ADHIKARAM
    # Examples: "அதிகாரம் 12 சொல்லு", "பன்னிரண்டாவது அதிகாரம்", "அறத்துப்பால் முதல் அதிகாரம் சொல்லு"
    is_adhikaram = ("அதிகாரம்" in norm or "அதிகர" in norm)
    num = extract_number(norm)

    if is_adhikaram:
        if num is not None:
            # If paal was specified (e.g. "அறத்துப்பால் முதல் அதிகாரம்"),
            # Arathuppal adhikarams start from 1. Porutpaal starts from 39. Kamathuppal starts from 109.
            # If someone says "பொருட்பால் முதல் அதிகாரம்", 1st adhikaram of Porutpaal is 39!
            if paal_match == "பொருட்பால்" and 1 <= num <= 70:
                num = 38 + num
            elif paal_match == "காமத்துப்பால்" and 1 <= num <= 25:
                num = 108 + num
            return IntentResult(Intent.ADHIKARAM_BY_NUMBER, number=num, text=norm, raw_query=raw_query)
        elif paal_match:
            # If someone said e.g. "அறத்துப்பால் அதிகாரங்கள்"
            return IntentResult(Intent.PAAL, text=paal_match, raw_query=raw_query)

    # If paal is mentioned without a specific adhikaram number (e.g. "அறத்துப்பால்", "பொருட்பால் சொல்லு")
    if paal_match and ("குறள்" not in norm and not is_adhikaram):
        return IntentResult(Intent.PAAL, text=paal_match, raw_query=raw_query)

    # 8. Check for KURAL_BY_NUMBER
    # Examples: "குறள் 150 சொல்லு", "150 வது குறள்", "நூற்று ஐம்பதாவது குறள் சொல்லு", "150 சொல்லு", "பன்னிரண்டு"
    is_kural = ("குறள்" in norm or "குறல்" in norm or "திருக்குறள்" in norm)
    if num is not None:
        # If user explicitly said "குறள்" / "திருக்குறள்" OR the query consists primarily of the number / request words
        clean_non_num = norm
        for w in ("குறள்", "திருக்குறள்", "எண்", "சொல்லு", "சொல்லுங்கள்", "கூறு", "படி", "எடுத்துக்காட்டு", "வது", "ஆவது"):
            clean_non_num = clean_non_num.replace(w, "")
        clean_non_num = clean_non_num.strip()

        # If it mentioned kural, or after stripping command words what remains is the number itself or very short
        if is_kural or len(clean_non_num.split()) <= 4:
            return IntentResult(Intent.KURAL_BY_NUMBER, number=num, text=norm, raw_query=raw_query)

    # 9. Otherwise, treat as KURAL_BY_TEXT (fuzzy text search for kural lyrics)
    # Examples: "அகர முதல எழுத்தெல்லாம் சொல்லு", "துப்பார்க்குத் துப்பாய துப்பாக்கி"
    return IntentResult(Intent.KURAL_BY_TEXT, text=raw_query, raw_query=raw_query)
