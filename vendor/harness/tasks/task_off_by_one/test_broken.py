from broken import sum_range

def test_sum_range_5():
    assert sum_range(5) == 15

def test_sum_range_1():
    assert sum_range(1) == 1

def test_sum_range_0():
    assert sum_range(0) == 0
