from utils import double, clamp

def test_double():
    assert double(3) == 6

def test_clamp_mid():
    assert clamp(5, 0, 10) == 5

def test_clamp_low():
    assert clamp(-1, 0, 10) == 0

def test_clamp_high():
    assert clamp(99, 0, 10) == 10
