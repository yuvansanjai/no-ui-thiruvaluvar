import os
import sys
import time
import threading
import tkinter as tk
from typing import Optional, List

from app.db import ThirukkuralDB, Kural
from app.search import KuralSearcher
from app.parser import parse_intent, Intent, IntentResult
from app.tts import (
    TTSEngine,
    FEEDBACK_STARTUP,
    FEEDBACK_OUT_OF_RANGE,
    FEEDBACK_NOT_UNDERSTOOD
)
from app.stt import STTEngine


class AssistantState:
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


class ThirukkuralVoiceApp:
    def __init__(self, root: tk.Tk, auto_meaning: bool = False):
        self.root = root
        self.auto_meaning = auto_meaning

        # Backend components
        self.db = ThirukkuralDB()
        self.searcher = KuralSearcher(self.db)
        self.tts = TTSEngine(auto_meaning=self.auto_meaning)
        self.stt = STTEngine()

        # App state
        self.state = AssistantState.IDLE
        self.current_kural: Optional[Kural] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_listening_flag = False
        self._interrupt_speaking_flag = False
        self._has_spoken_startup = False

        self._setup_ui()
        self._bind_events()

        # Speak startup greeting once on a background thread after UI shows
        self.root.after(300, self._startup_greeting)

    def _setup_ui(self):
        self.root.title("திருக்குறள்")
        self.root.geometry("540x580")
        self.root.minsize(420, 480)
        self.root.configure(bg="#0f172a") # Elegant deep slate background

        # Top spacer
        top_spacer = tk.Frame(self.root, bg="#0f172a", height=50)
        top_spacer.pack(side=tk.TOP, fill=tk.X)

        # Center Container for the ONE big mic button
        center_frame = tk.Frame(self.root, bg="#0f172a")
        center_frame.pack(expand=True, fill=tk.BOTH)

        # Canvas for the large circular button
        self.canvas_size = 180
        self.button_canvas = tk.Canvas(
            center_frame,
            width=self.canvas_size,
            height=self.canvas_size,
            bg="#0f172a",
            highlightthickness=0,
            cursor="hand2"
        )
        self.button_canvas.pack(pady=20)

        # Draw circular button
        self.circle_id = self.button_canvas.create_oval(
            10, 10, self.canvas_size - 10, self.canvas_size - 10,
            fill="#2563eb", outline="#3b82f6", width=4
        )
        self.icon_id = self.button_canvas.create_text(
            self.canvas_size // 2, self.canvas_size // 2,
            text="🎙️", font=("Segoe UI Emoji", 48), fill="#ffffff"
        )

        # Status text (small indicator directly under the button)
        self.status_label = tk.Label(
            center_frame,
            text="பேச பொத்தானை அழுத்தவும்",
            font=("Nirmala UI", 12),
            fg="#94a3b8",
            bg="#0f172a"
        )
        self.status_label.pack(pady=10)

        # Caption label: ONLY shows the Tamil text of the current kural in a small caption
        self.caption_frame = tk.Frame(self.root, bg="#0f172a")
        self.caption_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=30)

        self.caption_label = tk.Label(
            self.caption_frame,
            text="",
            font=("Nirmala UI", 11),
            fg="#e2e8f0",
            bg="#0f172a",
            wraplength=480,
            justify=tk.CENTER
        )
        self.caption_label.pack()

    def _bind_events(self):
        # Click on canvas triggers voice button
        self.button_canvas.bind("<Button-1>", lambda e: self.on_mic_button_clicked())
        # Spacebar keypress triggers voice button
        self.root.bind("<space>", lambda e: self.on_mic_button_clicked())
        # Escape stops playback or listening
        self.root.bind("<Escape>", lambda e: self._handle_barge_in())

    def _set_button_visuals(self, fill_color: str, outline_color: str, icon_text: str, status_text: str, status_color: str):
        self.button_canvas.itemconfig(self.circle_id, fill=fill_color, outline=outline_color)
        self.button_canvas.itemconfig(self.icon_id, text=icon_text)
        self.status_label.config(text=status_text, fg=status_color)

    def _update_ui_state(self, state: str):
        self.state = state
        if state == AssistantState.IDLE:
            self._set_button_visuals("#2563eb", "#3b82f6", "🎙️", "பேச பொத்தானை அழுத்தவும்", "#94a3b8")
        elif state == AssistantState.LISTENING:
            self._set_button_visuals("#dc2626", "#ef4444", "🎙️", "கேட்கிறது... பேசுங்கள்", "#f87171")
        elif state == AssistantState.PROCESSING:
            self._set_button_visuals("#d97706", "#f59e0b", "⏳", "புரிந்துகொள்கிறது...", "#fbbf24")
        elif state == AssistantState.SPEAKING:
            self._set_button_visuals("#059669", "#10b981", "🔊", "பேசுகிறது...", "#34d399")

    def _update_caption(self, kural: Optional[Kural]):
        self.current_kural = kural
        if kural:
            caption_text = f"குறள் {kural.number} ({kural.adhikaram_name})\n{kural.line1}\n{kural.line2}"
        else:
            caption_text = ""
        self.caption_label.config(text=caption_text)

    def _startup_greeting(self):
        if self._has_spoken_startup:
            return
        self._has_spoken_startup = True

        def run():
            # Load Whisper model and audio cache silently in the background
            try:
                self.stt._ensure_model_loaded()
            except Exception as e:
                print(f"[STT] Background model load error: {e}")

            self._update_ui_state(AssistantState.SPEAKING)
            self.tts.speak_text(FEEDBACK_STARTUP, check_interrupt=lambda: self._interrupt_speaking_flag)
            self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))

        t = threading.Thread(target=run, daemon=True)
        t.start()

    def _handle_barge_in(self):
        """Immediately stop speaking or listening."""
        self._interrupt_speaking_flag = True
        self._stop_listening_flag = True
        self.tts.stop_playback()

    def on_mic_button_clicked(self):
        """User clicks the button or presses Space."""
        if self.state == AssistantState.SPEAKING:
            # Barge-in: interrupt speech and start listening
            self._handle_barge_in()
            time.sleep(0.1)
            self._start_listening_flow()
        elif self.state == AssistantState.LISTENING:
            # Clicking while listening immediately stops recording and proceeds to transcribe
            self._stop_listening_flag = True
        elif self.state == AssistantState.IDLE:
            self._start_listening_flow()

    def _start_listening_flow(self):
        self._interrupt_speaking_flag = False
        self._stop_listening_flag = False
        self._update_ui_state(AssistantState.LISTENING)

        # Soft ding sound before listening
        self.tts.play_ding()

        def listen_worker():
            # 1. Record audio with VAD
            audio_data = self.stt.record_with_vad(
                silence_duration=1.2,
                speech_energy_threshold=0.012,
                max_duration=12.0,
                stop_check=lambda: self._stop_listening_flag
            )

            # If no audio captured or cancelled
            if audio_data is None or len(audio_data) == 0:
                self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))
                return

            # 2. Processing (Transcribe & Parse)
            self.root.after(0, lambda: self._update_ui_state(AssistantState.PROCESSING))
            raw_text, norm_text = self.stt.transcribe_audio_array(audio_data)
            print(f"[UI] Transcribed: '{raw_text}' -> Normalized: '{norm_text}'")

            if not norm_text:
                self._speak_feedback(FEEDBACK_NOT_UNDERSTOOD)
                return

            intent_res = parse_intent(norm_text)
            print(f"[UI] Parsed intent: {intent_res}")
            self._execute_intent(intent_res)

        self._worker_thread = threading.Thread(target=listen_worker, daemon=True)
        self._worker_thread.start()

    def _speak_feedback(self, text: str):
        self.root.after(0, lambda: self._update_ui_state(AssistantState.SPEAKING))
        self.tts.speak_text(text, check_interrupt=lambda: self._interrupt_speaking_flag)
        self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))

    def _execute_intent(self, intent_res: IntentResult):
        intent = intent_res.intent

        # 1. STOP (Completely silent in audio: stops playback and returns to idle)
        if intent == Intent.STOP:
            print("[UI] Stop requested: stopping playback silently.")
            self._handle_barge_in()
            self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))
            return

        # 2. REPEAT
        if intent == Intent.REPEAT:
            if self.current_kural:
                self._play_kural(self.current_kural)
            else:
                self._speak_feedback(FEEDBACK_NOT_UNDERSTOOD)
            return

        # 3. NEXT
        if intent == Intent.NEXT:
            current_num = self.current_kural.number if self.current_kural else 0
            next_num = current_num + 1
            if next_num > 1330:
                self._speak_feedback(FEEDBACK_OUT_OF_RANGE)
            else:
                k = self.db.get_kural_by_number(next_num)
                if k:
                    self._play_kural(k)
            return

        # 4. PREVIOUS
        if intent == Intent.PREVIOUS:
            current_num = self.current_kural.number if self.current_kural else 2
            prev_num = current_num - 1
            if prev_num < 1:
                self._speak_feedback(FEEDBACK_OUT_OF_RANGE)
            else:
                k = self.db.get_kural_by_number(prev_num)
                if k:
                    self._play_kural(k)
            return

        # 5. MEANING
        if intent == Intent.MEANING:
            if self.current_kural:
                meaning_text = f"குறள் எண் {self.current_kural.number}. பொருள்: {self.current_kural.meaning_ta}."
                self._speak_feedback(meaning_text)
            else:
                self._speak_feedback(FEEDBACK_NOT_UNDERSTOOD)
            return

        # 6. GREETING (Do not speak greeting again after startup; keep audio silent)
        if intent == Intent.GREETING:
            print("[UI] Greeting received; staying silent as startup greeting is only spoken once.")
            self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))
            return

        # 7. KURAL_BY_NUMBER
        if intent == Intent.KURAL_BY_NUMBER:
            num = intent_res.number
            if num is None or not (1 <= num <= 1330):
                self._speak_feedback(FEEDBACK_OUT_OF_RANGE)
                return
            kural = self.db.get_kural_by_number(num)
            if kural:
                self._play_kural(kural)
            else:
                self._speak_feedback(FEEDBACK_OUT_OF_RANGE)
            return

        # 8. ADHIKARAM_BY_NUMBER
        if intent == Intent.ADHIKARAM_BY_NUMBER:
            adh_no = intent_res.number
            if adh_no is None or not (1 <= adh_no <= 133):
                self._speak_feedback(FEEDBACK_OUT_OF_RANGE)
                return
            kurals = self.db.get_kurals_by_adhikaram(adh_no)
            if not kurals:
                self._speak_feedback(FEEDBACK_OUT_OF_RANGE)
                return

            self._play_adhikaram_kurals(adh_no, kurals)
            return

        # 9. PAAL
        if intent == Intent.PAAL:
            paal_name = intent_res.text or "அறத்துப்பால்"
            adhikarams = self.db.get_adhikarams_by_paal(paal_name)
            if not adhikarams:
                self._speak_feedback(FEEDBACK_NOT_UNDERSTOOD)
                return
            self._play_paal_adhikarams(paal_name, adhikarams)
            return

        # 10. KURAL_BY_TEXT (fuzzy match)
        if intent == Intent.KURAL_BY_TEXT:
            match_res = self.searcher.find_kural_by_text(intent_res.text)
            if match_res:
                kural, score = match_res
                print(f"[UI] Found kural {kural.number} with score {score:.1f}")
                self._play_kural(kural)
            else:
                self._speak_feedback(FEEDBACK_NOT_UNDERSTOOD)
            return

        # Fallback unknown
        self._speak_feedback(FEEDBACK_NOT_UNDERSTOOD)

    def _play_kural(self, kural: Kural):
        """Speak a single kural and update the caption."""
        self.root.after(0, lambda: self._update_caption(kural))
        self.root.after(0, lambda: self._update_ui_state(AssistantState.SPEAKING))
        self.tts.speak_kural(kural, check_interrupt=lambda: self._interrupt_speaking_flag)
        self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))

    def _play_adhikaram_kurals(self, adh_no: int, kurals: List[Kural]):
        """Speak all 10 kurals of an adhikaram one by one with a 1.2s pause between them."""
        self.root.after(0, lambda: self._update_ui_state(AssistantState.SPEAKING))
        adh_name = kurals[0].adhikaram_name if kurals else ""

        # Intro text
        intro = f"அதிகாரம் {adh_no}. {adh_name}."
        if not self.tts.speak_text(intro, check_interrupt=lambda: self._interrupt_speaking_flag):
            self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))
            return

        for idx, kural in enumerate(kurals):
            if self._interrupt_speaking_flag:
                break

            self.root.after(0, lambda k=kural: self._update_caption(k))
            completed = self.tts.speak_kural(kural, check_interrupt=lambda: self._interrupt_speaking_flag)
            if not completed or self._interrupt_speaking_flag:
                break

            # 1.2 second pause between kurals
            if idx < len(kurals) - 1:
                if not self.tts.sleep_interruptible(1.2, check_interrupt=lambda: self._interrupt_speaking_flag):
                    break

        self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))

    def _play_paal_adhikarams(self, paal_name: str, adhikarams: List[tuple]):
        """Speak adhikaram names of that paal one by one."""
        self.root.after(0, lambda: self._update_ui_state(AssistantState.SPEAKING))
        intro = f"{paal_name}. இதில் உள்ள அதிகாரங்கள்."
        if not self.tts.speak_text(intro, check_interrupt=lambda: self._interrupt_speaking_flag):
            self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))
            return

        for no, name in adhikarams:
            if self._interrupt_speaking_flag:
                break
            text = f"அதிகாரம் {no}. {name}."
            completed = self.tts.speak_text(text, check_interrupt=lambda: self._interrupt_speaking_flag)
            if not completed or self._interrupt_speaking_flag:
                break
            if not self.tts.sleep_interruptible(0.5, check_interrupt=lambda: self._interrupt_speaking_flag):
                break

        self.root.after(0, lambda: self._update_ui_state(AssistantState.IDLE))


def main():
    root = tk.Tk()
    app = ThirukkuralVoiceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
