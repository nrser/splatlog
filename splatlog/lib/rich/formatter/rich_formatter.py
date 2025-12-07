from __future__ import annotations
from inspect import isclass
from string import Formatter
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Iterable,
    Mapping,
    Sequence,
    Union,
    cast,
)

from rich.text import Text

from ..enrich import repr_highlight, REPR_HIGHLIGHTER
from .rich_repr import RichRepr, implements_rich_repr
from .rich_text import RichText


RichFormatterConverter = Callable[[Any], Text]
RichFormatterConversions = Mapping[str, RichFormatterConverter]


def _safe_isinstance(
    obj: object, class_or_tuple: Union[type, tuple[type, ...]]
) -> bool:
    """isinstance can fail in rare cases, for example types with no __class__

    Implementation copied from `rich.pretty._safe_isinstance` since it's
    private.
    """
    try:
        return isinstance(obj, class_or_tuple)
    except Exception:
        return False


def _iter_rich_args(rich_args: Any) -> Iterable[tuple[None | str, Any]]:
    for arg in rich_args:
        if _safe_isinstance(arg, tuple):
            if len(arg) == 3:
                key, child, default = arg
                if default == child:
                    continue
                yield key, child
            elif len(arg) == 2:
                key, child = arg
                yield key, child
            elif len(arg) == 1:
                yield None, arg[0]
        else:
            yield None, arg


# Turned out to not be so simple... or I'm not so smart :/
#
# def has_non_trivial_format_method(value: Any) -> bool:
#     if isinstance(value, (int, float, str)):
#         return True

#     if value.__class__.__format__ is object.__format__:
#         return False

#     return False


def ascii_convert(value: Any) -> Text:
    return repr_highlight(value, use_ascii=True)


def rich_repr_convert(obj: RichRepr) -> Text:
    # TODO ?
    # angular = getattr(obj.__rich_repr__, "angular", False)
    args = list(_iter_rich_args(obj.__rich_repr__()))
    class_name = obj.__class__.__name__

    text = Text("", end="")

    text.append(class_name + "(")

    for index, (key, child) in enumerate(args):
        child_text = repr_convert(child)
        if index != 0:
            text.append(", ")
        if key is not None:
            text.append(key + "=")
        text.append_text(child_text)

    text.append(")")
    REPR_HIGHLIGHTER.highlight(text)
    return text


def repr_convert(value: Any) -> Text:
    if implements_rich_repr(value):
        return rich_repr_convert(value)
    return repr_highlight(value)


def str_convert(value: Any) -> Text:
    return Text(str(value), end="")


def text_convert(value: Any) -> Text:
    if isclass(value):
        if (rich_type := getattr(value, "__rich_type__", None)) and isinstance(
            rich_type, Callable
        ):
            return rich_type()
    elif isinstance(value, RichText):
        return value.__rich_text__()

    return repr_convert(value)


class RichFormatter(Formatter):
    """An extension of `string.Formatter` that interpolates into
    `rich.text.Text` instances.
    """

    DEFAULT_CONVERTERS = MappingProxyType(
        {
            "a": ascii_convert,
            "r": repr_convert,
            "s": str_convert,
            "t": text_convert,
        }
    )

    _conversions: RichFormatterConversions

    def __init__(self, *, conversions: None | RichFormatterConversions = None):
        if conversions is None:
            self._conversions = self.DEFAULT_CONVERTERS
        else:
            self._conversions = MappingProxyType(
                {**self.DEFAULT_CONVERTERS, **conversions}
            )

    @property
    def conversions(self) -> RichFormatterConversions:
        return self._conversions

    def format(self, format_string: str, /, *args: Any, **kwargs: Any) -> Text:
        return self.vformat(format_string, args, kwargs)

    def vformat(
        self, format_string: str, args: Sequence[Any], kwargs: Mapping[str, Any]
    ) -> Text:
        used_args = set()
        result, _ = self._vformat(format_string, args, kwargs, used_args, 2)
        self.check_unused_args(used_args, args, kwargs)
        return result

    def _vformat(
        self,
        format_string: str,
        args: Sequence[Any],
        kwargs: Mapping[str, Any],
        used_args: set[int | str],
        recursion_depth: int,
        auto_arg_index: int = 0,
    ) -> tuple[Text, int]:
        if recursion_depth < 0:
            raise ValueError("Max string recursion exceeded")

        result = Text("", end="")

        for literal_text, field_name, format_spec, conversion in self.parse(
            format_string
        ):
            # output the literal text
            if literal_text:
                result.append(literal_text)

            # if there's a field, output it
            if field_name is not None:
                # this is some markup, find the object and do
                #  the formatting

                # handle arg indexing when empty field_names are given.
                if field_name == "":
                    if auto_arg_index is False:
                        raise ValueError(
                            "cannot switch from manual field "
                            "specification to automatic field "
                            "numbering"
                        )
                    field_name = str(auto_arg_index)
                    auto_arg_index += 1
                elif field_name.isdigit():
                    if auto_arg_index:
                        raise ValueError(
                            "cannot switch from manual field "
                            "specification to automatic field "
                            "numbering"
                        )
                    # disable auto arg incrementing, if it gets
                    # used later on, then an exception will be raised
                    auto_arg_index = False

                # given the field_name, find the object it references
                #  and the argument it came from
                obj, arg_used = self.get_field(field_name, args, kwargs)
                used_args.add(arg_used)

                # Convert to text
                obj = self.convert_field(obj, conversion)

                # expand the format spec, if needed
                format_spec, auto_arg_index = super()._vformat(
                    # If `field_name` is not `None` then neither will be
                    # `format_spec`
                    cast(str, format_spec),
                    args,
                    kwargs,
                    used_args,
                    recursion_depth - 1,
                    auto_arg_index=auto_arg_index,
                )

                # format the object and append to the result
                result.append_text(self.format_field(obj, format_spec))

        return result, auto_arg_index

    def format_field(self, value: Any, format_spec: str) -> Text:
        # Deal with `Text` first, either as a result of a _conversion_ or simply
        # provided for interpolation.
        if isinstance(value, Text):
            # If there is a format spec apply it to the plain string value of
            # the text. This seems like the most reasonable approach to support
            # to easily offer some support for formatting specifications.
            if format_spec != "":
                value.plain = super().format_field(value.plain, format_spec)

            # Return the `Text` to be interpolated.
            return value

        # If there is a format spec we simply proxy to the superclass
        # functionality. This might end up just being `object.__format__`, which
        # will simply raise a `TypeError` complaining about "unsupported format
        # string", but that's how `string.Formatter` works too (Python 3.10).
        #
        # If you want to use the string formatting specs on rich text you can
        # explicitly use a conversion like `!t:<format_spec>`, see examples
        # in `deps/splatlog/docs/content/splatlog/lib/rich/formatter.md`.
        #
        if format_spec != "":
            return Text(super().format_field(value, format_spec), end="")

        # With no format spec and a "whatever" value we default to the "text"
        # conversion, our analog of how `string.Formatter` defaults to `str`
        # conversion.
        return self._conversions["t"](value)

    def convert_field(self, value: Any, conversion: None | str) -> Any:
        if conversion is None:
            return value
        if convert := self._conversions.get(conversion):
            return convert(value)
        raise ValueError(
            "Unknown conversion specifier {0!s}".format(conversion)
        )
