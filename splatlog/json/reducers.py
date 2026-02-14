"""
Reducers for converting arbitrary Python objects to JSON-encodable forms.

This module provides {py:class}`JSONReducer` — a dataclass that pairs a match
predicate with a reduction function — along with a suite of pre-configured
reducers for common Python types (classes, dataclasses, enums, exceptions,
mappings, collections, etc.).

Reducers are ordered by priority, allowing the JSON encoder to try more
specific reducers before falling back to generic ones.
"""

import dataclasses
from collections.abc import Callable, Mapping, Collection
from enum import Enum
from inspect import isclass
import os
import sys
import traceback
from types import TracebackType
from typing import Any

# `Self` was added to stdlib typing in 3.11
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from splatlog.lib import fmt_type, has_method
from splatlog.typings import JSONEncodable, JSONReduceFn


@dataclasses.dataclass(frozen=True, order=True)
class JSONReducer:
    """
    A reducer converts objects to {py:type}`splatlog.typings.JSONEncodable` that
    can then be JSON encoded by {py:class}`json.JSONEncoder`.

    {py:class}`splatlog.json.JSONEncoder` uses a priority-ordered
    {py:class}`list` of reducers to extend the capabilities of
    {py:class}`json.JSONEncoder` to cover more of the things you may want to
    log.

    Each reducer consists of:

    -   {py:attr}`JSONReducer.priority` determining evaluation order (lower =
        earlier).
    -   {py:attr}`JSONReducer.name` for identification and debugging.
    -   {py:attr}`JSONReducer.is_match` predicate to test if this reducer
        handles an object.
    -   {py:attr}`JSONReducer.reduce` function that transforms the object to a
        JSON-encodable form.

    Reducers are immutable and comparable (ordered by priority, then name).
    """

    @classmethod
    def instance(cls, typ: type, priority: int, reduce: JSONReduceFn) -> Self:
        """Create a reducer that matches instances of a given type `typ`.

        ## Parameters

        -   `typ`: The type to match via `isinstance`.
        -   `priority`: Evaluation order (lower = earlier).
        -   `reduce`: Function to transform matched objects.

        ## Returns

        A new {py:class}`JSONReducer` with {py:attr}`JSONReducer.is_match` set
        to `isinstance(obj, typ)`.
        """
        return cls(
            name=fmt_type(typ),
            priority=priority,
            is_match=lambda obj: isinstance(obj, typ),
            reduce=reduce,
        )

    @classmethod
    def method(cls, method_name: str, priority: int) -> Self:
        """Create a reducer that matches objects with a specific method.

        The reducer matches any object that has a callable zero-argument method
        with the given name, and reduces by calling that method.

        ## Parameters

        -   `method_name`: Name of the method to look for and invoke.
        -   `priority`: Evaluation order (lower = earlier).

        ## Returns

        A new {py:class}`JSONReducer` that calls `obj.<method_name>()` on
        matched objects.
        """
        return cls(
            name=f".{method_name}()",
            priority=priority,
            is_match=lambda obj: has_method(obj, method_name, req_arity=0),
            reduce=lambda obj: getattr(obj, method_name)(),
        )

    priority: int
    """Evaluation order — lower values are tried first."""

    name: str
    """
    Human-readable identifier for this reducer. Also serves to order reducers of
    equal {py:attr}`JSONReducer.priority`.
    """

    is_match: Callable[[Any], bool]
    """Predicate returning `True` if this reducer can handle the argument."""

    reduce: JSONReduceFn
    """Function that transforms the object to a JSON-encodable form."""


def reduce_dataclass(value: Any) -> dict[str, JSONEncodable]:
    """
    Convert a dataclass instance to a JSON-encodable dictionary.

    The `__class__` key is added first to identify the dataclass type,
    followed by all fields from {py:func}`dataclasses.asdict`.
    """
    # Order is preserved, so put the `__class__` first
    d = {"__class__": CLASS_REDUCER.reduce(type(value))}
    d.update(dataclasses.asdict(value))
    return d


def reduce_exception(error: BaseException) -> dict[str, JSONEncodable]:
    """Convert an exception to a JSON-encodable dictionary.

    Produces a dict containing:

    -   `type`: The exception class name (e.g. `"ValueError"`).
    -   `msg`: The string representation of the exception.
    -   `traceback`: (if present) List of frame dicts from `TRACEBACK_REDUCER`.
    -   `cause`: (if present) Recursively reduced `__cause__` exception.

    ## Parameters

    -   `error`: The exception to reduce.

    ## Returns

    A dictionary representation of the exception suitable for JSON encoding.
    """
    dct: dict[str, JSONEncodable] = dict(
        type=fmt_type(error.__class__),
        msg=str(error),
    )

    if error.__traceback__ is not None:
        dct["traceback"] = TRACEBACK_REDUCER.reduce(error.__traceback__)

    if error.__cause__ is not None:
        dct["cause"] = reduce_exception(error.__cause__)

    return dct


TO_JSON_ENCODABLE_REDUCER = JSONReducer.method(
    method_name="to_json_encodable",
    priority=10,
)
"""Reducer for objects with a `to_json_encodable()` method (priority 10).

This is the highest-priority reducer, allowing objects to define their own
JSON serialization by implementing a zero-argument `to_json_encodable` method.
"""

CLASS_REDUCER = JSONReducer(
    name="class",
    priority=20,
    is_match=isclass,
    reduce=fmt_type,
)
"""Reducer for class objects (priority 20).

Converts class objects to their formatted type name string.
"""

