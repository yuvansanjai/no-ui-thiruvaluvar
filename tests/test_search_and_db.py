import pytest
from app.db import ThirukkuralDB
from app.search import KuralSearcher

@pytest.fixture(scope="module")
def db():
    return ThirukkuralDB()

@pytest.fixture(scope="module")
def searcher(db):
    return KuralSearcher(db)

def test_db_counts(db):
    all_kurals = db.get_all_kurals()
    assert len(all_kurals) == 1330
    assert all_kurals[0].number == 1
    assert all_kurals[-1].number == 1330

def test_spot_checks(db):
    k1 = db.get_kural_by_number(1)
    assert k1 is not None
    assert k1.number == 1
    assert k1.adhikaram_no == 1
    assert "அகர முதல" in k1.line1
    assert "பகவன் முதற்றே உலகு" in k1.line2

    k150 = db.get_kural_by_number(150)
    assert k150 is not None
    assert k150.number == 150
    assert k150.adhikaram_no == 15
    assert "அறன்வரையான்" in k150.line1
    assert "பெண்மை நயவாமை நன்று" in k150.line2

def test_adhikaram_queries(db):
    # Adhikaram 12 has 10 kurals (111-120)
    k12 = db.get_kurals_by_adhikaram(12)
    assert len(k12) == 10
    assert k12[0].number == 111
    assert k12[-1].number == 120

def test_paal_queries(db):
    arathuppal = db.get_adhikarams_by_paal("அறத்துப்பால்")
    assert len(arathuppal) == 38

    porutpaal = db.get_adhikarams_by_paal("பொருட்பால்")
    assert len(porutpaal) == 70

    kamathuppal = db.get_adhikarams_by_paal("காமத்துப்பால்")
    assert len(kamathuppal) == 25

def test_fuzzy_search(searcher):
    # Test 1: First words of Kural 1
    res1 = searcher.find_kural_by_text("அகர முதல எழுத்தெல்லாம் சொல்லு")
    assert res1 is not None
    kural1, score1 = res1
    assert kural1.number == 1
    assert score1 >= 80

    # Test 2: Famous kural 391
    res391 = searcher.find_kural_by_text("கற்க கசடற கற்பவை கற்றபின்")
    assert res391 is not None
    kural391, score391 = res391
    assert kural391.number == 391

    # Test 3: Kural 12
    res12 = searcher.find_kural_by_text("துப்பார்க்குத் துப்பாய துப்பாக்கி")
    assert res12 is not None
    kural12, score12 = res12
    assert kural12.number == 12

    # Test 4: Low match / gibberish returns None
    res_none = searcher.find_kural_by_text("வாழைப்பழம் தக்காளி வெங்காயம்")
    assert res_none is None
