import dataclasses
from collections.abc import Callable, Mapping, Collection
from enum import Enum
from inspect import isclass
import traceback
from types import TracebackType
from typing import Any, Type

from splatlog.lib import fmt_type, has_method

from .json_typings import JSONEncodable

THandleFn = Callable[[Any], JSONEncodable]


@dataclasses.dataclass(frozen=True, order=True)
class DefaultHandler:
    priority: int
    name: str
    is_match: Callable[[Any], bool]
    handle: THandleFn


def instance_handler(
    cls: Type, priority: int, handle: THandleFn
) -> DefaultHandler:
    return DefaultHandler(
        name=fmt_type(cls),
        priority=priority,
        is_match=lambda obj: isinstance(obj, cls),
        handle=handle,
    )


def method_handler(method_name: str, priority: int) -> DefaultHandler:
    return DefaultHandler(
        name=f".{method_name}()",
        priority=priority,
        is_match=lambda obj: has_method(obj, method_name, req_arity=0),
        handle=lambda obj: getattr(obj, method_name)(),
    )


def handle_exception(error: BaseException) -> dict[str, JSONEncodable]:
    dct: dict[str, JSONEncodable] = dict(
        type=fmt_type(error.__class__),
        msg=str(error),
    )

    if error.__traceback__ is not None:
        dct["traceback"] = TRACEBACK_HANDLER.handle(error.__traceback__)

    if error.__cause__ is not None:
        dct["cause"] = handle_exception(error.__cause__)

    return dct


TO_JSON_ENCODABLE_HANDLER = method_handler(
    method_name="to_json_encodable",
    priority=10,
)

CLASS_HANDLER = DefaultHandler(
    name="class",
    priority=20,
    is_match=isclass,
    handle=fmt_type,
)

DATACLASS_HANDLER = DefaultHandler(
    name="dataclasses.dataclass",
    priority=30,
    is_match=dataclasses.is_dataclass,
    handle=dataclasses.asdict,
)

ENUM_HANDLER = instance_handler(
    cls=Enum,
    priority=40,
    handle=lambda obj: f"{fmt_type(obj.__class__)}.{obj.name}",
)

TRACEBACK_HANDLER = instance_handler(
    cls=TracebackType,
    priority=40,
    handle=lambda tb: [
        dict(
            file=frame_summary.filename,
            line=frame_summary.lineno,
            name=frame_summary.name,
            text=frame_summary.line,
        )
        for frame_summary in traceback.extract_tb(tb)
    ],
)

EXCEPTION_HANDLER = instance_handler(
    cls=BaseException,
    priority=40,
    handle=handle_exception,
)

MAPPING_HANDLER = instance_handler(
    cls=Mapping,
    priority=50,
    handle=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "items": dict(obj),
    },
)

COLLECTION_HANDLER = instance_handler(
    cls=Collection,
    priority=60,
    handle=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "items": tuple(obj),
    },
)

FALLBACK_HANDLER = DefaultHandler(
    name="fallback",
    priority=100,
    is_match=lambda obj: True,
    handle=lambda obj: {
        "__class__": fmt_type(obj.__class__),
        "__repr__": repr(obj),
    },
)

ALL_HANDLERS: tuple[DefaultHandler, ...] = tuple(
    sorted(x for x in locals().values() if isinstance(x, DefaultHandler))
)
