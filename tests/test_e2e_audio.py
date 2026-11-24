import os
import sys

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
import edge_tts
from app.stt import STTEngine
from app.parser import parse_intent, Intent
from app.db import ThirukkuralDB
from app.search import KuralSearcher
from app.tts import TTSEngine

E2E_AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e_samples")
os.makedirs(E2E_AUDIO_DIR, exist_ok=True)

EXAMPLE_QUERIES = [
    {
        "id": "query_1_kural_150",
        "spoken_text": "குறள் 150 சொல்லு",
        "expected_intent": Intent.KURAL_BY_NUMBER,
        "expected_num": 150
    },
    {
        "id": "query_2_adhikaram_12",
        "spoken_text": "திருக்குறள் அதிகாரம் 12 சொல்லு",
        "expected_intent": Intent.ADHIKARAM_BY_NUMBER,
        "expected_num": 12
    },
    {
        "id": "query_3_kural_by_text",
        "spoken_text": "அகர முதல எழுத்தெல்லாம் சொல்லு",
        "expected_intent": Intent.KURAL_BY_TEXT,
        "expected_kural": 1
    },
    {
        "id": "query_4_paal_adhikaram",
        "spoken_text": "அறத்துப்பால் முதல் அதிகாரம் சொல்லு",
        "expected_intent": Intent.ADHIKARAM_BY_NUMBER,
        "expected_num": 1
    },
    {
        "id": "query_5_meaning",
        "spoken_text": "இதற்கு பொருள் சொல்லு",
        "expected_intent": Intent.MEANING,
        "expected_num": None
    },
    {
        "id": "query_6_next",
        "spoken_text": "அடுத்த குறள்",
        "expected_intent": Intent.NEXT,
        "expected_num": None
    },
    {
        "id": "query_7_previous",
        "spoken_text": "முந்தைய குறள்",
        "expected_intent": Intent.PREVIOUS,
        "expected_num": None
    },
    {
        "id": "query_8_repeat",
        "spoken_text": "மீண்டும் சொல்லு",
        "expected_intent": Intent.REPEAT,
        "expected_num": None
    },
    {
        "id": "query_9_stop",
        "spoken_text": "நிறுத்து",
        "expected_intent": Intent.STOP,
        "expected_num": None
    }
]

async def generate_sample_audio_files():
    print(f"Generating {len(EXAMPLE_QUERIES)} sample Tamil audio recordings...")
    for item in EXAMPLE_QUERIES:
        filepath = os.path.join(E2E_AUDIO_DIR, f"{item['id']}.mp3")
        if not os.path.exists(filepath):
            comm = edge_tts.Communicate(item["spoken_text"], "ta-IN-PallaviNeural", rate="-4%")
            await comm.save(filepath)
            print(f"  Created: {filepath} ({item['spoken_text']})")
        else:
            print(f"  Exists: {filepath}")

def run_end_to_end_test():
    asyncio.run(generate_sample_audio_files())

    print("\n" + "=" * 75)
    print("END-TO-END PIPELINE & STT ACCURACY VERIFICATION REPORT")
    print("=" * 75)

    stt = STTEngine()
    db = ThirukkuralDB()
    searcher = KuralSearcher(db)
    tts = TTSEngine()

    results = []
    correct_intent_count = 0
    correct_target_count = 0

    for item in EXAMPLE_QUERIES:
        filepath = os.path.join(E2E_AUDIO_DIR, f"{item['id']}.mp3")
        spoken = item["spoken_text"]

        # 1. STT Transcribe
        raw_transcript, norm_transcript = stt.transcribe_file(filepath, language="ta")

        # 2. Intent Parsing
        intent_res = parse_intent(norm_transcript)

        # 3. Execution verification
        target_matched = False
        response_preview = ""

        if intent_res.intent == Intent.KURAL_BY_NUMBER:
            k = db.get_kural_by_number(intent_res.number)
            if k and intent_res.number == item.get("expected_num"):
                target_matched = True
                response_preview = f"Kural {k.number}: {k.line1} / {k.line2}"
        elif intent_res.intent == Intent.ADHIKARAM_BY_NUMBER:
            kurals = db.get_kurals_by_adhikaram(intent_res.number)
            if kurals and intent_res.number == item.get("expected_num"):
                target_matched = True
                response_preview = f"Adhikaram {intent_res.number} ({kurals[0].adhikaram_name}): {len(kurals)} kurals"
        elif intent_res.intent == Intent.KURAL_BY_TEXT:
            match = searcher.find_kural_by_text(intent_res.text)
            if match:
                k, score = match
                if k.number == item.get("expected_kural"):
                    target_matched = True
                    response_preview = f"Matched Kural {k.number} (score: {score:.1f}%): {k.line1}"
        elif intent_res.intent in (Intent.MEANING, Intent.NEXT, Intent.PREVIOUS, Intent.REPEAT, Intent.STOP):
            if intent_res.intent == item["expected_intent"]:
                target_matched = True
                response_preview = f"Action {intent_res.intent.value} acknowledged"

        intent_correct = (intent_res.intent == item["expected_intent"])
        if intent_correct:
            correct_intent_count += 1
        if target_matched:
            correct_target_count += 1

        status = "SUCCESS" if (intent_correct and target_matched) else "MISMATCH"
        print(f"\n[{status}] Audio: {item['id']}")
        print(f"  Spoken Input : \"{spoken}\"")
        print(f"  STT Output   : \"{raw_transcript}\" -> norm: \"{norm_transcript}\"")
        print(f"  Parsed Intent: {intent_res.intent.value} (Expected: {item['expected_intent'].value})")
        print(f"  Resolved Data: {response_preview}")

        results.append({
            "id": item["id"],
            "spoken": spoken,
            "stt": raw_transcript,
            "intent_correct": intent_correct,
            "target_matched": target_matched
        })

    total = len(EXAMPLE_QUERIES)
    intent_acc = (correct_intent_count / total) * 100
    e2e_acc = (correct_target_count / total) * 100

    print("\n" + "=" * 75)
    print("FINAL SUMMARY METRICS")
    print("=" * 75)
    print(f"Total Test Audio Queries : {total}")
    print(f"Intent Classification Acc: {correct_intent_count}/{total} ({intent_acc:.1f}%)")
    print(f"End-to-End Success Rate  : {correct_target_count}/{total} ({e2e_acc:.1f}%)")
    print("=" * 75)

    assert intent_acc == 100.0, f"Expected 100% intent accuracy, got {intent_acc}%"
    assert e2e_acc == 100.0, f"Expected 100% end-to-end success, got {e2e_acc}%"
    print("\nALL END-TO-END AUDIO CHECKS PASSED!")

if __name__ == "__main__":
    run_end_to_end_test()
