from __future__ import annotations

from functools import total_ordering
from typing import Iterator, overload, Any


@total_ordering
class Interval:
    __slots__ = ("_range",)

    # --- construction -------------------------------------------------

    @overload
    def __init__(self, rng: range, /) -> None: ...

    # `range` takes no keyword arguments, so we mirror that

    @overload
    def __init__(self, start: int, stop: int, /) -> None: ...

    @overload
    def __init__(self, start: int, stop: int, step: int, /) -> None: ...

    def __init__(self, *args: Any) -> None:
        if len(args) == 1 and isinstance(args[0], range):
            self._range = args[0]
        else:
            self._range = range(*args)

    @classmethod
    def from_range(cls, r: range) -> "Interval":
        return cls(r)

    # --- range-like API -----------------------------------------------

    @property
    def start(self) -> int:
        return self._range.start

    @property
    def stop(self) -> int:
        return self._range.stop

    @property
    def step(self) -> int:
        return self._range.step

    @property
    def length(self) -> int:
        return len(self._range)

    def __len__(self) -> int:
        return len(self._range)

    def __iter__(self) -> Iterator[int]:
        return iter(self._range)

    def __contains__(self, value: int) -> bool:
        return value in self._range

    def __getitem__(self, idx: int) -> int:
        return self._range[idx]

    def to_range(self) -> range:
        return self._range

    # --- ordering ------------------------------------------------------

    def _sort_key(self) -> tuple[int, int, int]:
        # step included to make ordering total and deterministic
        return (self.start, self.length, self.step)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Interval):
            return self._sort_key() < other._sort_key()
        if isinstance(other, range):
            return self._sort_key() < (other.start, len(other), other.step)
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Interval):
            return self._range == other._range
        if isinstance(other, range):
            return self._range == other
        return NotImplemented

    # --- representation ------------------------------------------------

    def __repr__(self) -> str:
        return f"Interval({self.start}, {self.stop}, {self.step})"
