import os
import sqlite3
from dataclasses import dataclass
from typing import Optional, List, Tuple

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "thirukkural.db")

@dataclass
class Kural:
    number: int
    adhikaram_no: int
    adhikaram_name: str
    paal: str
    line1: str
    line2: str
    meaning_ta: str
    normalized_text: str

    @property
    def full_tamil_text(self) -> str:
        return f"{self.line1}\n{self.line2}"

    def to_spoken_text(self, include_meaning: bool = False) -> str:
        text = f"குறள் எண் {self.number}. {self.line1}. {self.line2}."
        if include_meaning and self.meaning_ta:
            text += f" பொருள்: {self.meaning_ta}."
        return text

class ThirukkuralDB:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}. Run data/build_db.py first.")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_kural_by_number(self, num: int) -> Optional[Kural]:
        if not (1 <= num <= 1330):
            return None
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT number, adhikaram_no, adhikaram_name, paal, line1, line2, meaning_ta, normalized_text
                FROM kural WHERE number = ?
            """, (num,))
            row = cur.fetchone()
            if row:
                return Kural(**dict(row))
            return None

    def get_kurals_by_adhikaram(self, adhikaram_no: int) -> List[Kural]:
        if not (1 <= adhikaram_no <= 133):
            return []
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT number, adhikaram_no, adhikaram_name, paal, line1, line2, meaning_ta, normalized_text
                FROM kural WHERE adhikaram_no = ? ORDER BY number ASC
            """, (adhikaram_no,))
            rows = cur.fetchall()
            return [Kural(**dict(r)) for r in rows]

    def get_adhikarams_by_paal(self, paal_name: str) -> List[Tuple[int, str]]:
        # Normalize paal matching
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT adhikaram_no, adhikaram_name
                FROM kural WHERE paal LIKE ? ORDER BY adhikaram_no ASC
            """, (f"%{paal_name}%",))
            rows = cur.fetchall()
            return [(r[0], r[1]) for r in rows]

    def get_all_kurals(self) -> List[Kural]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT number, adhikaram_no, adhikaram_name, paal, line1, line2, meaning_ta, normalized_text
                FROM kural ORDER BY number ASC
            """)
            rows = cur.fetchall()
            return [Kural(**dict(r)) for r in rows]
