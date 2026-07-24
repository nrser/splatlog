"""{py:class}`datetime.timedelta` formatting — {py:class}`~datetime.timedelta`
has no [`strftime`][], so we define a small format language for it.

[`strftime`]: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior

It reuses the `%H`/`%M`/`%S` directives (plus `%d` for days) and adds fraction
directives `%3f` (milliseconds), `%6f` (microsecond remainder), and `%f` (whole
sub-second microseconds), but adds two things `strftime` lacks — both aimed at
rendering durations whose magnitude isn't known ahead of time:

1.  `[...]` optional groups: omitted unless they contain an "in-range" unit,
    where a unit is in-range when it sits between the smallest and largest
    non-zero unit. So a middle zero (the minutes in `1h 0m 45s`) shows, while
    leading/trailing zeros drop out.

2.  A `-` flag (`%-S`): minimal-width rendering. Without it, whole units are
    zero-padded to their natural width (`%H`/`%M`/`%S` → 2, `%3f` → 3). The
    most-significant unit *present* absorbs everything larger than it, is never
    truncated, and is grouped with thousands separators (`1,234,567h`).

The units form a single ladder — days, hours, minutes, seconds, milliseconds,
microseconds — decomposed greedily over the units *present* in the template.
So `%3f` and `%6f` together split the sub-second remainder hierarchically
(`789ms` + `0µs`, or `0ms` + `12µs`), while `%f` holds the whole sub-second in
microseconds (`789000`).
"""

from collections.abc import Iterator
from itertools import groupby
import re
import datetime as dt

from .datetime import STRFTIME_COMPONENTS
from .formatter import formatter, FmtOpts


type _TdNode = tuple[str, str] | tuple[str, list["_TdNode"]]
"""A parsed template node: `("lit", str)`, `("dir", token)`, or
`("opt", [nodes])` for a `[...]` group."""

# (directive letter, microseconds per unit, natural zero-pad width [`0` = none])
_TD_WHOLE_UNITS: tuple[tuple[str, int, int], ...] = (
    ("d", 86_400_000_000, 0),
    ("H", 3_600_000_000, 2),
    ("M", 60_000_000, 2),
    ("S", 1_000_000, 2),
)

# fraction key → (microseconds per unit, precision). Ordered largest-first so
# `%3f` (milliseconds) decomposes before `%6f` (microseconds). `%3f` and `%6f`
# split the sub-second into a millisecond field and a 3-digit microsecond
# remainder, while `%f` is the whole sub-second as 6-digit microseconds.
_TD_FRACTIONS: dict[str, tuple[int, int]] = {
    "3f": (1_000, 3),
    "6f": (1, 3),
    "f": (1, 6),
}

_TD_WHOLE_WIDTHS: dict[str, int] = {
    letter: width for letter, _size, width in _TD_WHOLE_UNITS
}

_TD_TOKEN_RE = re.compile(r"%-?[36]f|%-?[dHMSf]|%%|\[|\]")
"""Matches a timedelta directive, an escaped `%%`, or a `[`/`]` group bound."""


def _parse_td_template(fmt: str) -> list[_TdNode]:
    """Parse a timedelta template into a tree of {py:data}`_TdNode`."""
    root: list[_TdNode] = []
    stack: list[list[_TdNode]] = [root]
    pos = 0
    for match in _TD_TOKEN_RE.finditer(fmt):
        if match.start() > pos:
            stack[-1].append(("lit", fmt[pos : match.start()]))

        token = match.group()
        if token == "[":
            group: list[_TdNode] = []
            stack[-1].append(("opt", group))
            stack.append(group)
        elif token == "]":
            if len(stack) > 1:
                stack.pop()
            else:
                stack[-1].append(("lit", "]"))
        elif token == "%%":
            stack[-1].append(("lit", "%"))
        else:
            stack[-1].append(("dir", token))

        pos = match.end()

    if pos < len(fmt):
        stack[-1].append(("lit", fmt[pos:]))

    return root


def _td_directive_key(token: str) -> str:
    """The unit key of a directive token (`"%-3f"` → `"3f"`, `"%H"` → `"H"`)."""
    return token[2:] if token.startswith("%-") else token[1:]


def _iter_td_directives(nodes: list[_TdNode]) -> Iterator[str]:
    """Yield every directive token in `nodes`, descending into `opt` groups."""
    for kind, payload in nodes:
        if kind == "dir":
            yield payload  # type: ignore[misc]
        elif kind == "opt":
            yield from _iter_td_directives(payload)  # type: ignore[arg-type]


