from code_insights.cli import (
    MONITOR_FAST_INTERVAL_SECONDS,
    MONITOR_IDLE_TO_MEDIUM_ROUNDS,
    MONITOR_IDLE_TO_SLOW_ROUNDS,
    MONITOR_MEDIUM_INTERVAL_SECONDS,
    MONITOR_SLOW_INTERVAL_SECONDS,
    _compute_monitor_interval,
)


def test_compute_monitor_interval_transitions_from_fast_to_medium_to_slow() -> None:
    assert _compute_monitor_interval(0) == MONITOR_FAST_INTERVAL_SECONDS
    assert _compute_monitor_interval(MONITOR_IDLE_TO_MEDIUM_ROUNDS - 1) == MONITOR_FAST_INTERVAL_SECONDS
    assert _compute_monitor_interval(MONITOR_IDLE_TO_MEDIUM_ROUNDS) == MONITOR_MEDIUM_INTERVAL_SECONDS
    assert _compute_monitor_interval(MONITOR_IDLE_TO_SLOW_ROUNDS - 1) == MONITOR_MEDIUM_INTERVAL_SECONDS
    assert _compute_monitor_interval(MONITOR_IDLE_TO_SLOW_ROUNDS) == MONITOR_SLOW_INTERVAL_SECONDS
