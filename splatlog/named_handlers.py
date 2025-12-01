"""Manage _named handlers_..."""

import logging
from pathlib import Path
from typing import Optional, Union, cast
from collections.abc import Mapping

from splatlog.json.json_formatter import JSONFormatter
from splatlog.lib.collections import partition_mapping
from splatlog.lib.text import fmt
from splatlog.lib.typeguard import satisfies
from splatlog.levels import get_level_value, is_level
from splatlog.locking import lock
from splatlog.rich_handler import RichHandler
from splatlog.typings import (
    ConsoleHandlerCastable,
    RichConsoleCastable,
    NamedHandlerCast,
    is_rich_console_castable,
)
from splatlog.verbosity.verbosity_levels_filter import VerbosityLevelsFilter


_registry: dict[str, NamedHandlerCast] = {}
_handlers: dict[str, None | logging.Handler] = {}


def check_name(name) -> None:
    if not isinstance(name, str):
        raise TypeError(
            "named handler names must be `str`, given {}: {}".format(
                fmt(type(name)), fmt(name)
            )
        )
    if name == "":
        raise ValueError("named handler names can not be empty")


def register_named_handler(name: str, cast: NamedHandlerCast):
    check_name(name)

    with lock():
        if name in _registry:
            raise KeyError(
                "Handler named {} already registered; cast function: {}".format(
                    fmt(name), fmt(_registry[name])
                )
            )
        _registry[name] = cast


def get_named_handler_cast(name: str):
    check_name(name)
    return _registry[name]


def named_handler(name: str):
    check_name(name)

    def decorator(cast: NamedHandlerCast) -> NamedHandlerCast:
        register_named_handler(name, cast)
        return cast

    return decorator


def get_named_handler(name: str) -> Optional[logging.Handler]:
    return _handlers.get(name)


def set_named_handler(name: str, value: object) -> None:
    check_name(name)
    cast = _registry[name]
    new_handler = cast(value)

    with lock():
        old_handler = _handlers.get(name)

        if new_handler is not old_handler:
            root_logger = logging.getLogger()

            if old_handler is not None:
                root_logger.removeHandler(old_handler)

            if new_handler is not None:
                root_logger.addHandler(new_handler)

            _handlers[name] = new_handler


