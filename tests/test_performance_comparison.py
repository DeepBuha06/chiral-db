# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for the logical-vs-direct performance comparison helpers."""

from __future__ import annotations

import pytest

from scripts.performance_comparison import (
    PROFILE_SCENARIOS,
    ScenarioResult,
    _build_direct_multi_entity_update_statements,
    _build_direct_nested_read_sql,
    _build_logical_multi_entity_update_request,
    _build_logical_nested_read_request,
    _build_parser,
    _get_scenario_runners,
    _parse_sizes,
    _render_summary_markdown,
)
from src.chiral.db.performance import BackendDistribution, OperationSummary


def _build_summary(*, latency: float, throughput: float, rows: int = 10) -> OperationSummary:
    return OperationSummary(
        operation="read",
        phase="logical",
        runs=3,
        average_latency_seconds=latency,
        p50_latency_seconds=latency,
        p95_latency_seconds=latency,
        throughput_ops_per_second=throughput,
        rows_processed=rows,
        rows_inserted=rows,
        metadata_lookups=0,
        backend_distribution=BackendDistribution(sql_rows=rows, jsonb_rows=0, child_rows=0),
    )


def test_parse_sizes_rejects_invalid_input() -> None:
    """Workload size parsing should reject empty and non-positive values."""
    with pytest.raises(ValueError, match="At least one workload size"):
        _parse_sizes("   ")

    with pytest.raises(ValueError, match="positive"):
        _parse_sizes("10,0")


def test_nested_read_builder_uses_jsonb_fields() -> None:
    """Nested read helpers should target overflow_data JSONB fields."""
    request = _build_logical_nested_read_request("session-a", 25)
    sql = _build_direct_nested_read_sql()

    assert request["select"] == ["username", "overflow_data.profile", "overflow_data.events"]
    assert request["limit"] == 25
    assert "\"overflow_data\"->'profile'" in sql
    assert "\"overflow_data\"->'events'" in sql


def test_multi_entity_update_builder_captures_parent_and_jsonb_updates() -> None:
    """Multi-entity update helpers should touch SQL and JSONB state together."""
    request = _build_logical_multi_entity_update_request("session-a", 7)
    statements = _build_direct_multi_entity_update_statements("session-a", 7)

    assert request["updates"]["username"] == "framework_user_7"
    assert request["updates"]["overflow_data.profile"] == {"city": "logical_city_7", "score": 7}
    assert len(statements) == 2
    assert "jsonb_set" in statements[1][0]
    assert statements[0][1]["username"] == "direct_user_7"
    assert statements[1][1]["profile"] == '{"city": "direct_city_7", "score": 7}'


def test_scenario_result_as_dict_reports_overhead() -> None:
    """Scenario summaries should expose latency and throughput deltas."""
    logical = _build_summary(latency=0.8, throughput=12.5)
    direct = _build_summary(latency=0.5, throughput=20.0)
    result = ScenarioResult(scenario="user_read", workload_size=25, logical=logical, direct=direct)

    payload = result.as_dict()

    assert payload["scenario"] == "user_read"
    assert payload["workload_size"] == 25
    assert payload["comparison"]["latency_overhead_seconds"] == pytest.approx(0.3)
    assert payload["comparison"]["latency_overhead_percent"] == pytest.approx(60.0)
    assert payload["comparison"]["throughput_delta_ops_per_second"] == pytest.approx(-7.5)


def test_domain_profile_includes_nested_and_multi_entity_only() -> None:
    """Domain profile should focus on nested and multi-entity scenarios."""
    runners = _get_scenario_runners("domain")
    scenario_names = [name for name, _, _ in runners]

    assert scenario_names == PROFILE_SCENARIOS["domain"]


def test_parser_defaults_to_full_profile_with_flat_reads() -> None:
    """Default profile should include the flat user read scenario in comparisons."""
    parser = _build_parser()
    args = parser.parse_args(["--session-id", "session-a"])
    runners = _get_scenario_runners(args.profile)
    scenario_names = [name for name, _, _ in runners]

    assert args.profile == "full"
    assert scenario_names == PROFILE_SCENARIOS["full"]


def test_summary_markdown_mentions_profile_and_win_counts() -> None:
    """Summary output should include profile text and logical win counters."""
    logical = _build_summary(latency=0.4, throughput=25.0)
    direct = _build_summary(latency=0.5, throughput=20.0)
    result = ScenarioResult(scenario="nested_read", workload_size=25, logical=logical, direct=direct)

    markdown = _render_summary_markdown([result], profile="domain")

    assert "Profile: Domain-focused profile" in markdown
    assert "Logical latency wins: 1/1" in markdown
    assert "Logical throughput wins: 1/1" in markdown
    assert "highly_nested_read" in markdown
