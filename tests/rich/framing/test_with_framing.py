"""Tests for splatlog.rich.section."""

import dataclasses as dc

from rich.console import Console, Group
from rich.measure import Measurement
from rich.padding import Padding, PaddingDimensions
from rich.segment import Segment, Segments
from rich.table import Table

from splatlog.rich.framing import with_framing


class TestWithFraming:
    def test_wraps_segments_for_nested_rendering(self):
        """
        Segments yielded from `__rich_console__` must be wrapped before
        grouping, or nested renderables (e.g. table cells) fail to measure them.
        """

        @dc.dataclass
        class Segmented:
            padding: PaddingDimensions

            @with_framing
            def __rich_console__(self, console, options):
                yield Segment("hey ")
                yield Segment("ho, ")
                yield Segment("let's go!")

        c = Console(no_color=True, force_terminal=False, width=80)

        # If nothing needs doing then `format` will get out of the way and we'll
        # receive an unmodified return value from `__rich_console__`

        # We can observe this by setting `padding=0` (no padding)
        no_format = list(Segmented(padding=0).__rich_console__(c, c.options))

        # What we receive is the three `Segment`
        assert no_format == [
            Segment("hey "),
            Segment("ho, "),
            Segment("let's go!"),
        ]

        # With padding to be added `format` will convert the segments to
        # renderables and group them for wrapping with a `Padding` element
        (with_format,) = Segmented(padding=(1, 0)).__rich_console__(
            c, c.options
        )
        assert isinstance(with_format, Padding)

        # Inside the `Padding` is a `Group`
        group = with_format.renderable
        assert isinstance(group, Group)

        (segments,) = group.renderables
        assert isinstance(segments, Segments)

        # Rendering the group simply unwraps the segments
        assert list(c.render(group)) == [
            Segment("hey "),
            Segment("ho, "),
            Segment("let's go!"),
        ]

        # The group is measurable (which `Segment` are not)
        m = Measurement.get(c, c.options, group)

        # However, it's not a very _good_ measurement... because `Segments` does
        # not implement any measurement functionality
        assert m.minimum == 0
        assert m.maximum == c.width

        # We can include the formatted element in other elements that need to
        # measure it, such as sticking it in a `Table` cell — this is where we'd
        # see failures before converting to renderables
        table = Table(show_header=False, show_edge=False, pad_edge=False)
        table.add_row("msg", with_format)

        with c.capture() as capture:
            c.print(table)

        output = capture.get()

        assert "msg" in output
        assert "hey ho, let's go!" in output