@named_handler("console")
def cast_console_handler(
    value: ConsoleHandlerCastable,
) -> Optional[logging.Handler]:
    """Convert a value into either a `logging.Handler` or `None`.

    If neither of those make sense raises a `TypeError`.

    ##### Examples #####

    1.  `True` is cast to a new `RichHandler` with all default attributes.

        ```python
        >>> cast_console_handler(True)
        <RichHandler (NOTSET)>

        ```

    2.  `False` and `None` cast to `None`.

        ```python
        >>> cast_console_handler(False) is None
        True

        >>> cast_console_handler(None) is None
        True

        ```

    3.  Any `logging.Handler` instance is simply returned.

        ```python
        >>> import sys

        >>> handler = logging.StreamHandler(sys.stdout)

        >>> cast_console_handler(handler) is handler
        True

        ```

    4.  Any `collections.abc.Mapping` is used as the keyword arguments to
        construct a new `RichHandler`.

        ```python
        >>> handler = cast_console_handler(
        ...     dict(
        ...         console=sys.stdout,
        ...         verbosity_levels=dict(
        ...             some_mod=((0, "WARNING"), (1, "INFO")),
        ...         )
        ...     )
        ... )

        >>> isinstance(handler, RichHandler)
        True

        >>> handler.console.file is sys.stdout
        True

        >>> handler.verbosity_levels
        {'some_mod': <VerbosityLevelResolver [0]: WARNING, [1, ...]: INFO>}

        ```

    5.  Anything that `RichHandler` can cast to a `rich.console.Console` (see
        `RichHandler.cast_console`) is assigned as the console in a new
        `RichHandler` instance.

        ```python
        >>> from io import StringIO

        >>> sio = StringIO()
        >>> handler = cast_console_handler(sio)

        >>> isinstance(handler, RichHandler)
        True

        >>> handler.console.file is sio
        True

        >>> import sys
        >>> cast_console_handler("stdout").console.file is sys.stdout
        True

        ```

    6.  Any log level name or value is assigned as the level to a new
        `RichHandler` instance.

        ```python
        >>> cast_console_handler(logging.DEBUG).level == logging.DEBUG
        True

        >>> cast_console_handler("DEBUG").level == logging.DEBUG
        True

        ```

        Note that in the extremely bizarre case where you name a log level
        `"stdout"` (or `"STDOUT"`) you can not use `"stdout"` to create a
        handler with that level because `"stdout"` will be cast to a
        `RichHandler` with the `RichHandler.console` writing to `sys.stdout`.

        ```python
        >>> stdout_level_value = hash("stdout") # Use somewhat unique int

        >>> logging.addLevelName(stdout_level_value, "stdout")

        >>> cast_console_handler("stdout").level == stdout_level_value
        False

        ```

        Same applies for `"stderr"`.

    7.  Anythings else raises a `TypeError`.

        ```python
        >>> cast_console_handler([1, 2, 3])
        Traceback (most recent call last):
            ...
        TypeError:
            Expected
                None
                | logging.Handler
                | typing.Mapping[str, typing.Any]
                | bool
                | rich.console.Console
                | 'stdout'
                | 'stderr'
                | typing.IO[str]
                | int
                | str,
            given list: [1, 2, 3]

        ```
    """

    if value is True:
        return RichHandler()

    if value is None or value is False:
        return None

    if isinstance(value, logging.Handler):
        return value

    if isinstance(value, Mapping):
        return RichHandler(**value)

    if is_rich_console_castable(value):
        # NOTE  This `typing.cast` seems to be required because the
        #       `typing.TypeGuard` in `satisfies` does not evaluate correctly
        #       with a complex type such as `RichConsoleCastable`.
        return RichHandler(console=cast(RichConsoleCastable, value))

    if is_level(value):
        return RichHandler(level=value)

    raise TypeError(
        "Expected {}, given {}: {}".format(
            fmt(ConsoleHandlerCastable),
            fmt(type(value)),
            fmt(value),
        )
    )


@named_handler("export")
def cast_export_handler(value) -> Optional[logging.Handler]:
    if value is None or value is False:
        return None

    if isinstance(value, logging.Handler):
        return value

    if isinstance(value, Mapping):
        if "stream" in value:
            cls = logging.StreamHandler
        elif "filename" in value:
            cls = logging.FileHandler
        else:
            raise KeyError(
                (
                    "Mappings passed to {} must contain 'filename' or "
                    "'stream' keys, given {}"
                ).format(
                    fmt(cast_export_handler),
                    fmt(value),
                )
            )

        post_kwds, init_kwds = partition_mapping(
            value, {"level", "formatter", "verbosity_levels"}
        )

        handler = cls(**init_kwds)

        if "level" in post_kwds:
            handler.setLevel(get_level_value(post_kwds["level"]))

        formatter = post_kwds.get("formatter")

        # If a `logging.Formatter` was provided just assign that
        if isinstance(formatter, logging.Formatter):
            handler.formatter = formatter
        else:
            # Cast to a `JSONFormatter`
            handler.formatter = JSONFormatter.cast(formatter)

        if verbosity_levels := post_kwds.get("verbosity_levels"):
            VerbosityLevelsFilter.set_on(handler, verbosity_levels)

        return handler

    if isinstance(value, (str, Path)):
        handler = logging.FileHandler(filename=value)
        handler.formatter = JSONFormatter()
        return handler

    raise TypeError(
        "Expected {}, given {}: {!r}".format(
            fmt(Union[None, logging.Handler, Mapping, str, Path]),
            fmt(type(value)),
            fmt(value),
        )
    )