def _td_decompose(
    td: dt.timedelta, nodes: list[_TdNode]
) -> tuple[dict[str, int], set[str], bool]:
    """Resolve `td` against the units present in `nodes`.

    Returns `(values, in_range, negative)` where `values` maps each present unit
    key to its rendered integer, `in_range` is the set of unit keys between the
    smallest and largest non-zero unit, and `negative` is the sign.

    Two special cases when nothing renders non-zero:

    -   A _true_ zero (`total == 0`) yields its least-significant *whole* unit,
        for a clean `00:00:00` / `0s` with no sub-second `.000`.
    -   A non-zero delta that merely rounds to all-zero (e.g. sub-millisecond)
        yields its least-significant unit — the fraction, if present — so the
        `.000` reveals that _something_ is there.
    """
    present: set[str] = {
        _td_directive_key(t) for t in _iter_td_directives(nodes)
    }

    negative = td < dt.timedelta(0)
    td_abs = abs(td)
    total_us = (
        td_abs.days * 86_400 + td_abs.seconds
    ) * 1_000_000 + td_abs.microseconds

    values: dict[str, int] = {}
    slots: list[str] = []

    remainder = total_us
    for letter, size, _width in _TD_WHOLE_UNITS:
        if letter in present:
            values[letter] = remainder // size
            remainder %= size
            slots.append(letter)

    frac_remainder = total_us % 1_000_000
    for key, (unit_us, _prec) in _TD_FRACTIONS.items():
        if key in present:
            values[key] = frac_remainder // unit_us
            frac_remainder %= unit_us
            slots.append(key)

    nonzero = [i for i, slot in enumerate(slots) if values.get(slot, 0)]
    if nonzero:
        lo, hi = nonzero[0], nonzero[-1]
        in_range = {slots[i] for i in range(lo, hi + 1)}
    elif not slots:
        in_range = set()
    elif total_us == 0:
        # True zero: least-significant *whole* unit (clean `00:00:00` / `0s`).
        whole = [slot for slot in slots if slot not in _TD_FRACTIONS]
        in_range = {(whole or slots)[-1]}
    else:
        # Rounds to all-zero but isn't: reveal it via the least-significant unit
        # (the fraction, giving `.000`).
        in_range = {slots[-1]}

    return values, in_range, negative


def _render_td_directive(token: str, values: dict[str, int]) -> str:
    """Render a single directive `token` from pre-computed `values`."""
    minimal = token.startswith("%-")
    key = _td_directive_key(token)

    if key in _TD_FRACTIONS:
        _unit_us, precision = _TD_FRACTIONS[key]
        value = values.get(key, 0)
        return str(value) if minimal else f"{value:0{precision}d}"

    value = values.get(key, 0)
    width = _TD_WHOLE_WIDTHS[key]
    if minimal or width == 0:
        return f"{value:,d}"
    return f"{value:0{width},d}"


def _td_group_shown(nodes: list[_TdNode], in_range: set[str]) -> bool:
    """Whether an `opt` group renders — i.e. holds an in-range directive."""
    return any(
        _td_directive_key(token) in in_range
        for token in _iter_td_directives(nodes)
    )


_TD_SEP_CHARS = frozenset(":.")
"""Literal characters tagged as separators (`"sep"`). Everything else in a
literal run is whitespace (`"space"`) or free text (`"text"`)."""


def _td_literal_component(char: str) -> str:
    """Classify a single literal `char` as `"sep"`, `"space"`, or `"text"`."""
    if char in _TD_SEP_CHARS:
        return "sep"
    if char.isspace():
        return "space"
    return "text"


def _iter_td_literal_runs(text: str) -> Iterator[tuple[str, str]]:
    """Split a literal run into maximal `(text, component)` sub-runs — tagging
    separators (`:`/`.`) `"sep"`, whitespace `"space"`, and the rest (unit
    designations and other free text) `"text"`."""
    for component, chars in groupby(text, key=_td_literal_component):
        yield "".join(chars), component


