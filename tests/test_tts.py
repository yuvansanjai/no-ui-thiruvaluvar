import pytest
from unittest.mock import MagicMock
from app.db import ThirukkuralDB
from app.tts import TTSEngine, sanitize_tts_text

def test_kural_150_tts_text_no_markup():
    """
    Ensure the text passed to TTS for Kural 150 contains only clean Tamil text
    and NO SSML or XML markup (<, >, speak, prosody, break, voice, xml, 1.0).
    """
    db = ThirukkuralDB()
    k150 = db.get_kural_by_number(150)
    assert k150 is not None
    assert k150.number == 150

    tts = TTSEngine()
    spoken_clips = []

    # Mock speak_text to capture every segment passed to TTS
    def mock_speak_text(text, check_interrupt=None):
        spoken_clips.append(text)
        return True

    tts.speak_text = mock_speak_text
    tts.sleep_interruptible = MagicMock(return_value=True)

    # Speak kural 150
    completed = tts.speak_kural(k150)
    assert completed is True

    # Check segments:
    # Segment 1: Header ("குறள் எண் 150.")
    # Segment 2: Line 1 ("அறன்வரையான் அல்ல செயினும் பிறன்வரையாள்")
    # Segment 3: Line 2 ("பெண்மை நயவாமை நன்று.")
    assert len(spoken_clips) == 3
    assert spoken_clips[0] == "குறள் எண் 150."
    assert "அறன்வரையான்" in spoken_clips[1]
    assert "பெண்மை நயவாமை நன்று" in spoken_clips[2]

    disallowed = ("<", ">", "speak", "prosody", "break", "voice", "xml", "1.0")

    for clip in spoken_clips:
        clip_lower = clip.lower()
        for bad in disallowed:
            assert bad not in clip_lower, f"Found disallowed '{bad}' in spoken clip: '{clip}'"

def test_kural_150_with_meaning_no_markup():
    db = ThirukkuralDB()
    k150 = db.get_kural_by_number(150)
    tts = TTSEngine(auto_meaning=True)
    spoken_clips = []

    tts.speak_text = lambda text, check_interrupt=None: spoken_clips.append(text) or True
    tts.sleep_interruptible = MagicMock(return_value=True)

    completed = tts.speak_kural(k150, include_meaning=True)
    assert completed is True
    assert len(spoken_clips) == 4
    assert spoken_clips[3].startswith("பொருள்:")

    disallowed = ("<", ">", "speak", "prosody", "break", "voice", "xml", "1.0")
    for clip in spoken_clips:
        clip_lower = clip.lower()
        for bad in disallowed:
            assert bad not in clip_lower, f"Found disallowed '{bad}' in spoken clip: '{clip}'"

def test_sanitize_tts_text_strips_disallowed_tokens():
    bad_input = "<speak version='1.0'><voice name='test'><prosody rate='-8%'>குறள்<break time='500ms'/>எண்</prosody></voice></speak>"
    cleaned = sanitize_tts_text(bad_input)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "speak" not in cleaned.lower()
    assert "prosody" not in cleaned.lower()
    assert "break" not in cleaned.lower()
    assert "voice" not in cleaned.lower()
    assert "xml" not in cleaned.lower()
    assert "குறள்" in cleaned
    assert "எண்" in cleaned
