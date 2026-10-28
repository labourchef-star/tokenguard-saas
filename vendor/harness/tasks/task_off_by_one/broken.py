"""Intentionally buggy: off-by-one in sum_range."""

def sum_range(n: int) -> int:
    """Return sum of 1..n inclusive. BUG: range stops early."""
    total = 0
    for i in range(1, n):  # BUG: should be range(1, n+1)
        total += i
    return total
