"""
Manage _verbosity_, which is stored as a module-level private variable, and is
hence global to the process.
"""

from __future__ import annotations

from splatlog.locking import lock
from splatlog.typings import Verbosity, to_verbosity


_verbosity: Verbosity = Verbosity(0)
"""
Current {py:type}`splatlog.typing.Verbosity`, defaults to `0`.
"""


def get_verbosity() -> Verbosity:
    """
    Get the current _verbosity_.

    > 📝 NOTE — Thread Safety
    >
    > There is no locking around the read, it simply returns whatever value is
    > visible to the thread at the time. This is because `VerbosityLevelsFilter`
    > reads on every filter, so we want it to be fast.
    >
    > This does mean that the various logger levels are not guaranteed to be in
    > a state consistent near calls to {py:func}`set_verbosity`.
    >
    """
    return _verbosity


def set_verbosity(verbosity: Verbosity) -> None:
    """
    Set the _verbosity_, which is used by {py:class}`splatlog.levels.Filter`.
    """
    global _verbosity

    verbosity = to_verbosity(verbosity)

    # Lock around this so that two coincident calls from different threads don't
    # execute this block at the same time, which could result in logger levels
    # that are inconsistent with the final _verbosity_ value.
    with lock():
        _verbosity = verbosity
