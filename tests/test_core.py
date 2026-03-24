import pytest
from compactor.core import SmartCompactor

@pytest.fixture
def compactor():
    settings = {
        "dedup_window_seconds": 5,
        "error_threshold": 2,
        "log_pattern": r'^(?P<ts>\S+)\s+(?P<level>\S+)\s+(?P<action>login|logout)\s+(?P<user>\S+)$',
        "output_template": "{ts} [{level}] {fields}",
        "aliases": {"user_id": "user"},
        "level_overrides": [
            {"field": "code", "min": 500, "max": 599, "new_level": "ERROR"}
        ]
    }
    return SmartCompactor(settings)

def test_scenario_1_regex_match(compactor):
    log_stream = ["2024-01-01T10:00:00 INFO login alice"]
    results = list(compactor.compact_stream(log_stream))
    assert len(results) == 1
    assert results[0] == "2024-01-01T10:00:00 [INFO] action=login user=alice"

def test_scenario_2_key_value_fallback(compactor):
    log_stream = ["2024-01-01T10:05:00 INFO action=upload user_id=bob code=200"]
    results = list(compactor.compact_stream(log_stream))
    assert len(results) == 1
    assert results[0] == "2024-01-01T10:05:00 [INFO] action=upload code=200 user=bob"

def test_scenario_3_raw_pass_through(compactor):
    log_stream = [
        "Traceback (most recent call last):",
        "  File \"app.py\", line 10, in <module>",
        "ZeroDivisionError: division by zero"
    ]
    results = list(compactor.compact_stream(log_stream))
    assert len(results) == 3
    assert results[0] == "Traceback (most recent call last):"

def test_deduplication_and_escalation(compactor):
    log_stream = [
        "2024-01-01T11:00:00 INFO action=upload code=500", 
        "2024-01-01T11:00:02 INFO action=upload code=500"
    ]
    results = list(compactor.compact_stream(log_stream))
    assert len(results) == 1
    assert results[0] == "2024-01-01T11:00:00~11:00:02 [CRITICAL] action=upload code=500 (x2)"


def test_streaming_order_emits_earliest_start_ts_first(compactor):
    """Later-start group completes while an earlier-start group is still open; EOF drains in start_ts order."""
    # B's second line at +5s from B's start (window is 5; not > 5 so it merges). A stays open until EOF.
    log_stream = [
        "2024-01-01T10:00:00 INFO login alice",
        "2024-01-01T10:00:02 INFO login bob",
        "2024-01-01T10:00:07 INFO login bob",
    ]
    results = list(compactor.compact_stream(log_stream))
    assert len(results) == 2
    assert results[0] == "2024-01-01T10:00:00 [INFO] action=login user=alice"
    assert results[1] == (
        "2024-01-01T10:00:02~10:00:07 [INFO] action=login user=bob (x2)"
    )


def test_deferred_flush_does_not_emit_before_earlier_open_group(compactor):
    """B's window expires mid-stream; B sits in pending until A (earlier start_ts) closes at EOF."""
    log_stream = [
        "2024-01-01T10:00:00 INFO login alice",
        "2024-01-01T10:00:02 INFO login bob",
        "2024-01-01T10:00:10 INFO login bob",
    ]
    results = list(compactor.compact_stream(log_stream))
    assert len(results) == 3
    assert results[0] == "2024-01-01T10:00:00 [INFO] action=login user=alice"
    assert results[1] == "2024-01-01T10:00:02 [INFO] action=login user=bob"
    assert results[2] == "2024-01-01T10:00:10 [INFO] action=login user=bob"


def test_different_levels_same_fields_remain_separate(compactor):
    """Stable signature: level is part of the key; same fields, different levels do not merge."""
    log_stream = [
        "2024-01-01T12:00:00 INFO login alice",
        "2024-01-01T12:00:01 WARN login alice",
    ]
    results = list(compactor.compact_stream(log_stream))
    assert len(results) == 2
    assert " [INFO] " in results[0]
    assert " [WARN] " in results[1]


def test_alias_conflict_passes_through_raw_line(compactor):
    log_stream = [
        "2024-01-01T13:00:00 INFO user_id=1 user=2 code=200",
    ]
    results = list(compactor.compact_stream(log_stream))
    assert len(results) == 1
    assert results[0] == "2024-01-01T13:00:00 INFO user_id=1 user=2 code=200"