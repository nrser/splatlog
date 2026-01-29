import dataclasses
from collections.abc import Callable, Mapping, Collection
from enum import Enum
from inspect import isclass
import traceback
from types import TracebackType
from typing import Any, Self

from splatlog.lib import fmt_type, has_method
from splatlog.typings import JSONEncodable, JSONReduceFn


@dataclasses.dataclass(frozen=True, order=True)
class JSONReducer:
    priority: int
    name: str
    is_match: Callable[[Any], bool]
    reduce: JSONReduceFn

    @classmethod
    def instance_reducer(
        cls, typ: type, priority: int, reduce: JSONReduceFn
    ) -> Self:
        return cls(
            name=fmt_type(typ),
            priority=priority,
            is_match=lambda obj: isinstance(obj, typ),
            reduce=reduce,
        )

    @classmethod
    def method_reducer(cls, method_name: str, priority: int) -> Self:
        return cls(
            name=f".{method_name}()",
            priority=priority,
            is_match=lambda obj: has_method(obj, method_name, req_arity=0),
            reduce=lambda obj: getattr(obj, method_name)(),
        )


def reduce_exception(error: BaseException) -> dict[str, JSONEncodable]:
    dct: dict[str, JSONEncodable] = dict(
        type=fmt_type(error.__class__),
        msg=str(error),
    )

    if error.__traceback__ is not None:
        dct["traceback"] = TRACEBACK_REDUCER.reduce(error.__traceback__)

    if error.__cause__ is not None:
        dct["cause"] = reduce_exception(error.__cause__)

    return dct


TO_JSON_ENCODABLE_REDUCER = JSONReducer.method_reducer(
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

ENUM_REDUCER = JSONReducer.instance_reducer(
    typ=Enum,
    priority=40,
    reduce=lambda obj: f"{fmt_type(obj.__class__)}.{obj.name}",
)

TRACEBACK_REDUCER = JSONReducer.instance_reducer(
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

EXCEPTION_REDUCER = JSONReducer.instance_reducer(
    typ=BaseException,
    priority=40,
    reduce=reduce_exception,
)

MAPPING_REDUCER = JSONReducer.instance_reducer(
    typ=Mapping,
    priority=50,
    reduce=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "items": dict(obj),
    },
)

COLLECTION_REDUCER = JSONReducer.instance_reducer(
    typ=Collection,
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
