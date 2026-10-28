"""loop_stop: quality-preserving loop detector for coding-agent tool use."""

from .detector import LoopDetector, Decision, DecisionKind
from .session_log import SessionLog

__all__ = ["LoopDetector", "Decision", "DecisionKind", "SessionLog"]
__version__ = "0.1.0"
