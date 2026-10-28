"""App with a broken import."""
from mathy_typo import square  # BUG: should be `from mathy import square`

def area(side: int) -> int:
    return square(side)
