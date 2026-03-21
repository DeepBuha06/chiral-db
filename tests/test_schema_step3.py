# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Step 3 schema materialization helper tests."""

from src.chiral.db.schema import _analysis_type_to_sql_type, _normalize_child_column_types, get_decomposition_plan


def test_get_decomposition_plan_returns_defaults() -> None:
    """Missing decomposition metadata should produce a default empty plan."""
    plan = get_decomposition_plan({"temperature": {"target": "sql"}})
    assert plan["version"] == 1
    assert plan["parent_table"] == "chiral_data"
    assert plan["entities"] == []


def test_get_decomposition_plan_extracts_metadata_shape() -> None:
    """Decomposition plan should be extracted from analysis metadata envelope."""
    analysis = {
        "temperature": {"target": "sql", "type": "float"},
        "__analysis_metadata__": {
            "decomposition_plan": {
                "version": 1,
                "parent_table": "chiral_data",
                "entities": [
                    {
                        "source_field": "comments",
                        "child_table": "chiral_data_comments",
                        "child_columns": ["text", "time"],
                    }
                ],
            }
        },
    }

    plan = get_decomposition_plan(analysis)
    assert plan["version"] == 1
    assert plan["parent_table"] == "chiral_data"
    assert len(plan["entities"]) == 1
    assert plan["entities"][0]["source_field"] == "comments"


def test_analysis_type_to_sql_type_mapping() -> None:
    """Known inferred analysis types should map to native SQL types."""
    assert _analysis_type_to_sql_type("int") == "INTEGER"
    assert _analysis_type_to_sql_type("float") == "DOUBLE PRECISION"
    assert _analysis_type_to_sql_type("bool") == "BOOLEAN"
    assert _analysis_type_to_sql_type("str") == "TEXT"
    assert _analysis_type_to_sql_type("date") == "TIMESTAMP"
    assert _analysis_type_to_sql_type("unknown") == "TEXT"


def test_normalize_child_column_types_sanitizes_names_and_defaults() -> None:
    """Child column type map should normalize column names and keep only valid string entries."""
    entity = {
        "child_column_types": {
            "Event Time": "timestamp",
            "Score": "float",
            "is_active": "bool",
            "bad_obj": {"type": "int"},
        }
    }

    normalized = _normalize_child_column_types(entity)

    assert normalized["event_time"] == "TIMESTAMP"
    assert normalized["score"] == "DOUBLE PRECISION"
    assert normalized["is_active"] == "BOOLEAN"
    assert "bad_obj" not in normalized
