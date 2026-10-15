"""Learning, bandit optimization, priors, and OPE module."""

from src.engine.learning.decide import DecisionRecord, decide
from src.engine.learning.ope import LoggedDecision, OPEResult, compute_ope_estimates
from src.engine.learning.priors import PriorResult, resolve_prior
from src.engine.learning.rewards import compute_decision_rewards
from src.engine.learning.updater import apply_nightly_discounting, update_arm_stats_batch

__all__ = [
    "decide",
    "DecisionRecord",
    "resolve_prior",
    "PriorResult",
    "compute_decision_rewards",
    "update_arm_stats_batch",
    "apply_nightly_discounting",
    "compute_ope_estimates",
    "LoggedDecision",
    "OPEResult",
]
