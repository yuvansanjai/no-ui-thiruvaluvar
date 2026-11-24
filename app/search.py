import re
from typing import Optional, Tuple, List
from rapidfuzz import fuzz
from app.db import ThirukkuralDB, Kural

STOP_WORDS = {
    'சொல்லு', 'சொல்லுங்கள்', 'கூறு', 'கூறுங்கள்', 'படி', 'படியுங்கள்', 
    'எடு', 'காட்டு', 'திருக்குறள்', 'குறள்', 'எனக்கு', 'தெரியுமா', 'சொல்'
}

class KuralSearcher:
    def __init__(self, db: Optional[ThirukkuralDB] = None):
        self.db = db or ThirukkuralDB()
        self.all_kurals: List[Kural] = self.db.get_all_kurals()

    def clean_search_text(self, text: str) -> str:
        if not text:
            return ""
        # Remove punctuation
        t = re.sub(r"[.,\/#!$%\^&\*;:{}=\-_`~()\"\'\?\।\॥]", " ", text)
        words = [w.strip() for w in t.split() if w.strip() and w.strip() not in STOP_WORDS]
        return " ".join(words)

    def find_kural_by_text(self, query: str, threshold: float = 72.0) -> Optional[Tuple[Kural, float]]:
        """
        Fuzzy match query against all kurals:
        Checks prefix match against line1, token set ratio on line1, and normalized text.
        Returns (best_kural, score) or None if score < threshold.
        """
        clean_q = self.clean_search_text(query)
        if not clean_q or len(clean_q) < 5:
            return None

        best_kural: Optional[Kural] = None
        best_score: float = 0.0

        for kural in self.all_kurals:
            # 1. Prefix match against line1
            pref_len = min(len(clean_q), len(kural.line1))
            score_prefix = fuzz.ratio(clean_q, kural.line1[:pref_len]) if pref_len >= 5 else 0.0

            # 2. Token set / sort ratio on line 1
            score_line1_set = fuzz.token_set_ratio(clean_q, kural.line1)
            score_line1_sort = fuzz.token_sort_ratio(clean_q, kural.line1)

            # 3. Match full text
            score_full = fuzz.token_set_ratio(clean_q, kural.normalized_text)

            # Weighted composite score
            # We favor prefix match and line1 set match heavily
            score = max(score_prefix, score_line1_set * 0.95, score_line1_sort * 0.95, score_full * 0.88)

            if score > best_score:
                best_score = score
                best_kural = kural

        if best_kural and best_score >= threshold:
            return best_kural, best_score
        return None
