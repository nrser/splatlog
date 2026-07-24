"""
{py:class}`~datetime.datetime` formatting.

`strftime` templates are tokenized into typed segments so that the plain
formatters below and the Rich enrichment in {py:mod}`splatlog.rich.enrich`
render from a single source of truth. Each directive maps to a "component"
name (used as a style suffix when enriching, e.g. `%Y` → `year` →
`datetime.year`); the literal runs between directives are tagged `"sep"`.
"""

from collections.abc import Iterator
import re
import datetime as dt

from .formatter import formatter, FmtOpts


STRFTIME_COMPONENTS: dict[str, str] = {
    # Weekday / day-of-week
    "a": "weekday",
    "A": "weekday",
    "w": "weekday",
    "u": "weekday",
    # Day of month
    "d": "day",
    # Month
    "b": "month",
    "B": "month",
    "m": "month",
    # Year
    "y": "year",
    "Y": "year",
    "G": "year",
    # Hour
    "H": "hour",
    "I": "hour",
    # AM/PM
    "p": "period",
    # Minute
    "M": "minute",
    # Second
    "S": "second",
    # Sub-second
    "f": "fraction",
    # Time zone
    "z": "tz",
    "Z": "tz",
    # Day of year
    "j": "ordinal",
    # Week of year
    "U": "week",
    "W": "week",
    "V": "week",
    # Locale composites
    "c": "datetime",
    "x": "date",
    "X": "time",
}
"""Maps a {py:meth}`~datetime.datetime.strftime` directive letter to the
"component" name used as a style suffix when enriching (see
{py:func}`iter_strftime_segments`)."""

_STRFTIME_DIRECTIVE_RE = re.compile(
    r"""
      %3f                       # Custom: milliseconds, zero-padded to 3 digits
    | %[-_0^#]*[EO]?[a-zA-Z]    # A directive, w/ optional flags & `E`/`O` locale
    | %%                        # An escaped, literal percent sign
    """,
    re.VERBOSE,
)
"""Matches a single {py:meth}`~datetime.datetime.strftime` directive.

Because we render each directive individually we must recognize the full set of
directives (plus platform flag/locale modifiers like `%-d` or `%Ec`) so that any
valid template tokenizes correctly, not just the ones in our defaults. The
custom `%3f` is matched first so it never reaches the platform `strftime`.
"""


def iter_strftime_segments(
    value: dt.date | dt.time, fmt: str
) -> Iterator[tuple[str, str]]:
    """Tokenize a {py:meth}`~datetime.datetime.strftime` template `fmt` against
    `value`, yielding `(text, component)` pairs.

    Each directive is rendered individually — which is safe, since `strftime`
    directives are context-free — so callers know exactly which component each
    slice of output belongs to. `component` is the name from
    {py:data}`STRFTIME_COMPONENTS` for directives (or `"fraction"` for the custom
    `%3f`), and `"sep"` for literal runs (including an escaped `%%`).

    ## Examples

    ```pycon
    >>> import datetime as dt
    >>> t = dt.datetime(2026, 3, 10, 14, 23, 45, 123_456)

    >>> list(iter_strftime_segments(t, "%Y-%m-%d"))
    [('2026', 'year'), ('-', 'sep'), ('03', 'month'), ('-', 'sep'), ('10', 'day')]

    ```

    The custom `%3f` yields milliseconds; `%%` is a literal separator:

    ```pycon
    >>> list(iter_strftime_segments(t, "%S.%3f%%"))
    [('45', 'second'), ('.', 'sep'), ('123', 'fraction'), ('%', 'sep')]

    ```

    Empty directives (e.g. `%Z` on a naive value) yield empty text, left for the
    caller to handle:

    ```pycon
    >>> list(iter_strftime_segments(t, "%H:%M %Z"))
    [('14', 'hour'), (':', 'sep'), ('23', 'minute'), (' ', 'sep'), ('', 'tz')]

    ```
    """
    pos = 0
    for match in _STRFTIME_DIRECTIVE_RE.finditer(fmt):
        if match.start() > pos:
            yield fmt[pos : match.start()], "sep"

        token = match.group()
        if token == "%3f":
            yield f"{getattr(value, 'microsecond', 0) // 1000:03d}", "fraction"
        elif token == "%%":
            yield "%", "sep"
        else:
            yield (
                value.strftime(token),
                STRFTIME_COMPONENTS.get(token[-1], "sep"),
            )

        pos = match.end()

    if pos < len(fmt):
        yield fmt[pos:], "sep"


