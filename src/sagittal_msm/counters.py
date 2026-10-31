# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Operation counting, split by algorithm phase.

Algorithms never count anything themselves. They call group operations inside
`with counter.phase("...")` blocks, and the group records each operation against the
current phase. That keeps the counts tied to the code that actually runs.
"""

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager

DEFAULT_PHASE = "other"


class OpCounter:
    """Counts operations by (phase, operation name)."""

    def __init__(self) -> None:
        self.counts: dict[str, Counter[str]] = {}
        self._phase = DEFAULT_PHASE

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        """Attribute operations inside the block to phase `name`. Phases don't nest."""
        previous, self._phase = self._phase, name
        try:
            yield
        finally:
            self._phase = previous

    def record(self, op: str, n: int = 1) -> None:
        self.counts.setdefault(self._phase, Counter())[op] += n

    def total(self, op: str | None = None, phase: str | None = None) -> int:
        """Total count, optionally limited to one operation and/or one phase."""
        phases = [self.counts.get(phase, Counter())] if phase else list(self.counts.values())
        if op is None:
            return sum(sum(c.values()) for c in phases)
        return sum(c[op] for c in phases)

    def reset(self) -> None:
        self.counts.clear()

    def as_dict(self) -> dict[str, dict[str, int]]:
        return {phase: dict(ops) for phase, ops in self.counts.items()}