def _emit_td_nodes(
    nodes: list[_TdNode], values: dict[str, int], in_range: set[str]
) -> Iterator[tuple[str, str]]:
    for kind, payload in nodes:
        if kind == "lit":
            yield from _iter_td_literal_runs(payload)  # type: ignore[arg-type]
        elif kind == "dir":
            key = _td_directive_key(payload)  # type: ignore[arg-type]
            component = STRFTIME_COMPONENTS.get(key[-1], "sep")
            yield _render_td_directive(payload, values), component  # type: ignore[arg-type]
        elif kind == "opt":
            if _td_group_shown(payload, in_range):  # type: ignore[arg-type]
                yield from _emit_td_nodes(payload, values, in_range)  # type: ignore[arg-type]


def iter_timedelta_segments(
    td: dt.timedelta, fmt: str
) -> Iterator[tuple[str, str]]:
    """Tokenize a timedelta template `fmt` against `td`, yielding
    `(text, component)` pairs (the counterpart to
    {py:func}`iter_strftime_segments`, resolving `[...]` groups and the sign).

    ## Examples

    In-range logic keeps a middle zero but drops the leading/trailing ones:

    ```pycon
    >>> import datetime as dt
    >>> list(iter_timedelta_segments(
    ...     dt.timedelta(hours=1, seconds=45), "[%-Hh] [%-Mm] [%-Ss] [%-3fms]"
    ... ))
    [('1', 'hour'), ('h', 'text'), (' ', 'space'), ('0', 'minute'), ('m', 'text'), (' ', 'space'), ('45', 'second'), ('s', 'text'), (' ', 'space')]

    ```
    """
    nodes = _parse_td_template(fmt)
    values, in_range, negative = _td_decompose(td, nodes)
    if negative:
        yield "-", "sign"
    yield from _emit_td_nodes(nodes, values, in_range)


