"""
{py:func}`~splatlog.rich.enrich` support for
{py:type}`~splatlog.lib.types.Number`:

1.  {py:class}`int`
2.  {py:class}`float`
3.  {py:class}`~decimal.Decimal`
4.  {py:class}`~fractions.Fraction`
5.  {py:class}`complex`

Numbers are formatted with {py:func}`~splatlog.lib.text.fmt_number` (so all the
{py:class}`~splatlog.lib.text.FmtOpts` number templates apply) and then styled
for Rich display. Unlike the {py:mod}`~splatlog.rich.enrich.datetime`
enrichers — which style each tokenized component — the whole formatted number
gets a single style, since `str.format` output (grouping, currency, percent, the
`𝒊` imaginary unit, `∞`/`NaN`) doesn't decompose cleanly into components.
"""

from __future__ import annotations
import dataclasses as dc

from rich.console import Console, ConsoleOptions, RenderResult
from rich.style import Style
from rich.text import Text

from splatlog.lib.text import Number, fmt_number

from .enriched import Enriched
from .enrichment import EnrichOpts, enrichment


@enrichment
def enrich_number(value: Number, opts: EnrichOpts) -> Text:
    """
    Enrich a number: format it with {py:func}`~splatlog.lib.text.fmt_number`
    (honoring {py:class}`EnrichOpts`) and style the result `repr.number` (or
    `repr.number_complex` for {py:class}`complex`).

    ## Examples

    ```pycon
    >>> from splatlog.rich.enrich import EnrichOpts

    >>> enrich_number(1234567).plain
    '1,234,567'

    >>> enrich_number(1234567).style
    'repr.number'

    >>> enrich_number(complex(1, 2)).style
    'repr.number_complex'

    ```

    Formatting is customized through {py:class}`EnrichOpts` (or
    {py:class}`EnrichKwds` keyword arguments):

    ```pycon
    >>> enrich_number(1234567, EnrichOpts(i_fmt="{:_}")).plain
    '1_234_567'

    >>> enrich_number(1234.5, f_fmt="${:,.2f}").plain
    '$1,234.50'

    ```
    """
    style = (
        "repr.number_complex" if isinstance(value, complex) else "repr.number"
    )
    return Text(fmt_number(value, opts), style=style, end="")


@dc.dataclass(frozen=True)
class EnrichedId(Enriched[int]):
    """
    Wraps an integer _identifier_ (e.g. a database primary key) so it renders
    _verbatim_ — without the digit grouping {py:func}`enrich_number` applies —
    and in a distinct {py:attr}`style`.

    Grouping (`5,733`) is great for quantities you _read_, but wrong for IDs,
    which you mostly _copy/paste_ — the commas get in the way and the styling
    makes them look like ordinary numbers. Wrap ID fields with
    {py:class}`EnrichedId` (e.g. in a `_enrich_` method) to render them plainly
    and set them apart.

    As an {py:class}`~splatlog.rich.enrich.Enriched` wrapper, the original
    {py:class}`int` remains available via
    {py:attr}`~splatlog.rich.enrich.Enriched.value` /
    {py:func}`~splatlog.rich.enrich.unwrap`, so callers that care about the
    underlying value (its {py:class}`type`, serialization, …) still see an
    {py:class}`int`.

    ## Examples

    Renders the raw digits (no grouping), unlike {py:func}`enrich_number`:

    ```pycon
    >>> import sys
    >>> from rich.console import Console
    >>> console = Console(file=sys.stdout, no_color=True, force_terminal=False)

    >>> console.print(EnrichedId(5733))
    5733

    >>> enrich_number(5733).plain
    '5,733'

    ```

    The underlying {py:class}`int` is recoverable:

    ```pycon
    >>> from splatlog.rich.enrich import unwrap

    >>> EnrichedId(5733).value
    5733

    >>> unwrap(EnrichedId(5733))
    5733

    ```
    """

    style: str | Style = "repr.uuid"
    """
    Rich style applied when rendering.

    Default: `"repr.uuid"`{l=py} — {py:obj}`rich.default_styles.DEFAULT_STYLES`
    class for _identifiers_, defaults to bright-yellow, which contrasts well to
    the cyan `"repr.number"` that regular {py:class}`int` use.
    """

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield Text(str(self.value), style=self.style, end="")
