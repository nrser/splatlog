import pytest
from rich.console import Group
from rich.segment import Segment, Segments
from rich.text import Text

from splatlog.rich.framing import to_renderable_type


class TestStringCase:
    def test_returns_string_unchanged(self):
        assert to_renderable_type("hello") == "hello"

    def test_empty_string(self):
        assert to_renderable_type("") == ""


class TestConsoleRenderableCase:
    def test_returns_text_unchanged(self):
        text = Text("styled text")
        assert to_renderable_type(text) is text


class TestRichCastCase:
    def test_returns_rich_cast_unchanged(self):
        class MyRichCast:
            def __rich__(self) -> Text:
                return Text("cast")

        obj = MyRichCast()
        assert to_renderable_type(obj) is obj


class TestSegmentCase:
    def test_wraps_segment_in_renderable_segment(self):
        seg = Segment("content")
        result = to_renderable_type(seg)
        assert isinstance(result, Segments)
        assert result.segments == [seg]


class TestEmptyListCase:
    def test_returns_empty_string(self):
        assert to_renderable_type([]) == ""


class TestSingleItemListCase:
    def test_unwraps_single_string(self):
        assert to_renderable_type(["only"]) == "only"

    def test_unwraps_single_renderable(self):
        text = Text("one")
        assert to_renderable_type([text]) is text


class TestMultiItemListCase:
    def test_returns_group(self):
        result = to_renderable_type(["a", "b", "c"])
        assert isinstance(result, Group)

    def test_group_contains_converted_items(self):
        seg = Segment("seg")
        result = to_renderable_type(["str", seg])
        assert isinstance(result, Group)
        renderables = list(result.renderables)
        assert renderables[0] == "str"
        assert isinstance(renderables[1], Segments)


class TestIterableCase:
    def test_generator_converted_to_group(self):
        def gen():
            yield "a"
            yield "b"

        result = to_renderable_type(gen())
        assert isinstance(result, Group)

    def test_tuple_converted(self):
        result = to_renderable_type(("x", "y"))
        assert isinstance(result, Group)

    def test_single_item_generator_unwraps(self):
        result = to_renderable_type(x for x in ["only"])
        assert result == "only"


class TestValueErrorCase:
    def test_raises_for_int(self):
        with pytest.raises(ValueError, match="can not convert"):
            to_renderable_type(42)

    def test_raises_for_none(self):
        with pytest.raises(ValueError, match="can not convert"):
            to_renderable_type(None)

    def test_raises_for_object(self):
        with pytest.raises(ValueError, match="can not convert"):
            to_renderable_type(object())
