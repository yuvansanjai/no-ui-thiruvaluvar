import os
import re
import hashlib
import asyncio
import time
import pygame
import edge_tts
from typing import Optional, Callable
from app.db import Kural

AUDIO_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tts_cache")
DING_SOUND_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ding.wav")

VOICE_PALLAVI = "ta-IN-PallaviNeural"
VOICE_VALLUVAR = "ta-IN-ValluvarNeural"
DEFAULT_VOICE = VOICE_PALLAVI
DEFAULT_RATE = "-8%"

# Standard voice feedback messages (ONLY startup greeting and the two allowed error messages)
FEEDBACK_STARTUP = "வணக்கம். பேச பொத்தானை அழுத்துங்கள்."
FEEDBACK_OUT_OF_RANGE = "அந்த எண் இல்லை. குறள் ஒன்று முதல் ஆயிரத்து முந்நூற்று முப்பது வரை உள்ளன."
FEEDBACK_NOT_UNDERSTOOD = "மன்னிக்கவும், புரியவில்லை. மீண்டும் சொல்லுங்கள்."


def sanitize_tts_text(text: str) -> str:
    """
    Safety check: strip any XML/SSML tags, angle brackets, or metadata keywords
    before sending text to TTS. Logs a warning to the console if detected.
    """
    if not text:
        return ""
    disallowed_keywords = ("<", ">", "xml", "prosody", "speak", "break", "voice")
    text_lower = text.lower()
    if any(k in text_lower for k in disallowed_keywords):
        print(f"[TTSEngine] WARNING: Disallowed markup/keyword detected in TTS text: {text}")
        cleaned = re.sub(r"<[^>]+>", " ", text)
        for k in disallowed_keywords:
            cleaned = re.sub(re.escape(k), "", cleaned, flags=re.IGNORECASE)
        text = cleaned

    return re.sub(r"\s+", " ", text).strip()


class TTSEngine:
    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE, auto_meaning: bool = False):
        self.voice = voice
        self.rate = rate
        self.auto_meaning = auto_meaning
        self.cache_dir = AUDIO_CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        self._init_audio()
        self._stop_requested = False
        self._is_speaking = False

    def _init_audio(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as e:
            print(f"[TTSEngine] pygame mixer init warning: {e}")

    def play_ding(self):
        """Play soft ding sound when user clicks or starts listening."""
        try:
            if os.path.exists(DING_SOUND_PATH):
                sound = pygame.mixer.Sound(DING_SOUND_PATH)
                sound.play()
        except Exception as e:
            print(f"[TTSEngine] ding error: {e}")

    def stop_playback(self):
        """Barge-in: immediately stop any current speech playback."""
        self._stop_requested = True
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        self._is_speaking = False

    @property
    def is_speaking(self) -> bool:
        try:
            return pygame.mixer.get_init() and (pygame.mixer.music.get_busy() or self._is_speaking)
        except Exception:
            return self._is_speaking

    def sleep_interruptible(self, duration_sec: float, check_interrupt: Optional[Callable[[], bool]] = None) -> bool:
        """Sleep for duration_sec while checking for interruption every 40ms."""
        steps = max(1, int(duration_sec / 0.04))
        for _ in range(steps):
            if self._stop_requested or (check_interrupt and check_interrupt()):
                return False
            time.sleep(0.04)
        return True

    def get_audio_path_for_text(self, text: str) -> str:
        clean_text = sanitize_tts_text(text)
        h = hashlib.sha256(f"{self.voice}:{self.rate}:{clean_text}".encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.mp3")

    async def _generate_audio_file(self, text: str, filepath: str):
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(filepath)

    def synthesize(self, text: str) -> str:
        """
        Synthesize PLAIN Tamil text to an MP3 file with speed controlled by rate parameter.
        NEVER passes SSML or XML markup.
        """
        clean_text = sanitize_tts_text(text)
        if not clean_text:
            raise ValueError("TTS text is empty after sanitization.")

        cached_file = self.get_audio_path_for_text(clean_text)
        if os.path.exists(cached_file) and os.path.getsize(cached_file) > 300:
            return cached_file

        temp_file = cached_file + ".tmp.mp3"
        try:
            asyncio.run(self._generate_audio_file(clean_text, temp_file))
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 300:
                os.replace(temp_file, cached_file)
                return cached_file
        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            raise RuntimeError(f"TTS synthesis failed for text '{clean_text}': {e}")
        return cached_file

    def play_audio_file(self, filepath: str, check_interrupt: Optional[Callable[[], bool]] = None) -> bool:
        """
        Plays an audio file synchronously while allowing barge-in / cancellation.
        Returns True if played to completion, False if interrupted.
        """
        self._stop_requested = False
        self._is_speaking = True
        try:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                if self._stop_requested or (check_interrupt and check_interrupt()):
                    pygame.mixer.music.stop()
                    self._is_speaking = False
                    return False
                clock.tick(30)
            self._is_speaking = False
            return True
        except Exception as e:
            print(f"[TTSEngine] play_audio_file error: {e}")
            self._is_speaking = False
            return False

    def speak_text(self, text: str, check_interrupt: Optional[Callable[[], bool]] = None) -> bool:
        """Speak plain Tamil text."""
        clean_text = sanitize_tts_text(text)
        if not clean_text:
            return True
        audio_file = self.synthesize(clean_text)
        return self.play_audio_file(audio_file, check_interrupt=check_interrupt)

    def speak_kural(
        self,
        kural: Kural,
        include_meaning: Optional[bool] = None,
        check_interrupt: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Speak a kural as separate clean clips with natural pauses:
        1. "குறள் எண் {kural.number}."
        2. Line 1
        3. Pause ~500 ms
        4. Line 2
        5. If meaning requested: Pause ~900 ms, then "பொருள்: {meaning_ta}."
        """
        self._stop_requested = False
        with_meaning = self.auto_meaning if include_meaning is None else include_meaning

        # Segment 1: Header ("குறள் எண் N.")
        header_text = f"குறள் எண் {kural.number}."
        if not self.speak_text(header_text, check_interrupt=check_interrupt):
            return False

        if not self.sleep_interruptible(0.2, check_interrupt=check_interrupt):
            return False

        # Segment 2: Line 1
        if not self.speak_text(kural.line1, check_interrupt=check_interrupt):
            return False

        # Natural silence between line 1 and line 2 (500 ms)
        if not self.sleep_interruptible(0.5, check_interrupt=check_interrupt):
            return False

        # Segment 3: Line 2
        if not self.speak_text(kural.line2, check_interrupt=check_interrupt):
            return False

        # Optional Segment 4: Meaning with 900 ms pause
        if with_meaning and kural.meaning_ta:
            if not self.sleep_interruptible(0.9, check_interrupt=check_interrupt):
                return False
            meaning_text = f"பொருள்: {kural.meaning_ta}."
            if not self.speak_text(meaning_text, check_interrupt=check_interrupt):
                return False

        return True
