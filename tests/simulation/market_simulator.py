"""Market Simulator: Synthetic gym market modeling consumer behavior and bandit convergence."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import numpy as np

from src.engine.domain.bandits import (
    ArmPosterior,
    apply_time_discount,
    select_arm,
    update_beta_posterior,
)
from src.engine.learning.ope import LoggedDecision


@dataclass
class SimulatedLead:
    lead_id: UUID
    segment: str  # 'f_25_34', 'all'
    hook_arm_id: UUID
    offer_arm_id: UUID
    propensity: float
    explored: bool
    created_at: datetime
    reward: float = 0.0


class GymMarketSimulator:
    """
    Synthetic market simulation environment:
    - 6 ad hooks, 4 offers
    - Ground truth conversion rates per arm combination and segment
    - Daily time discounting (0.995) to model non-stationarity
    - Mid-run regime shift at day 60 (hook 0 collapses)
    """

    def __init__(
        self,
        seed: int = 42,
        num_leads: int = 2000,
        regime_shift_day: int = 60,
        leads_per_day: int = 4,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.num_leads = num_leads
        self.regime_shift_day = regime_shift_day
        self.leads_per_day = leads_per_day
        self.shift_lead_index = regime_shift_day * leads_per_day  # e.g. lead 240
        self.start_date = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)

        # 6 Hook Arms
        self.hooks = [uuid4() for _ in range(6)]
        # 4 Offer Arms
        self.offers = [uuid4() for _ in range(4)]

        # Base conversion rates: Arm 0 initial best (0.35), Arm 1 post-shift best (0.32)
        self.hook_initial_rates = [0.35, 0.20, 0.18, 0.16, 0.14, 0.04]
        self.hook_collapsed_rates = [0.01, 0.32, 0.18, 0.16, 0.14, 0.04]

    def run_simulation(
        self,
        use_bandit: bool = True,
        warm_start_priors: dict[UUID, tuple[float, float]] | None = None,
    ) -> dict[str, Any]:
        """
        Runs the simulation across num_leads.
        Returns logged decisions, regret trace, arm allocation frequencies, and stats.
        """
        bandit_stats: dict[UUID, dict[str, float]] = {}
        for h_id in self.hooks:
            if warm_start_priors and h_id in warm_start_priors:
                a, b = warm_start_priors[h_id]
            else:
                a, b = 1.0, 1.0
            bandit_stats[h_id] = {"alpha": a, "beta": b, "n": 0}

        logged_decisions: list[LoggedDecision] = []
        hook_allocations: list[int] = []
        regret_history: list[float] = []
        cumulative_regret = 0.0

        for lead_num in range(1, self.num_leads + 1):
            day_offset = lead_num // self.leads_per_day
            self.start_date + timedelta(days=day_offset)

            # Active true rates
            if lead_num >= self.shift_lead_index:
                active_rates = self.hook_collapsed_rates
                oracle_best_rate = 0.32
            else:
                active_rates = self.hook_initial_rates
                oracle_best_rate = 0.35

            segment = "f_25_34" if self.rng.random() < 0.4 else "all"

            # Selection
            if use_bandit:
                arm_posteriors = [
                    ArmPosterior(
                        arm_id=h_id,
                        alpha=bandit_stats[h_id]["alpha"],
                        beta=bandit_stats[h_id]["beta"],
                        n=int(bandit_stats[h_id]["n"]),
                    )
                    for h_id in self.hooks
                ]
                choice = select_arm(arm_posteriors, epsilon=0.05, num_draws=2000, rng=self.rng)
                chosen_hook = choice.chosen_arm_id
                propensity = choice.propensity
                chosen_hook_idx = self.hooks.index(chosen_hook)
            else:
                chosen_hook_idx = int(self.rng.choice(len(self.hooks)))
                chosen_hook = self.hooks[chosen_hook_idx]
                propensity = 1.0 / len(self.hooks)

            hook_allocations.append(chosen_hook_idx)

            # Conversion and Regret
            true_rate = active_rates[chosen_hook_idx]
            instant_regret = max(0.0, oracle_best_rate - true_rate)
            cumulative_regret += instant_regret
            regret_history.append(cumulative_regret)

            # Binary reward signal representing funnel member conversion
            reward = 1.0 if self.rng.random() < true_rate else 0.0

            logged_decisions.append(
                LoggedDecision(
                    decision_id=uuid4(),
                    chosen_arm_id=chosen_hook,
                    candidate_arm_ids=list(self.hooks),
                    propensity=propensity,
                    observed_reward=reward,
                    context={"segment": segment, "day": day_offset},
                )
            )

            # Posterior update
            if use_bandit:
                cur_a = bandit_stats[chosen_hook]["alpha"]
                cur_b = bandit_stats[chosen_hook]["beta"]
                new_a, new_b = update_beta_posterior(
                    current_alpha=cur_a,
                    current_beta=cur_b,
                    current_applied_reward=0.0,
                    new_cumulative_reward=reward,
                    first_time=True,
                )
                bandit_stats[chosen_hook]["alpha"] = new_a
                bandit_stats[chosen_hook]["beta"] = new_b
                bandit_stats[chosen_hook]["n"] += 1

                # Nightly discount
                if lead_num % self.leads_per_day == 0:
                    for h_id in self.hooks:
                        da, db = apply_time_discount(
                            bandit_stats[h_id]["alpha"],
                            bandit_stats[h_id]["beta"],
                            factor=0.995,
                        )
                        bandit_stats[h_id]["alpha"] = da
                        bandit_stats[h_id]["beta"] = db

        total_leads = len(hook_allocations)
        counts = [hook_allocations.count(i) for i in range(len(self.hooks))]
        arm_shares = [c / total_leads for c in counts]
        best_arm_traffic_share = max(arm_shares)

        # Allocation to collapsed arm within 300 further leads (leads shift_lead to shift_lead + 300)
        end_eval_window = self.shift_lead_index + 300
        window = hook_allocations[end_eval_window - 50 : end_eval_window]
        collapsed_share_at_300 = float(window.count(0)) / len(window) if window else 0.0

        return {
            "cumulative_regret": cumulative_regret,
            "regret_history": regret_history,
            "arm_traffic_shares": arm_shares,
            "best_arm_traffic_share": best_arm_traffic_share,
            "collapsed_arm_share_at_300": collapsed_share_at_300,
            "final_bandit_stats": bandit_stats,
            "logged_decisions": logged_decisions,
        }