DATACLASS_REDUCER = JSONReducer(
    name="dataclasses.dataclass",
    priority=30,
    is_match=dataclasses.is_dataclass,
    reduce=reduce_dataclass,
)
"""Reducer for {py:mod}`dataclasses` (priority 30).

Converts dataclass instances to dictionaries via {py:func}`dataclasses.asdict`,
adding a `__class__` key with the {py:data}`CLASS_REDUCER` encoding of the
dataclass type, so you know what it is.

## Examples

```python
>>> import dataclasses

>>> @dataclasses.dataclass
... class Point:
...     x: int
...     y: int

>>> pt = Point(x=1, y=2)

>>> DATACLASS_REDUCER.is_match(pt)
True

>>> DATACLASS_REDUCER.reduce(pt) == {
...     "__class__": "splatlog.json.reducers.Point",
...     "x": 1,
...     "y": 2
... }
True

```
"""

ENUM_REDUCER = JSONReducer.instance(
    typ=Enum,
    priority=40,
    reduce=lambda obj: f"{fmt_type(obj.__class__)}.{obj.name}",
)
"""Reducer for {py:class}`enum.Enum` members (priority 40).

Converts enum values to strings like `"EnumClass.MEMBER_NAME"`.

## Examples

```python
>>> from enum import Enum
>>> from splatlog.json.reducers import ENUM_REDUCER

>>> class State(Enum):
...     STOPPED = 0
...     RUNNING = 1
...     CRASHED = 2

>>> state = State.RUNNING

>>> ENUM_REDUCER.is_match(state)
True

>>> ENUM_REDUCER.reduce(state)
'splatlog.json.reducers.State.RUNNING'

```
"""

TRACEBACK_REDUCER = JSONReducer.instance(
    typ=TracebackType,
    priority=40,
    reduce=lambda tb: [
        dict(
            file=frame_summary.filename,
            line=frame_summary.lineno,
            name=frame_summary.name,
            text=frame_summary.line,
        )
        for frame_summary in traceback.extract_tb(tb)
    ],
)
"""Reducer for {py:class}`types.TracebackType` (priority 40).

Converts tracebacks to a list of frame dictionaries, each containing
`file`, `line`, `name`, and `text` keys.

## Examples

```python
>>> def error_prone():
...     raise Exception("uh-oh")

>>> try:
...     error_prone()
... except Exception as err:
...     tb = TRACEBACK_REDUCER.reduce(err.__traceback__)

>>> tb == [
...     {
...         'file': '<doctest splatlog.json.reducers.__test__.TRACEBACK_REDUCER[1]>',
...         'line': 2,
...         'name': '<module>',
...         'text': 'error_prone()'
...     },
...     {
...         'file': '<doctest splatlog.json.reducers.__test__.TRACEBACK_REDUCER[0]>',
...         'line': 2,
...         'name': 'error_prone',
...         'text': 'raise Exception("uh-oh")'
...     }
... ]
True

```
"""

EXCEPTION_REDUCER = JSONReducer.instance(
    typ=BaseException,
    priority=40,
    reduce=reduce_exception,
)
"""Reducer for {py:class}`Exception` (priority 40).

Converts exceptions to dictionaries with `type`, `msg`, and optionally
`traceback` and `cause` keys. See `reduce_exception` for details.
"""

MAPPING_REDUCER = JSONReducer.instance(
    typ=Mapping,
    priority=50,
    reduce=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "items": dict(obj),
    },
)
"""Reducer for {py:class}`collections.abc.Mapping` types (priority 50).

Converts mappings (dict subclasses, etc.) to a dict with `__class__` and
`items` keys, preserving the original class name.
"""

COLLECTION_REDUCER = JSONReducer.instance(
    typ=Collection,
    priority=60,
    reduce=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "items": tuple(obj),
    },
)
"""Reducer for {py:class}`collections.abc.Collection` types (priority 60).

Converts collections (sets, frozensets, etc.) to a dict with `__class__` and
`items` keys. Lower priority than {py:data}`MAPPING_REDUCER` since
{py:class}`collections.abc.Mapping` is also a
{py:class}`collections.abc.Collection`.
"""

FALLBACK_REDUCER = JSONReducer(
    name="fallback",
    priority=100,
    is_match=lambda obj: True,
    reduce=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "__repr__": repr(obj),
    },
)
"""Fallback reducer for any object (priority 100).

Matches everything and produces a dict with `__class__` and `__repr__` keys.
This is the last resort when no other reducer matches.
"""

ALL_REDUCERS: tuple[JSONReducer, ...] = tuple(
    sorted(x for x in locals().values() if isinstance(x, JSONReducer))
)
"""All reducers defined in this module, sorted by priority (ascending).

This tuple is constructed by collecting all {py:class}`JSONReducer` instances
from the module's local namespace and sorting them.

Used as the default reducer set for {py:class}`splatlog.json.JSONEncoder`.
"""

# Are we testing? ENV flag is set in `tox.ini`, can set manually if need when
# running commands directly.
if os.environ.get("TESTING"):
    # `doctest` doesn't automatically pickup the "following docstring" format
    # used by Sphinx/MyST to document constants, so we need to do some AST
    # parsing and stick it in a `__test__` dict, which `doctest` looks for
    from splatlog._testing import get_constant_docstrings

    __test__ = get_constant_docstrings(__name__)
