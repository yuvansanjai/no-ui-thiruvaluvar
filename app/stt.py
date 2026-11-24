import os
import time
import queue
import numpy as np
import sounddevice as sd
import soundfile as sf
from typing import Optional, Callable, Tuple
from faster_whisper import WhisperModel
from app.parser import normalize_tamil_text

DEFAULT_MODEL_SIZE = "small"
SAMPLE_RATE = 16000
CHANNELS = 1
TAMIL_INITIAL_PROMPT = (
    "திருக்குறள், குறள் எண், அதிகாரம், அறத்துப்பால், பொருட்பால், காமத்துப்பால், "
    "பொருள், அடுத்த குறள், முந்தைய குறள், மீண்டும் சொல்லு, நிறுத்து, "
    "ஒன்று, இரண்டு, பன்னிரண்டு, நூற்று ஐம்பது, ஆயிரத்து முந்நூற்று முப்பது."
)

class STTEngine:
    def __init__(self, model_size: str = DEFAULT_MODEL_SIZE, device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    def _ensure_model_loaded(self):
        if self._model is None:
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

    def record_with_vad(
        self,
        silence_duration: float = 1.3,
        speech_energy_threshold: float = 0.012,
        max_duration: float = 12.0,
        stop_check: Optional[Callable[[], bool]] = None,
        on_speech_started: Optional[Callable[[], None]] = None
    ) -> Optional[np.ndarray]:
        """
        Record audio from the microphone until speech finishes (VAD).
        - Automatically detects when user speaks.
        - Automatically stops when user remains silent for `silence_duration` seconds.
        - Supports early stop via `stop_check()`.
        Returns numpy array of float32 samples at 16kHz, or None if aborted/empty.
        """
        q = queue.Queue()

        def audio_callback(indata, frames, time_info, status):
            if status:
                pass
            q.put(indata.copy())

        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                callback=audio_callback,
                blocksize=int(SAMPLE_RATE * 0.05) # 50ms blocks
            )
        except Exception as e:
            print(f"[STTEngine] Microphone open error: {e}")
            return None

        recorded_chunks = []
        speech_detected = False
        silence_start_time = None
        start_time = time.time()

        with stream:
            while True:
                if stop_check and stop_check():
                    break

                if time.time() - start_time > max_duration:
                    break

                try:
                    block = q.get(timeout=0.1)
                except queue.Empty:
                    continue

                recorded_chunks.append(block)

                # Compute block RMS energy
                rms = np.sqrt(np.mean(block ** 2))

                if rms > speech_energy_threshold:
                    if not speech_detected:
                        speech_detected = True
                        if on_speech_started:
                            on_speech_started()
                    silence_start_time = None
                else:
                    if speech_detected:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time >= silence_duration:
                            # Speech ended after silence duration
                            break

        if not recorded_chunks:
            return None

        audio_data = np.concatenate(recorded_chunks, axis=0).flatten()

        # If no significant speech was detected during the whole window
        max_rms = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0
        if max_rms < speech_energy_threshold * 0.8:
            return None

        return audio_data

    def transcribe_audio_array(self, audio_data: np.ndarray, language: str = "ta") -> Tuple[str, str]:
        """
        Transcribe raw audio array with faster-whisper.
        Returns (raw_transcript, normalized_transcript).
        """
        self._ensure_model_loaded()
        if len(audio_data) == 0:
            return "", ""

        # Normalize audio volume to [-1.0, 1.0]
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max(max_val, 1e-4)

        segments, info = self._model.transcribe(
            audio_data,
            language=language,
            initial_prompt=TAMIL_INITIAL_PROMPT,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400),
            beam_size=5
        )

        texts = [s.text.strip() for s in segments]
        raw_text = " ".join(texts).strip()
        norm_text = normalize_tamil_text(raw_text)
        return raw_text, norm_text

    def transcribe_file(self, filepath: str, language: str = "ta") -> Tuple[str, str]:
        """Transcribe an audio file (wav, mp3, flac)."""
        self._ensure_model_loaded()
        segments, info = self._model.transcribe(
            filepath,
            language=language,
            initial_prompt=TAMIL_INITIAL_PROMPT,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400),
            beam_size=5
        )
        texts = [s.text.strip() for s in segments]
        raw_text = " ".join(texts).strip()
        norm_text = normalize_tamil_text(raw_text)
        return raw_text, norm_text
