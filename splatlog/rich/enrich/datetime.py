"""
{py:mod}`datetime` enrichment.

Instead of highlighting an already-formatted string with a regex (which can't
reliably style separators or repeated components — see
`rich.highlighter.ISO8601Highlighter`), we tokenize our own template via
`splatlog.lib.text.iter_strftime_segments` (or `iter_timedelta_segments`) and
style each component precisely as we build the `Text`.
"""

from __future__ import annotations
from collections import abc
import datetime as dt

from rich.text import Text

from splatlog.lib.text import (
    FmtOpts,
    iter_strftime_segments,
    iter_timedelta_segments,
)

from .enrichment import EnrichOpts, enrichment


_DATETIME_STYLE = "datetime"
"""Base style-name prefix for {py:class}`~datetime.datetime`,
{py:class}`~datetime.date`, and {py:class}`~datetime.time` component styling;
each component is styled `{_DATETIME_STYLE}.{component}` (see
{py:data}`~splatlog.lib.text.datetime.STRFTIME_COMPONENTS` and the theme).
"""

_TIMEDELTA_STYLE = "timedelta"
"""Base style-name prefix for {py:class}`~datetime.timedelta` component styling;
each component is styled `{_TIMEDELTA_STYLE}.{component}`.
"""


def _enrich_segments(
    segments: abc.Iterable[tuple[str, str]], *, base: str
) -> Text:
    """Build a styled {py:class}`~rich.text.Text` from `(text, component)`
    `segments`, styling each `{base}.{component}` and stripping surrounding
    whitespace to match the plain formatters' `.strip()`."""
    items = [(text, component) for text, component in segments if text]

    # Keep a leading sign attached to the body, trimming whitespace *after* it
    # so an omitted optional leading term doesn't leave a gap (e.g. `- 1s`).
    lead = 0
    while lead < len(items) and items[lead][1] == "sign":
        lead += 1
    head, body = items[:lead], items[lead:]

    while body and not body[0][0].strip():
        body.pop(0)
    while body and not body[-1][0].strip():
        body.pop()
    if body:
        head_text, head_component = body[0]
        body[0] = (head_text.lstrip(), head_component)
        tail_text, tail_component = body[-1]
        body[-1] = (tail_text.rstrip(), tail_component)

    items = head + body

    text = Text(end="")
    text.append_tokens(
        (item_text, f"{base}.{component}") for item_text, component in items
    )
    return text


def enrich_strftime(
    value: dt.date | dt.time, fmt_str: str, *, base: str = _DATETIME_STYLE
) -> Text:
    """
    Build a styled {py:class}`~rich.text.Text` from a
    {py:meth}`~datetime.datetime.strftime` template, styling each component
    `{base}.{component}` (e.g. `datetime.year`, `datetime.sep`).

    The visible content is identical to
    {py:func}`~splatlog.lib.text.datetime.fmt_datetime` (and friends):
    surrounding whitespace is stripped so a trailing empty `%Z` on a naive value
    doesn't leave a dangling separator.

    ## Examples

    Every component — including the separators the ISO 8601 highlighter can't
    reach — carries its own style:

    ```pycon
    >>> import datetime as dt
    >>> text = enrich_strftime(dt.date(2026, 3, 10), "%Y-%m-%d")
    >>> text.plain
    '2026-03-10'

    >>> for span in text.spans:
    ...     print(f"{span.start:>2}..{span.end:<2} {span.style}")
     0..4  datetime.year
     4..5  datetime.sep
     5..7  datetime.month
     7..8  datetime.sep
     8..10 datetime.day

    ```
    """
    return _enrich_segments(iter_strftime_segments(value, fmt_str), base=base)


def enrich_timedelta(
    value: dt.timedelta,
    fmt_str: str = FmtOpts.td_fmt,
    *,
    base: str = _TIMEDELTA_STYLE,
) -> Text:
    """
    Build a styled {py:class}`~rich.text.Text` from a timedelta template (see
    {py:func}`~splatlog.lib.text.timedelta.iter_timedelta_segments`), styling
    each component `{base}.{component}` (e.g. `timedelta.hour`,
    `timedelta.sign`).

    ## Examples

    ```pycon
    >>> import datetime as dt
    >>> text = enrich_timedelta(
    ...     -dt.timedelta(hours=1, seconds=45), "[%-Hh] [%-Mm] [%-Ss]"
    ... )
    >>> text.plain
    '-1h 0m 45s'

    >>> for span in text.spans:
    ...     print(f"{span.start:>2}..{span.end:<2} {span.style}")
     0..1  timedelta.sign
     1..2  timedelta.hour
     2..3  timedelta.text
     3..4  timedelta.space
     4..5  timedelta.minute
     5..6  timedelta.text
     6..7  timedelta.space
     7..9  timedelta.second
     9..10 timedelta.text

    ```
    """
    return _enrich_segments(iter_timedelta_segments(value, fmt_str), base=base)


@enrichment
def enrich_datetime(value: dt.datetime, opts: EnrichOpts) -> Text:
    """
    Enrich a {py:class}`datetime.datetime` using {py:attr}`FmtOpts.dt_fmt`.

    ```pycon
    >>> import datetime as dt
    >>> enrich_datetime(
    ...     dt.datetime(2026, 3, 10, 14, 23, 45, 123_456)
    ... ).plain
    '2026-03-10 14:23:45.123'

    ```
    """
    return enrich_strftime(value, opts.dt_fmt)


@enrichment
def enrich_date(value: dt.date, opts: EnrichOpts) -> Text:
    """
    Enrich a {py:class}`datetime.date` using {py:attr}`FmtOpts.d_fmt`.

    ```pycon
    >>> import datetime as dt
    >>> enrich_date(dt.date(2026, 3, 10)).plain
    '2026-03-10'

    ```
    """
    return enrich_strftime(value, opts.d_fmt)


@enrichment
def enrich_time(value: dt.time, opts: EnrichOpts) -> Text:
    """
    Enrich a {py:class}`datetime.time` using {py:attr}`FmtOpts.tm_fmt`.

    ```pycon
    >>> import datetime as dt
    >>> enrich_time(dt.time(14, 23, 45, 123_456)).plain
    '14:23:45.123'

    ```
    """
    return enrich_strftime(value, opts.tm_fmt)