def _strftime(value: dt.date | dt.time, fmt: str) -> str:
    """Render a `strftime` template the same way {py:func}`iter_strftime_segments`
    tokenizes it, joining the segments and stripping surrounding whitespace (so
    trailing empty directives like `%Z` on a naive value don't leave a dangling
    separator)."""
    return "".join(
        text for text, _ in iter_strftime_segments(value, fmt)
    ).strip()


@formatter
def fmt_datetime(t: dt.datetime, opts: FmtOpts) -> str:
    """
    Format a {py:class}`datetime.datetime` with sub-second directives.

    Wraps {py:meth}`datetime.datetime.strftime` and adds support for:

    -   `%3f` — milliseconds, zero-padded to 3 digits.

    The standard `%f` (microseconds, 6 digits) continues to work as it's handled
    by {py:class}`~datetime.datetime` itself.

    The template is tokenized by {py:func}`iter_strftime_segments` — which
    renders each directive individually and resolves the custom `%3f` — so the
    plain output here stays byte-for-byte identical to the Rich enrichment in
    {py:mod}`splatlog.rich.enrich`.

    Surrounding whitespace is stripped from the result, allowing formats like
    `"%Y-%m-%d %H:%M:%S.%3f %Z"` to not produce a trailing space when used with
    naive {py:class}`~datetime.datetime` instances.

    Examples
    --------------------------------------------------------------------------

    We'll be demonstrating on the {py:class}`~datetime.datetime` `t`, which we
    set to the _naive_ (without timezone) moment of `March 14, 2026` at
    `14:23.123456` — that's `2:23PM` at `123,456` microseconds past the
    minute-mark.

        >>> import datetime as dt

        >>> t = dt.datetime(2026, 3, 10, 14, 23, 45, 123_456)
        >>> t.isoformat()
        '2026-03-10T14:23:45.123456'

    Default format:

        >>> fmt_datetime(t)
        '2026-03-10 14:23:45.123'

    Extract just the milliseconds:

        >>> fmt_datetime(t, dt_fmt="%3f ms")
        '123 ms'

    Mixed with standard directives:

        >>> fmt_datetime(t, dt_fmt="%H:%M:%S.%3f")
        '14:23:45.123'

    Standard `%f` (microseconds) still works:

        >>> fmt_datetime(t, dt_fmt="%H:%M:%S.%f")
        '14:23:45.123456'

    No custom directives — passes through to
    {py:meth}`~datetime.datetime.strftime`:

        >>> fmt_datetime(t, dt_fmt="%X")
        '14:23:45'

    With timezone:

        >>> fmt_datetime(
        ...     dt.datetime(2026, 3, 10, 14, 23, 45, 123_456, dt.timezone.utc)
        ... )
        '2026-03-10 14:23:45.123 UTC'

        >>> fmt_datetime(
        ...     dt.datetime(2026, 3, 10, 14, 23, 45, 123_456, dt.timezone.utc)
        ... )
        '2026-03-10 14:23:45.123 UTC'

    """
    return _strftime(t, opts.dt_fmt)


@formatter
def fmt_date(d: dt.date, opts: FmtOpts) -> str:
    """
    Format a {py:class}`datetime.date`.

    Uses {py:attr}`FmtOpts.d_fmt` as the format string, defaulting to
    ISO 8601 (`%Y-%m-%d`).

    Examples
    --------------------------------------------------------------------------

    ```pycon
    >>> import datetime as dt

    >>> fmt_date(dt.date(2026, 3, 10))
    '2026-03-10'

    >>> fmt_date(dt.date(2026, 3, 10), d_fmt="%m/%d/%Y")
    '03/10/2026'

    >>> fmt_date(dt.date(2026, 12, 25), d_fmt="%B %d, %Y")
    'December 25, 2026'

    ```
    """
    return _strftime(d, opts.d_fmt)


@formatter
def fmt_time(t: dt.time, opts: FmtOpts) -> str:
    """
    Format a {py:class}`datetime.time` with sub-second directives.

    Uses {py:attr}`FmtOpts.tm_fmt` as the format string, defaulting to
    `%H:%M:%S.%3f`. Supports the `%3f` directive for milliseconds, same
    as {py:func}`fmt_datetime`.

    Examples
    --------------------------------------------------------------------------

    ```pycon
    >>> import datetime as dt

    >>> fmt_time(dt.time(14, 23, 45, 123_456))
    '14:23:45.123'

    >>> fmt_time(dt.time(14, 23, 45), tm_fmt="%I:%M %p")
    '02:23 PM'

    >>> fmt_time(dt.time())
    '00:00:00.000'

    ```

    """
    return _strftime(t, opts.tm_fmt)
