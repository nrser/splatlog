import json
from typing import Optional, TypeVar, IO, Union
from collections.abc import Iterable, Callable, Mapping

from splatlog.lib import each, fmt_type
from splatlog.lib.text import fmt
from splatlog.typings import JSONEncoderCastable

from .default_handlers import ALL_HANDLERS, DefaultHandler

__all__ = ["JSONEncoder"]

Self = TypeVar("Self", bound="JSONEncoder")


class JSONEncoder(json.JSONEncoder):
    """
    An extension of `json.JSONEncoder` that attempts to deal with all the crap
    you might splat into a log.

    ##### Usage #####

    ###### Usage with `json.dump` and `json.dumps` #######

    The encoder can be used with `json.dump` and `json.dumps` as follows.

    ```python

    >>> from sys import stdout

    >>> json.dump(dict(x=1, y=2, z=3), stdout, cls=JSONEncoder)
    {"x": 1, "y": 2, "z": 3}

    >>> json.dumps(dict(x=1, y=2, z=3), cls=JSONEncoder)
    '{"x": 1, "y": 2, "z": 3}'

    ```

    ###### Instance Usage ######

    However, usage with `json.dump` and `json.dumps` will create a new
    `splatlog.json.json_encoder.JSONEncoder` instance for each call. It's more
    efficient to create a single instance and use it repeatedly.

    ```python

    >>> encoder = JSONEncoder()

    ```

    The encoder provides a `splatlog.json.json_encoder.JSONEncoder.dump`
    convenience method for (chunked) encoding to a file-like object.

    ```python

    >>> encoder.dump(dict(x=1, y=2, z=3), stdout)
    {"x": 1, "y": 2, "z": 3}

    ```

    The inherited `json.JSONEncoder.encode` method stands-in for `json.dumps`.

    ```python

    >>> encoder.encode(dict(x=1, y=2, z=3))
    '{"x": 1, "y": 2, "z": 3}'

    ```

    ###### Construction Helpers #####

    Construction helper class methods are provided for common instance
    configurations.

    The `splatlog.json.json_encoder.JSONEncoder.pretty` helper creates instances
    that output "pretty" JSON by setting
    `splatlog.json.json_encoder.JSONEncoder.indent` to `4`.

    Useful for human-read output.

    ```python

    >>> pretty_encoder = JSONEncoder.pretty()
    >>> pretty_encoder.dump(dict(x=1, y=2, z=3), stdout)
    {
        "x": 1,
        "y": 2,
        "z": 3
    }

    ```

    The `splatlog.json.json_encoder.JSONEncoder.compact` helper creates
    instances that output the most compact JSON, limiting each output to a
    single line.

    Useful for machine-read output, especially log files.

    ```python

    >>> compact_encoder = JSONEncoder.compact()
    >>> compact_encoder.dump(dict(x=1, y=2, z=3), stdout)
    {"x":1,"y":2,"z":3}

    ```

    ##### Extended Encoding Capabilities #####

    The whole point of this class is to be able to encode (far) more than the
    standard `json.JSONEncoder`.

    Extended capabilities are presented in resolution order — first one that
    applies wins... or loses; if that path fails for some reason, we don't keep
    trying down-list.

    ###### Custom Handler #######

    Any object can implement a `to_json_encodable` method, and that will be
    used.

    ```python

    >>> class A:
    ...     def __init__(self, x, y, z):
    ...         self.x = x
    ...         self.y = y
    ...         self.z = z
    ...
    ...     def to_json_encodable(self):
    ...         return dict(x=self.x, y=self.y, z=self.z)

    >>> encoder.dump(A(x=1, y=2, z=3), stdout)
    {"x": 1, "y": 2, "z": 3}

    ```

    ###### Classes ######

    Classes are encoded _nominally_ as JSON strings, composed of the class
    `__module__` and `__qualname__`, joined with a `.` character.

    This is indented to keep information about the types of objects both
    specific and concise.

    ```python

    >>> class B:
    ...     pass

    >>> encoder.dump(B, stdout)
    "splatlog.json.json_encoder.B"

    ```

    For classes that are part of the top-level namespace (which have a
    `__module__` of `"builtins"`) the module part is omitted.

    Hence the top-level class `str` encodes simply as `"str"`, not as
    `"builtins.str"`.

    ```python

    >>> encoder.dump(str, stdout)
    "str"

    ```

    ###### Dataclasses ######

    Dataclass instances are encoded via `dataclasses.asdict`.

    ```python

    >>> import dataclasses

    >>> @dataclasses.dataclass
    ... class DC:
    ...     x: int
    ...     y: int
    ...     z: int

    >>> encoder.dump(DC(x=1, y=2, z=3), stdout)
    {"x": 1, "y": 2, "z": 3}

    ```

    ###### Enums ######

    Instances of `enum.Enum` are encoded _nominally_ as JSON strings, composed
    of the class of the object (per class encoding, discussed above) and the
    object's `name`, joined (again) with a `.`.

    ```python

    >>> from enum import Enum

    >>> class Status(Enum):
    ...     OK = "ok"
    ...     ERROR = "error"

    >>> encoder.dump(Status.OK, stdout)
    "splatlog.json.json_encoder.Status.OK"

    ```

    Note that enums that descend from `enum.IntEnum` are automatically encoded
    by _value_ via the standard JSON encoder.

    ```python

    >>> from enum import IntEnum

    >>> class IntStatus(IntEnum):
    ...     OK = 200
    ...     ERROR = 500

    >>> encoder.dump(IntStatus.OK, stdout)
    200

    ```

    ###### Exceptions ######

    Yes, `splatlog.json.json_encoder.JSONEncoder` attempts to encode exceptions.

    At the most basic level, it tries to always give you the things you expect
    from an exception: the type of exception, and the message.

    The simplest version is an exception that was never raised, and hence has
    no traceback or cause.

    ```python

    >>> pretty_encoder.dump(RuntimeError("Never raised"), stdout)
    {
        "type": "RuntimeError",
        "msg": "Never raised"
    }

    ```

    In a more realistic scenario, the exception has been raised and has a
    traceback, which the encoder trawls through and encodes as well.

    ```python

    >>> def capture_error(fn, *args, **kwds):
    ...     try:
    ...         fn(*args, **kwds)
    ...     except BaseException as error:
    ...         return error

    >>> def f():
    ...     raise RuntimeError("Hey there")

    >>> pretty_encoder.dump(capture_error(f), stdout)
    {
        "type": "RuntimeError",
        "msg": "Hey there",
        "traceback": [
            {
                "file": "<doctest ...>",
                "line": 3,
                "name": "capture_error",
                "text": "fn(*args, **kwds)"
            },
            {
                "file": "<doctest ...>",
                "line": 2,
                "name": "f",
                "text": "raise RuntimeError(\\"Hey there\\")"
            }
        ]
    }

    ```

    To go even deeper, exceptions with an explicit cause also encode that cause.

    ```python

    >>> def g(f):
    ...     try:
    ...         f()
    ...     except Exception as error:
    ...         raise RuntimeError(f"{f} threw up") from error

    >>> pretty_encoder.dump(capture_error(g, f), stdout)
    {
        "type": "RuntimeError",
        "msg": "<function f at ...> threw up",
        "traceback": [
            {
                "file": "<doctest ...>",
                "line": 3,
                "name": "capture_error",
                "text": "fn(*args, **kwds)"
            },
            {
                "file": "<doctest ...>",
                "line": 5,
                "name": "g",
                "text": "raise RuntimeError(f\\"{f} threw up\\") from error"
            }
        ],
        "cause": {
            "type": "RuntimeError",
            "msg": "Hey there",
            "traceback": [
                {
                    "file": "<doctest ...>",
                    "line": 3,
                    "name": "g",
                    "text": "f()"
                },
                {
                    "file": "<doctest ...>",
                    "line": 2,
                    "name": "f",
                    "text": "raise RuntimeError(\\"Hey there\\")"
                }
            ]
        }
    }

    ```

    ###### Tracebacks ######

    Exhibited in the _Exceptions_ section, but basically the encoder pulls the
    `traceback.StackSummary` and iterates through it's `traceback.FrameSummay`
    entries, encoding the attributes as (arguably) more general names.

    >>> pretty_encoder.dump(capture_error(f).__traceback__, stdout)
    [
        {
            "file": "<doctest ...>",
            "line": 3,
            "name": "capture_error",
            "text": "fn(*args, **kwds)"
        },
        {
            "file": "<doctest ...>",
            "line": 2,
            "name": "f",
            "text": "raise RuntimeError(\\"Hey there\\")"
        }
    ]

    ###### Collections ######

    Objects that implement `collections.abc.Collection` are encoded as a JSON
    object containing the class and collection items.

    In the case of `collections.abc.Mapping`, items are encoded as a JSON
    object (via `dict(collection)`).

    ```python

    >>> from collections import UserDict

    >>> ud = UserDict(dict(a=1, b=2, c=3))
    >>> pretty_encoder.dump(ud, stdout)
    {
        "__class__": "collections.UserDict",
        "items": {
            "a": 1,
            "b": 2,
            "c": 3
        }
    }

    ```

    All other `collections.abc.Collection` have their items encoded as a JSON
    array (via `tuple(collection)`).

    ```python

    >>> pretty_encoder.dump({1, 2, 3}, stdout)
    {
        "__class__": "set",
        "items": [
            1,
            2,
            3
        ]
    }

    ```

    ###### Everything Else #######

    Because this encoder is focused on serializing log data that may contain any
    object, and that log data will often be examined only after said object is
    long gone, we try to provide a some-what useful catch-all.

    Anything that doesn't fall into any of the preceding categories will be
    encoded as a JSON object containing the `__class__` (as a string, per the
    _Classes_ section) and `__repr__`.

    ```python

    >>> pretty_encoder.dump(lambda x: x, stdout)
    {
        "__class__": "function",
        "__repr__": "<function <lambda> at ...>"
    }

    ```
    """

    COMPACT_KWDS = dict(indent=None, separators=(",", ":"))
    PRETTY_KWDS = dict(indent=4)

    @classmethod
    def compact(cls: type[Self], **kwds) -> Self:
        return cls(**cls.COMPACT_KWDS, **kwds)

    @classmethod
    def pretty(cls: type[Self], **kwds) -> Self:
        return cls(**cls.PRETTY_KWDS, **kwds)

    @classmethod
    def cast(cls: type[Self], value: JSONEncoderCastable) -> Self:
        if isinstance(value, cls):
            return value

        if value is None:
            return cls.compact()

        if isinstance(value, str):
            if value == "compact":
                return cls.compact()
            elif value == "pretty":
                return cls.pretty()
            else:
                raise ValueError(
                    (
                        "Only strings 'compact' and 'pretty' are recognized; "
                        "given {!r}"
                    ).format(value)
                )

        if isinstance(value, Mapping):
            return cls(**value)

        raise TypeError(
            "Expected {}, given {}: {}".format(
                fmt(Union[cls, str, Mapping]), fmt(type(value)), fmt(value)
            )
        )

    _handlers: Optional[list[DefaultHandler]] = None
    _continue_on_handler_error: bool = True

    def __init__(
        self,
        *,
        handlers: Union[None, DefaultHandler, Iterable[DefaultHandler]] = None,
        default: None = None,
        **kwds,
    ):
        if default is not None:
            raise TypeError(
                f"{fmt_type(JSONEncoder)} does not support `default` "
                + f"argument (`default` must be `None`), given {default!r}"
            )

        super().__init__(**kwds)

        if handlers is not None:
            self.add_handlers(handlers)

    def default(self, obj):
        for handler in (
            ALL_HANDLERS if self._handlers is None else self._handlers
        ):
            try:
                if handler.is_match(obj):
                    return handler.handle(obj)
            except Exception as error:
                if self._continue_on_handler_error:
                    pass
                else:
                    raise TypeError(
                        f"Encoding handler {handler.name} raised"
                    ) from error

        return super().default(obj)

    def dump(self, obj, fp: IO) -> None:
        for chunk in self.iterencode(obj):
            fp.write(chunk)

    def get_handlers(self) -> tuple[DefaultHandler, ...]:
        if self._handlers is None:
            return ALL_HANDLERS
        return tuple(self._handlers)

    def add_handlers(self, handlers) -> None:
        if self._handlers is None:
            self._handlers = list(ALL_HANDLERS)

        self._handlers.extend(each(handlers))

        self._handlers.sort()

    def remove_handlers(
        self, match: Callable[[DefaultHandler], bool]
    ) -> tuple[DefaultHandler, ...]:
        if self._handlers is None:
            self._handlers = list(ALL_HANDLERS)

        matches = tuple(h for h in self._handlers if match(h))

        for h in matches:
            self._handlers.remove(h)

        return matches
