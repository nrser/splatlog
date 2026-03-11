"""Time/date formatting with sub-second directives.

Extends {py:meth}`datetime.datetime.strftime` with:

-   `%3f` — milliseconds, zero-padded to 3 digits

The standard `%f` (microseconds, 6 digits) continues to work as it's handled
by {py:class}`datetime.datetime` itself.

The implementation follows the same strategy Python uses for `%f`: pre-process
the format string to replace custom directives before delegating to
{py:meth}`datetime.datetime.strftime`.

Examples
--------

>>> from datetime import datetime

>>> t = datetime(2026, 3, 10, 14, 23, 45, 123_456)

Just milliseconds:

>>> strftime(t, "%3f")
'123'

Mixed with standard directives:

>>> strftime(t, "%H:%M:%S.%3f")
'14:23:45.123'

Standard ``%f`` (microseconds) still works:

>>> strftime(t, "%H:%M:%S.%f")
'14:23:45.123456'

Full date-time:

>>> strftime(t, "%Y-%m-%d %H:%M:%S.%3f")
'2026-03-10 14:23:45.123'

No custom directives — passes through to ``datetime.strftime``:

>>> strftime(t, "%X")
'14:23:45'

"""

from __future__ import annotations

import datetime as dt


def strftime(t: dt.datetime, fmt: str) -> str:
    """Format a `datetime` with sub-second directives.

    See module docstring for details and examples.
    """
    if "%3f" in fmt:
        fmt = fmt.replace("%3f", f"{t.microsecond // 1000:03d}")
    return t.strftime(fmt)
