from app import area

def test_area():
    assert area(4) == 16

def test_area_zero():
    assert area(0) == 0
