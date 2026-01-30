import json
import sys
from typing import IO
from collections.abc import Iterable, Callable, Mapping
from warnings import warn

# `Self` was added to stdlib typing in 3.11
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from splatlog.lib import fmt_type_value
from splatlog.lib.text import fmt
from splatlog.typings import JSONEncoderCastable, OnReducerError, assert_never

from .reducers import ALL_REDUCERS, JSONReducer

__all__ = ["JSONEncoder"]

_REDUCER_ERROR_MSG = (
    "Encoding reducer '{}' raised failed to reduce {}, error: {}"
)


class JSONEncoder(json.JSONEncoder):
    """
    An extension of {py:class}`json.JSONEncoder` that attempts to deal with all
    the crap you might splat into a log.

    Works by overriding the {py:meth}`JSONEncoder.default` method to consult a
    list of {py:class}`splatlog.json.JSONReducer` to reduce objects to a
    {py:type}`splatlog.typings.JSONEncodable` form. The list defaults to
    {py:data}`splatlog.json.ALL_REDUCERS`, and can be customized per encoder
    instance.

    ## Usage

    **Usage with {py:func}`json.dump` and {py:func}`json.dumps`**

    The encoder can be used with {py:func}`json.dump` and {py:func}`json.dumps`
    by setting the `cls` keyword argument to the class.

    ```python
    >>> import json
    >>> import sys

    >>> json.dump(dict(x=1, y=2, z=3), sys.stdout, cls=JSONEncoder)
    {"x": 1, "y": 2, "z": 3}

    >>> json.dumps(dict(x=1, y=2, z=3), cls=JSONEncoder)
    '{"x": 1, "y": 2, "z": 3}'

    ```

    **Reusable Instance Usage**

    However, usage with {py:func}`json.dump` and {py:func}`json.dumps` will
    create a new {py:class}`JSONEncoder` instance for each call. It's more
    efficient to create a single instance and use it repeatedly.

    ```python
    >>> encoder = JSONEncoder()

    ```

    The encoder provides a {py:meth}`JSONEncoder.dump` convenience method for
    (chunked) encoding to a file-like object.

    ```python
    >>> encoder.dump(dict(x=1, y=2, z=3), sys.stdout)
    {"x": 1, "y": 2, "z": 3}

    ```

    The inherited {py:meth}`json.JSONEncoder.encode` method stands-in for
    {py:func}`json.dumps`.

    ```python
    >>> encoder.encode(dict(x=1, y=2, z=3))
    '{"x": 1, "y": 2, "z": 3}'

    ```

    **Pretty Encoding**

    Class methods are provided to help construct common configurations.

    The {py:meth}`JSONEncoder.pretty` helper creates instances that output
    "pretty" JSON by setting the `indent` attribute to `4`.

    Useful for human-read output.

    ```python
    >>> pretty_encoder = JSONEncoder.pretty()
    >>> pretty_encoder.dump(dict(x=1, y=2, z=3), sys.stdout)
    {
        "x": 1,
        "y": 2,
        "z": 3
    }

    ```

    **Compact Encoding**

    The {py:class}`JSONEncoder.compact` helper creates instances that output the
    most compact JSON, limiting each output to a single line.

    Useful for machine-read output, especially log files.

    ```python
    >>> compact_encoder = JSONEncoder.compact()
    >>> compact_encoder.dump(dict(x=1, y=2, z=3), sys.stdout)
    {"x":1,"y":2,"z":3}

    ```

    **Reducers — Extended Encoding Capabilities**

    The whole point of this class is to be able to encode (far) more than the
    standard {py:class}`json.JSONEncoder`.

    Extended capabilities are provided by {py:class}`splatlog.json.JSONReducer`

    **`to_json_encodable` Method Reducer**

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

    >>> encoder.dump(A(x=1, y=2, z=3), sys.stdout)
    {"x": 1, "y": 2, "z": 3}

    ```

    **Classes**

    Classes are encoded _nominally_ as JSON strings, composed of the class
    `__module__` and `__qualname__`, joined with a `.` character.

    This is indented to keep information about the types of objects both
    specific and concise.

    ```python

    >>> class B:
    ...     pass

    >>> encoder.dump(B, sys.stdout)
    "splatlog.json.B"

    ```

    For classes that are part of the top-level namespace (which have a
    `__module__` of `"builtins"`) the module part is omitted.

    Hence the top-level class `str` encodes simply as `"str"`, not as
    `"builtins.str"`.

    ```python

    >>> encoder.dump(str, sys.stdout)
    "str"

    ```

    **Dataclasses**

    Dataclass instances are encoded via `dataclasses.asdict`, with an
    additional `__class__` key for the type.

    ```python

    >>> import dataclasses

    >>> @dataclasses.dataclass
    ... class DC:
    ...     x: int
    ...     y: int
    ...     z: int

    >>> encoder.dump(DC(x=1, y=2, z=3), sys.stdout)
    {"__class__": "splatlog.json.DC", "x": 1, "y": 2, "z": 3}

    ```

    **Enums**

    Instances of {py:class}`enum.Enum` are encoded _nominally_ as JSON strings,
    composed of the class of the object (per class encoding, discussed above)
    and the object's `name`, joined (again) with a `.`.

    ```python
    >>> from enum import Enum

    >>> class Status(Enum):
    ...     OK = "ok"
    ...     ERROR = "error"

    >>> encoder.dump(Status.OK, sys.stdout)
    "splatlog.json.Status.OK"

    ```

    Note that enums that descend from `enum.IntEnum` are automatically encoded
    by _value_ via the standard JSON encoder.

    ```python
    >>> from enum import IntEnum

    >>> class IntStatus(IntEnum):
    ...     OK = 200
    ...     ERROR = 500

    >>> encoder.dump(IntStatus.OK, sys.stdout)
    200

    ```

    **Exceptions**

    Yes, {py:class}`JSONEncoder` attempts to encode exceptions.

    At the most basic level, it tries to always give you the things you expect
    from an exception: the type of exception, and the message.

    The simplest version is an exception that was never raised, and hence has
    no traceback or cause.

    ```python
    >>> pretty_encoder.dump(RuntimeError("Never raised"), sys.stdout)
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

    >>> pretty_encoder.dump(capture_error(f), sys.stdout)
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

    >>> pretty_encoder.dump(capture_error(g, f), sys.stdout)
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

    **Tracebacks**

    Exhibited in the _Exceptions_ section, but basically the encoder pulls the
    {py:class}`traceback.StackSummary` and iterates through it's
    {py:class}`traceback.FrameSummary` entries, encoding the attributes as
    (arguably) more general names.

    ```python
    >>> pretty_encoder.dump(capture_error(f).__traceback__, sys.stdout)
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

    ```

    **Collections**

    Objects that implement {py:class}`collections.abc.Collection` are encoded as
    a JSON object containing the class and collection items.

    In the case of {py:class}`collections.abc.Mapping`, items are encoded as a
    JSON object (via `dict(collection)`).

    ```python
    >>> from collections import UserDict

    >>> ud = UserDict(dict(a=1, b=2, c=3))
    >>> pretty_encoder.dump(ud, sys.stdout)
    {
        "__class__": "collections.UserDict",
        "items": {
            "a": 1,
            "b": 2,
            "c": 3
        }
    }

    ```

    All other {py:class}`collections.abc.Collection` have their items encoded as
    a JSON array (via `tuple(collection)`).

    ```python
    >>> pretty_encoder.dump({1, 2, 3}, sys.stdout)
    {
        "__class__": "set",
        "items": [
            1,
            2,
            3
        ]
    }

    ```

    **Everything Else**

    Because this encoder is focused on serializing log data that may contain any
    object, and that log data will often be examined only after said object is
    long gone, we try to provide a some-what useful catch-all.

    Anything that doesn't fall into any of the preceding categories will be
    encoded as a JSON object containing the `__class__` (as a string, per the
    _Classes_ section) and `__repr__`.

    ```python
    >>> pretty_encoder.dump(lambda x: x, sys.stdout)
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
                fmt(cls | str | Mapping), fmt(type(value)), fmt(value)
            )
        )

    reducers: list[JSONReducer]
    """
    {py:class}`splatlog.json.JSONReducer` used to reduce objects to
    {py:type}`splatlog.typings.JSONEncodable` values that the superclass can
    encode.

    See `{py:meth}`JSONEncoder.default` for details.

    ```{warning}
    This list should always be sorted — {py:class}`splatlog.json.JSONReducer`
    compare by {py:attr}`splatlog.json.JSONReducer.priority` (lower first),
    then by {py:attr}`splatlog.json.JSONReducer.name` (alphanumeric).

    The constructor, {py:meth}`JSONEncoder.add_reducers`, and
    {py:meth}`JSONEncoder.remove_reducers` take care of sorting for you. If you
    edit or replace the list directly you will need to sort it yourself. Calling
    {py:meth}`list.sort` will do the trick.
    ```
    """

    on_reducer_error: OnReducerError

    def __init__(
        self,
        *,
        reducers: Iterable[JSONReducer] = ALL_REDUCERS,
        on_reducer_error: OnReducerError = "continue",
        default: None = None,
        **kwds,
    ):
        # We prohibit the `default` keyword because we use the default behavior
        # for the reducers
        if default is not None:
            assert_never(default, None)

        super().__init__(**kwds)

        self.reducers = sorted(reducers)
        self.on_reducer_error = on_reducer_error

    def default(self, obj):
        for reducer in self.reducers:
            try:
                if reducer.is_match(obj):
                    return reducer.reduce(obj)
            except Exception as error:
                match self.on_reducer_error:
                    case "continue":
                        pass
                    case "raise":
                        raise TypeError(
                            _REDUCER_ERROR_MSG.format(
                                fmt(reducer), fmt_type_value(obj), fmt(error)
                            )
                        ) from error
                    case "warn":
                        warn(
                            _REDUCER_ERROR_MSG.format(
                                fmt(reducer), fmt_type_value(obj), fmt(error)
                            )
                        )
                    case _:
                        assert_never(self.on_reduce_error, OnReducerError)

        return super().default(obj)

    def dump(self, obj, fp: IO) -> None:
        for chunk in self.iterencode(obj):
            fp.write(chunk)

    def add_reducers(self, *reducers: JSONReducer) -> None:
        """
        Add {py:class}`splatlog.json.JSONReducer` instances to the encoder.

        Sorts the reducers by priority after making the additions.
        """
        self.reducers.extend(reducers)
        self.reducers.sort()

    def remove_reducers(
        self, match: Callable[[JSONReducer], bool]
    ) -> tuple[JSONReducer, ...]:
        matches = tuple(r for r in self.reducers if match(r))

        for r in matches:
            self.reducers.remove(r)

        return matches
