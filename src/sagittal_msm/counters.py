# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Operation counting, split by algorithm phase.

Algorithms never count anything themselves. They call group operations inside
`with counter.phase("...")` blocks, and the group records each operation against the
current phase. That keeps the counts tied to the code that actually runs.

A counter can have linked counters that follow its phase, pausing and resets. Real curves use
this to count field operations (multiplications, squarings, ...) separately from group
operations.
"""

from collections import Counter
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager

DEFAULT_PHASE = "other"


class OpCounter:
    """Counts operations by (phase, operation name)."""

    def __init__(self) -> None:
        self.counts: dict[str, Counter[str]] = {}
        self.linked: list[OpCounter] = []
        self._phase = DEFAULT_PHASE
        self._paused = 0

    def link(self, other: "OpCounter") -> None:
        self.linked.append(other)

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        """Attribute operations inside the block to phase `name`. Phases don't nest."""
        previous, self._phase = self._phase, name
        with ExitStack() as stack:
            for other in self.linked:
                stack.enter_context(other.phase(name))
            try:
                yield
            finally:
                self._phase = previous

    @contextmanager
    def paused(self) -> Iterator[None]:
        """Count nothing inside the block. For building inputs and checking answers."""
        self._paused += 1
        with ExitStack() as stack:
            for other in self.linked:
                stack.enter_context(other.paused())
            try:
                yield
            finally:
                self._paused -= 1

    def record(self, op: str, n: int = 1) -> None:
        if not self._paused:
            self.counts.setdefault(self._phase, Counter())[op] += n

    def total(self, op: str | None = None, phase: str | None = None) -> int:
        """Total count, optionally limited to one operation and/or one phase."""
        phases = [self.counts.get(phase, Counter())] if phase else list(self.counts.values())
        if op is None:
            return sum(sum(c.values()) for c in phases)
        return sum(c[op] for c in phases)

    def reset(self) -> None:
        self.counts.clear()
        for other in self.linked:
            other.reset()

    def as_dict(self) -> dict[str, dict[str, int]]:
        return {phase: dict(ops) for phase, ops in self.counts.items()}
