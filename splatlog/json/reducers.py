import dataclasses
from collections.abc import Callable, Mapping, Collection
from enum import Enum
from inspect import isclass
import traceback
from types import TracebackType
from typing import Any, Type

from splatlog.lib import fmt_type, has_method
from splatlog.typings import JSONEncodable, JSONReduceFn


@dataclasses.dataclass(frozen=True, order=True)
class JSONReducer:
    priority: int
    name: str
    is_match: Callable[[Any], bool]
    reduce: JSONReduceFn


def instance_reducer(
    cls: Type, priority: int, reduce: JSONReduceFn
) -> JSONReducer:
    return JSONReducer(
        name=fmt_type(cls),
        priority=priority,
        is_match=lambda obj: isinstance(obj, cls),
        reduce=reduce,
    )


def method_reducer(method_name: str, priority: int) -> JSONReducer:
    return JSONReducer(
        name=f".{method_name}()",
        priority=priority,
        is_match=lambda obj: has_method(obj, method_name, req_arity=0),
        reduce=lambda obj: getattr(obj, method_name)(),
    )


def exception_reducer(error: BaseException) -> dict[str, JSONEncodable]:
    dct: dict[str, JSONEncodable] = dict(
        type=fmt_type(error.__class__),
        msg=str(error),
    )

    if error.__traceback__ is not None:
        dct["traceback"] = TRACEBACK_REDUCER.reduce(error.__traceback__)

    if error.__cause__ is not None:
        dct["cause"] = exception_reducer(error.__cause__)

    return dct


TO_JSON_ENCODABLE_REDUCER = method_reducer(
    method_name="to_json_encodable",
    priority=10,
)

CLASS_REDUCER = JSONReducer(
    name="class",
    priority=20,
    is_match=isclass,
    reduce=fmt_type,
)

DATACLASS_REDUCER = JSONReducer(
    name="dataclasses.dataclass",
    priority=30,
    is_match=dataclasses.is_dataclass,
    reduce=dataclasses.asdict,
)

ENUM_REDUCER = instance_reducer(
    cls=Enum,
    priority=40,
    reduce=lambda obj: f"{fmt_type(obj.__class__)}.{obj.name}",
)

TRACEBACK_REDUCER = instance_reducer(
    cls=TracebackType,
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

EXCEPTION_REDUCER = instance_reducer(
    cls=BaseException,
    priority=40,
    reduce=exception_reducer,
)

MAPPING_REDUCER = instance_reducer(
    cls=Mapping,
    priority=50,
    reduce=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "items": dict(obj),
    },
)

COLLECTION_REDUCER = instance_reducer(
    cls=Collection,
    priority=60,
    reduce=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "items": tuple(obj),
    },
)

FALLBACK_REDUCER = JSONReducer(
    name="fallback",
    priority=100,
    is_match=lambda obj: True,
    reduce=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "__repr__": repr(obj),
    },
)

ALL_REDUCERS: tuple[JSONReducer, ...] = tuple(
    sorted(x for x in locals().values() if isinstance(x, JSONReducer))
)