@formatter
def fmt_timedelta(td: dt.timedelta, opts: FmtOpts) -> str:
    """Format a {py:class}`datetime.timedelta` using the
    {py:attr}`splatlog.lib.text.FmtOpts.td_fmt` template, default:
    `"[%dd] [%H:%M:%S[.%3f]]"`{l=py}.

    ## Template Language

    The {py:class}`~datetime.timedelta` template language was created to
    compliment the C/Python [`strftime`][] language used in
    {py:func}`~splatlog.lib.text.fmt_datetime`,
    {py:func}`~splatlog.lib.text.fmt_date`, and
    {py:func}`~splatlog.lib.text.fmt_time`. It strives for similarity with
    [`strftime`][] templates, while introducing features well-suited for
    producing familiar {py:class}`~datetime.timedelta` formats.

    The {py:class}`~datetime.timedelta` template language consists of:

    1.  _Directives_ — `%`-codes that are replaced with
        {py:class}`~datetime.timedelta` terms; see following table.
    2.  _Optional Groups_ — square-bracket `[...]` spans that are omitted
        unless they contain a directive with non-zero or captive zero (between
        non-zero terms) evaluation.
    3.  _Whitespace_ — leading and trailing spaces are trimmed and repeated
        internal spaces are collapsed to a single space.
    3.  _Literal Text_ — anything else is copied verbatim to the output.

    ### Format Codes

    | Directive | Meaning                   | Example               | Notes |
    | --------- | ------------------------- | --------------------- | ----- |
    | `%d`      | Days                      | `0`, `1,234`          | (1)   |
    | `%H`      | Hours                     | `00`, `12`, `1,234`   | (1)   |
    | `%M`      | Minutes                   | `00`, `12`            |       |
    | `%S`      | Seconds                   | `00`, `12`            |       |
    | `%3f`     | Milliseconds              | `000`, `123`          | (2)   |
    | `%6f`     | Microseconds              | `000`, `123`          | (2)   |
    | `%f`      | Sub-seconds (milli+micro) | `000000`, `123456`    | (2)   |
    | `%-...`   | Minimal-width modifier    | `%-Ss` → `1s`         | (3)   |
    | `[...]`   | Optional group            | `[%dd]` → `1d`        | (4)   |
    | `%%`      | Literal `%`               | `%`                   |       |

    ### Notes

    1.  Larger units are never truncated, so the largest unit present in the
        template will absorb any large units.

        Formatting a multi-day {py:class}`~datetime.timedelta` with a `%d`
        directive shows them as days:

        ```pycon
        >>> from datetime import timedelta

        >>> x = timedelta(days=12)

        >>> fmt_timedelta(x, td_fmt="%dd %Hh %Mm %Ss")
        '12d 00h 00m 00s'

        ```

        If we omit the `%d` directive those days will be displayed as a large
        amount of hours:

        ```
        >>> fmt_timedelta(x, td_fmt="%Hh %Mm %Ss")
        '288h 00m 00s'

        ```

        Removing the `%H` directive shoves the days down into minutes, and
        so-forth:

        ```
        >>> fmt_timedelta(x, td_fmt="%Mm %Ss")
        '17,280m 00s'

        >>> fmt_timedelta(x, td_fmt="%Ss")
        '1,036,800s'

        ```

    2.  `%3f` and `%6f` are directive we introduced to target the millisecond
        (`ms`) and microsecond (`µm`) sections of the sub-second regime
        ({py:class}`~datetime.timedelta` is limited to microsecond resolution).

        This allows formats that treat `ms` and `µs` separately, as well as
        formats that limit precision to `ms` — in which case `µs` are truncated:

        ```pycon
        >>> from datetime import timedelta

        >>> x = timedelta(milliseconds=123, microseconds=456)

        >>> fmt_timedelta(x, td_fmt="%3fms %6fµs")
        '123ms 456µs'

        >>> fmt_timedelta(x, td_fmt="%-S.%3fs")
        '0.123s'

        ```

        Both `%3f` and `%6f` are zero-padded to three places:

        ```pycon
        >>> y = timedelta(milliseconds=1, microseconds=2)

        >>> fmt_timedelta(y, td_fmt="%3fms %6fµs")
        '001ms 002µs'

        ```

        The C/Python `%f` directive encompasses the entire sub-second range,
        zero-padded to six places:

        ```pycon
        >>> fmt_timedelta(y, td_fmt="%fµs")
        '001002µs'

        ```

    3.  As in the C/Python [`strftime` language][], inserting the minimal-width
        flag `-` after the `%` in a directive removes zero-padding:

        ```pycon
        >>> from datetime import timedelta

        >>> x = timedelta(days=12)

        >>> fmt_timedelta(x, td_fmt="%dd %Hh %Mm %Ss")
        '12d 00h 00m 00s'

        >>> fmt_timedelta(x, td_fmt="%dd %-Hh %-Mm %-Ss")
        '12d 0h 0m 0s'

        >>> y = timedelta(milliseconds=1, microseconds=2)

        >>> fmt_timedelta(y, td_fmt="%3fms %6fµs")
        '001ms 002µs'

        >>> fmt_timedelta(y, td_fmt="%-3fms %-6fµs")
        '1ms 2µs'

        >>> fmt_timedelta(y, td_fmt="%fµs")
        '001002µs'

        >>> fmt_timedelta(y, td_fmt="%-fµs")
        '1002µs'

        ```

    4.  Optional groups `[...]` let a template adapt to a
        {py:class}`~datetime.timedelta`'s magnitude: a group is dropped unless
        it contains an _in-range_ directive — one whose term is non-zero, or a
        zero _captured_ between non-zero terms. This trims leading and trailing
        zero terms while keeping interior ("captive") zeros:

        ```pycon
        >>> from datetime import timedelta

        >>> units = "[%-dd] [%-Hh] [%-Mm] [%-Ss]"

        >>> fmt_timedelta(timedelta(hours=1, seconds=45), td_fmt=units)
        '1h 0m 45s'

        >>> fmt_timedelta(timedelta(minutes=5), td_fmt=units)
        '5m'

        >>> fmt_timedelta(timedelta(days=2, seconds=3), td_fmt=units)
        '2d 0h 0m 3s'

        ```

        Groups nest, so a term can carry its own optional sub-term — here the
        fractional seconds only appear when there are milliseconds:

        ```pycon
        >>> secs = "[%-S[.%3f]s]"

        >>> fmt_timedelta(timedelta(seconds=5), td_fmt=secs)
        '5s'

        >>> fmt_timedelta(timedelta(seconds=5, milliseconds=500), td_fmt=secs)
        '5.500s'

        ```

        When nothing is in-range there are two cases. A _true_ zero keeps the
        least-significant whole term (a clean `0s`), while a delta too small to
        register in any whole term still reveals itself through its
        least-significant term — the fraction, if the template has one:

        ```pycon
        >>> fmt_timedelta(timedelta(0), td_fmt=secs)
        '0s'

        >>> fmt_timedelta(timedelta(microseconds=12), td_fmt=secs)
        '0.000s'

        ```

    ## Default Format

    {py:attr}`FmtOpts.td_fmt` defaults to `"[%dd] [%H:%M:%S[.%3f]]"` — a
    wall-clock `HH:MM:SS` with an optional leading `Nd` days term and an
    optional trailing `.mmm` milliseconds term, each shown only when the
    corresponding unit is in-range.

    Sub-minute durations still render the full clock, revealing milliseconds
    only when present:

    ```pycon
    >>> fmt_timedelta(dt.timedelta(milliseconds=12))
    '00:00:00.012'

    >>> fmt_timedelta(dt.timedelta(seconds=5))
    '00:00:05'

    >>> fmt_timedelta(dt.timedelta(seconds=12, milliseconds=345))
    '00:00:12.345'

    >>> fmt_timedelta(dt.timedelta(minutes=5, seconds=30))
    '00:05:30'

    >>> fmt_timedelta(
    ...     dt.timedelta(hours=12, minutes=34, seconds=56, milliseconds=789)
    ... )
    '12:34:56.789'

    ```

    Days appear as a leading `Nd` term (grouped with commas past a thousand),
    and a bare day count drops the clock entirely:

    ```pycon
    >>> fmt_timedelta(dt.timedelta(days=1))
    '1d'

    >>> fmt_timedelta(dt.timedelta(days=1234))
    '1,234d'

    >>> fmt_timedelta(dt.timedelta(days=1, seconds=1))
    '1d 00:00:01'

    >>> fmt_timedelta(dt.timedelta(days=123, milliseconds=500))
    '123d 00:00:00.500'

    >>> fmt_timedelta(
    ...     dt.timedelta(
    ...         days=1, hours=23, minutes=45, seconds=56, milliseconds=789
    ...     )
    ... )
    '1d 23:45:56.789'

    ```

    Zero renders as a plain clock, and negatives keep their sign:

    ```pycon
    >>> fmt_timedelta(dt.timedelta())
    '00:00:00'

    >>> fmt_timedelta(-dt.timedelta(seconds=1, milliseconds=500))
    '-00:00:01.500'

    >>> fmt_timedelta(-dt.timedelta(hours=2, minutes=30))
    '-02:30:00'

    ```

    ## Custom templates

    Set {py:attr}`FmtOpts.td_fmt` to any template. A compact seconds template
    (`%-S` is minimal-width and thousands-grouped once it's the leading unit)
    suits durations you expect around the seconds/milliseconds range:

    ```pycon
    >>> td, secs = dt.timedelta, "%-S[.%3f]s"

    >>> [fmt_timedelta(t, td_fmt=secs) for t in (
    ...     td(seconds=12),
    ...     td(seconds=12, milliseconds=345),
    ...     td(milliseconds=123),
    ...     td(seconds=1_234_456, milliseconds=789),
    ... )]
    ['12s', '12.345s', '0.123s', '1,234,456.789s']

    ```

    A unit-segmented, expandable template — `%3f` and `%6f` split the
    sub-second remainder into milliseconds and microseconds:

    ```pycon
    >>> units = "[%-Hh] [%-Mm] [%-Ss] [%-3fms] [%-6fµs]"

    >>> [fmt_timedelta(t, td_fmt=units) for t in (
    ...     td(microseconds=12),
    ...     td(milliseconds=12),
    ...     td(seconds=12, milliseconds=345),
    ...     td(hours=1, seconds=45),
    ...     td(hours=1_234_567, minutes=23, seconds=45),
    ... )]
    ['12µs', '12ms', '12s 345ms', '1h 0m 45s', '1,234,567h 23m 45s']

    ```

    The sign is preserved. A true zero renders cleanly (its least-significant
    whole unit), while a non-zero duration too small to show still reveals
    itself through the fraction:

    ```pycon
    >>> fmt_timedelta(-td(seconds=1, milliseconds=500), td_fmt=secs)
    '-1.500s'

    >>> fmt_timedelta(td(0), td_fmt=secs)
    '0s'

    >>> fmt_timedelta(td(microseconds=12), td_fmt=secs)
    '0.000s'

    >>> fmt_timedelta(td(0), td_fmt=units)
    '0s'

    ```
    """
    sign = ""
    body: list[str] = []
    for text, component in iter_timedelta_segments(td, opts.td_fmt):
        if component == "sign":
            sign = text
        else:
            body.append(text)
    # Strip the body independently so an optional leading term (e.g. omitted
    # `[%dd] `) doesn't leave the sign dangling with an interior space.
    return sign + "".join(body).strip()
