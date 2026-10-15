"""Automated pytest test suite verifying market simulator convergence thresholds."""

from scripts.simulate import run_comprehensive_simulation_suite


def test_market_simulation_thresholds() -> None:
    results = run_comprehensive_simulation_suite()

    # Threshold 1: Cumulative regret is at least 30% lower than uniform random
    assert results["regret_reduction_pct"] >= 30.0, (
        f"Regret reduction {results['regret_reduction_pct']:.1f}% failed target >= 30%"
    )

    # Threshold 2: After 2,000 leads, the best arm gets at least 40% of traffic
    assert results["median_best_arm_share"] >= 40.0, (
        f"Best arm share {results['median_best_arm_share']:.1f}% failed target >= 40%"
    )

    # Threshold 3: After regime shift, allocation to collapsed arm falls below 10% within 300 further leads
    assert results["median_collapsed_share"] < 10.0, (
        f"Collapsed arm share {results['median_collapsed_share']:.1f}% failed target < 10%"
    )

    # Threshold 4: Wrong prior recovery within 500 leads
    assert results["wrong_prior_recovery_rate"] >= 90.0, (
        f"Wrong prior recovery rate {results['wrong_prior_recovery_rate']:.1f}% failed target >= 90%"
    )

    # Threshold 5: OPE coverage >= 90%
    assert results["ope_coverage_pct"] >= 90.0, (
        f"OPE coverage {results['ope_coverage_pct']:.1f}% failed target >= 90%"
    )

    # Threshold 6: Seed replay determinism
    assert results["replay_identical"] is True, (
        "Replaying simulation with identical seed produced divergent stats."
    )
