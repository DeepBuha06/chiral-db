# Copyright (c) 2026 Chiral Contributors
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Monotonic Clock for Transaction Time generation.

Implements the collision resolution strategy: t_trans = max(Clock_now, Last_assigned + epsilon).
"""

import threading
import time
from typing import cast


class MonotonicClock:
    """Singleton clock ensuring monotonically increasing timestamps."""

    _instance = None
    _lock = threading.Lock()
    _last_assigned = 0.0

    @classmethod
    def get_instance(cls) -> "MonotonicClock":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
            if cls._instance is None:
                msg = "Failed to initialize MonotonicClock singleton"
                raise RuntimeError(msg)
        return cast("MonotonicClock", cls._instance)

    def get_transaction_time(self) -> float:
        """Generate a unique, monotonically increasing timestamp.

        Returns unix timestamp as float.
        """
        with self._lock:
            now = time.time()
            # Epsilon = 1 microsecond = 1e-6 (standard precision for many DBs)
            epsilon = 1e-6

            t_trans = max(now, self._last_assigned + epsilon)

            self._last_assigned = t_trans
            return t_trans
