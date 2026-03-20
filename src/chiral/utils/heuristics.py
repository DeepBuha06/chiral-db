# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Mathematical heuristics for data analysis."""

import math
from collections import Counter
from typing import Any


def _get_type_name(value: object) -> str:
    """Get normalized type name for a value.

    Args:
        value: The value to get type name for.

    Returns:
        String name of the type.

    """
    if value is None:
        return "NULL"
    # bool must be checked before int since bool is subclass of int
    type_map = {
        bool: "BOOLEAN",
        int: "INTEGER",
        float: "FLOAT",
        str: "STRING",
        dict: "DICT",
        list: "LIST",
    }
    for type_cls, type_name in type_map.items():
        if isinstance(value, type_cls):
            return type_name
    return type(value).__name__.upper()


def calculate_entropy(data: list[Any]) -> float:
    """Calculate the Shannon entropy of the types in a list of values (Type Entropy).

    Htype(F) = -∑ p(t) ⋅ log2 p(t)  where t ∈ T (set of types)

    Args:
        data: List of values (mixed types allowed).

    Returns:
        Float value representing type entropy:
        - H = 0: All values have the same type (Perfect Stability) → SQL candidate
        - H > 0: Type drift/mixed types → MongoDB candidate

    Notes:
        - NULL/None is treated as a distinct type for entropy calculation
        - This captures "Presence Stability"

    """
    if not data:
        return 0.0

    # Count types, treating None as a distinct type
    type_counts = Counter(_get_type_name(value) for value in data)

    total_count = len(data)

    entropy = 0.0
    for count in type_counts.values():
        probability = count / total_count
        if probability > 0:
            entropy -= probability * math.log2(probability)

    return entropy
