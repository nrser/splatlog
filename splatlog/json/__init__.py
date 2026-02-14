"""
JSON serialization for log records.

Provides {py:class}`JSONEncoder` for converting Python objects to JSON-safe
representations, {py:class}`JSONFormatter` for formatting log records as JSON,
and a system of {py:class}`JSONReducer` functions for customizing how objects
are serialized.
"""

from .encoder import JSONEncoder
from .formatter import (
    LOCAL_TIMEZONE,
    ToJSONFormatter,
    JSONFormatter,
)
from .reducers import (
    JSONReducer,
    TO_JSON_ENCODABLE_REDUCER,
    CLASS_REDUCER,
    DATACLASS_REDUCER,
    ENUM_REDUCER,
    EXCEPTION_REDUCER,
    MAPPING_REDUCER,
    ALL_REDUCERS,
)

__all__ = [
    "JSONEncoder",
    "JSONFormatter",
    "LOCAL_TIMEZONE",
    "ToJSONFormatter",
    "JSONReducer",
    "TO_JSON_ENCODABLE_REDUCER",
    "CLASS_REDUCER",
    "DATACLASS_REDUCER",
    "ENUM_REDUCER",
    "EXCEPTION_REDUCER",
    "MAPPING_REDUCER",
    "ALL_REDUCERS",
]
