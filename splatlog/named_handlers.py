"""
Registry for _named handlers_ — a mapping from short string names (like
`"console"` and `"export"`) to factory functions that build
{py:class}`logging.Handler` instances from user-supplied configuration values.

Named handlers are the mechanism behind the keyword arguments to
{py:func}`splatlog.setup`: each keyword name is looked up in the registry and
the corresponding factory function converts the value into a handler that is
attached to the root logger.
"""

import logging
from pathlib import Path
from typing import IO, Any, Literal, Union, overload
from collections.abc import Callable, Mapping
import keyword

from splatlog.json import JSONFormatter
from splatlog.levels import Filter
from splatlog.lib import satisfies
from splatlog.lib.collections import partition_mapping
from splatlog.lib.text import fmt
from splatlog.locking import lock
from splatlog.rich.handler import RichHandler
from splatlog.types import (
    ToConsoleHandler,
    NamedHandlerFactory,
    ToExportHandler,
    OnConflict,
    assert_never,
    can_be_level,
    is_to_rich_console,
)


_registry: dict[str, NamedHandlerFactory] = {}
"""
Map from handler name to the factory function that builds a
{py:class}`logging.Handler` from a configuration value.
"""

_handlers: dict[str, None | logging.Handler] = {}
"""
Map from handler name to the currently active {py:class}`logging.Handler`
(or {py:data}`None` if deleted).
"""


def check_name(name: object) -> None:
    """
    Validate that `name` is a valid named handler name.

    Named handler names must be valid Python identifiers (since they are used
    as keyword arguments to {py:func}`splatlog.setup`) and must not be Python
    keywords.

    ## Parameters

    -   `name`: The value to validate.

    ## Raises

    -   {py:class}`TypeError` if `name` is not a {py:class}`str`.
    -   {py:class}`ValueError` if `name` is not {py:meth}`str.isidentifier` or
        is {py:func}`keyword.iskeyword`.

    ## Examples

    ```python
    >>> check_name("console")

    >>> check_name("")
    Traceback (most recent call last):
        ...
    ValueError: named handler name must be a valid Python identifier, given ''

    >>> check_name("not-valid")
    Traceback (most recent call last):
        ...
    ValueError: named handler name must be a valid Python identifier, given 'not-valid'

    >>> check_name("class")
    Traceback (most recent call last):
        ...
    ValueError: named handler name must not be a Python keyword, given 'class'

    >>> check_name(123)
    Traceback (most recent call last):
        ...
    TypeError: named handler names must be `str`, given int: 123

    ```
    """
    if not isinstance(name, str):
        raise TypeError(
            "named handler names must be `str`, given {}: {}".format(
                fmt(type(name)), fmt(name)
            )
        )
    if not name.isidentifier():
        raise ValueError(
            f"named handler name must be a valid Python identifier, "
            f"given {fmt(name)}"
        )

    if keyword.iskeyword(name):
        raise ValueError(
            f"named handler name must not be a Python keyword, "
            f"given {fmt(name)}"
        )


def put_factory(
    name: str,
    factory: NamedHandlerFactory,
    *,
    on_conflict: OnConflict = "raise",
) -> None:
    """
    Register a factory function for a named handler.

    :::{tip}

    If you're defining a factory function you probably want the
    {py:deco}`register` decorator, which calls this function for you.

    :::

    ## Parameters

    -   `name`: The handler name (e.g. `"console"`).

    -   `factory`: A callable that accepts a configuration value and returns a
        {py:class}`logging.Handler`.

    -   `on_conflict`: What to do if `name` is already registered:

        -   `"raise"` (default) — raise an exception.
        -   `"ignore"` — do nothing.
        -   `"replace"` — overwrite it.
    """
    check_name(name)

    with lock():
        if name in _registry:
            match on_conflict:
                case "raise":
                    raise KeyError(
                        (
                            "Handler named {} already registered; "
                            "factory function: {}"
                        ).format(fmt(name), fmt(_registry[name]))
                    )
                case "ignore":
                    return
                case "replace":
                    pass
        _registry[name] = factory


def get_factory(name: str) -> NamedHandlerFactory:
    """
    Get the registered factory function for a named handler.

    ## Parameters

    -   `name`: The handler name to look up.

    ## Returns

    The {py:class}`~splatlog.types.NamedHandlerFactory` registered for `name`.

    ## Raises

    -   {py:class}`KeyError` if no factory function is registered for `name`.
    """
    check_name(name)
    return _registry[name]


def register(
    name: str, *, on_conflict: OnConflict = "raise"
) -> Callable[[NamedHandlerFactory], NamedHandlerFactory]:
    """
    Create a decorator that registers the decorated function as a named handler
    factory function, allowing `name` to be used like the `console` and `export`
    arguments to {py:func}`splatlog.setup`.

    ## Parameters

    -   `name`: name that will be used to configure the handler.

    -   `on_conflict`: what to do if a handler with `name` is already
        registered:

        -   `"raise"` (default) — raise an exception.
        -   `"ignore"` — do nothing.
        -   `"replace"` — overwrite it.

    ## Examples

    ```python
    from typing import Any
    import logging
    import splatlog

    @splatlog.named_handlers.register("custom")
    def custom_handler_factory(value: Any) -> logging.Handler:
        ...
    ```
    """
    # Raise an `Exception` if `name` is invalid. Right now `name` just need to
    # be a non-empty string.
    check_name(name)

    def decorator(factory: NamedHandlerFactory) -> NamedHandlerFactory:
        put_factory(name, factory, on_conflict=on_conflict)
        return factory

    return decorator


# Accessors
# ============================================================================


def get(name: str) -> logging.Handler | None:
    """
    Get the currently active handler for `name`, or {py:data}`None` if no
    handler is set.

    ## Parameters

    -   `name`: The handler name to look up.

    ## Returns

    The {py:class}`logging.Handler` or {py:data}`None`.
    """
    return _handlers.get(name)


@overload
def put(
    name: Literal["console"], value: ToConsoleHandler
) -> None: ...


@overload
def put(
    name: Literal["export"], value: ToExportHandler
) -> None: ...


@overload
def put(name: str, value: Any) -> None: ...


def put(name: str, value: Any) -> None:
    """
    Construct a {py:class}`logging.Handler` from `value` and add it to the root
    {py:class}`logging.Logger`.

    Uses the factory function registered by `name` with
    {py:func}`put_factory` or the {py:deco}`register` decorator to convert
    `value` to a handler. A factory function _must_ be registered for `name`,
    or a {py:class}`KeyError` will be raised (this is primarily to catch typos).

    After putting a named handler you may access it with {py:func}`get`. In
    practice, named handlers are put mostly through {py:func}`splatlog.setup`,
    which calls this function.

    Acquires the {py:func}`splatlog.locking.lock` to do the root logger access
    and mutations. Construction of the handler is done before acquiring the
    lock. If the new handler is identical to the old handler, the swap is
    skipped.

    ## Parameters

    -   `name`: The handler name (must be registered).
    -   `value`: Configuration value passed to the factory function. If
        {py:data}`None` or {py:data}`False`, the handler is deleted instead.
    """

    # When passed `None` or `False` hand-off to the deleter. `False` is used
    # from `splatlog.setup` because `None` is ignored.
    #
    # Standardizes deleting named handlers, relieves converters from having to
    # handle them.
    if value is None or value is False:
        return delete(name)

    check_name(name)

    build = _registry[name]
    new_handler = build(value)

    if not isinstance(new_handler, logging.Handler):
        raise TypeError(
            (
                "Expected {} handler builder to return {}; gave {}: {} "
                + "and received {}: {}"
            ).format(
                fmt(name),
                fmt(logging.Handler),
                fmt(type(value)),
                fmt(value),
                fmt(type(new_handler)),
                fmt(new_handler),
            )
        )

    with lock():
        old_handler = _handlers.get(name)

        if new_handler is not old_handler:
            root_logger = logging.getLogger()

            if old_handler is not None:
                root_logger.removeHandler(old_handler)

            if new_handler is not None:
                root_logger.addHandler(new_handler)

            _handlers[name] = new_handler


def delete(name: str) -> None:
    """
    Remove a named handler from the root {py:class}`logging.Logger`.

    If no handler is currently set for `name`, this is a no-op.

    ## Parameters

    -   `name`: The handler name to remove.
    """
    check_name(name)

    with lock():
        old_handler = _handlers.get(name)

        if old_handler is not None:
            root_logger = logging.getLogger()

            root_logger.removeHandler(old_handler)

            del _handlers[name]


# Conversion
# ============================================================================
#
# Converting values to the built-in `console` and `export` named handlers.
# Serve as examples for adding custom ones.


@register("console")
def to_console_handler(value: ToConsoleHandler) -> logging.Handler:
    """
    Factory function for the `console` named handler. Converts a
    {py:class}`~splatlog.types.ToConsoleHandler` value into a
    {py:class}`logging.Handler`.

    ## Parameters

    -   `value`: The configuration value to convert.

    ## Returns

    A {py:class}`logging.Handler` (typically a
    {py:class}`~splatlog.rich.RichHandler`).

    ## Raises

    -   {py:class}`TypeError` if `value` cannot be converted.

    ## Examples

    1.  {py:data}`True` is converted to a new
        {py:class}`~splatlog.rich.RichHandler` with all default
        attributes.

        ```python
        >>> to_console_handler(True)
        <RichHandler (NOTSET)>

        ```

    2.  Any {py:class}`collections.abc.Mapping` is used as the keyword arguments
        to construct a new {py:class}`~splatlog.rich.RichHandler`.

        ```python
        >>> import sys
        >>> from splatlog.types import Verbosity

        >>> handler = to_console_handler(
        ...     dict(
        ...         console=sys.stdout,
        ...         level={
        ...             "some_mod": {
        ...                 Verbosity(0): "WARNING",
        ...                 Verbosity(1): "INFO",
        ...             }
        ...         }
        ...     )
        ... )

        >>> isinstance(handler, RichHandler)
        True

        >>> handler.console.file is sys.stdout
        True

        >>> len(handler.filters)
        1

        ```

    3.  Anything that can be converted to a {py:class}`rich.console.Console`
        (see {py:func}`splatlog.rich.to_console`) is assigned as the console in
        a new {py:class}`~splatlog.rich.RichHandler`.

        ```python
        >>> from io import StringIO

        >>> sio = StringIO()
        >>> handler = to_console_handler(sio)

        >>> isinstance(handler, RichHandler)
        True

        >>> handler.console.file is sio
        True

        >>> import sys
        >>> to_console_handler("stdout").console.file is sys.stdout
        True

        ```

    4.  Any log level name or value is assigned as the level to a new
        {py:class}`~splatlog.rich.RichHandler`.

        ```python
        >>> to_console_handler(logging.DEBUG).level == logging.DEBUG
        True

        >>> to_console_handler("DEBUG").level == logging.DEBUG
        True

        ```

        Note that in the extremely bizarre case where you name a log level
        `"stdout"` (or `"STDOUT"`) you cannot use `"stdout"` to create a
        handler with that level because `"stdout"` will be converted to a
        {py:class}`~splatlog.rich.RichHandler` writing to
        {py:data}`sys.stdout`.

        ```python
        >>> stdout_level_value = hash("stdout") # Use somewhat unique int

        >>> logging.addLevelName(stdout_level_value, "stdout")

        >>> to_console_handler("stdout").level == stdout_level_value
        False

        ```

        Same applies for `"stderr"`.

    5.  Anything else raises a {py:class}`TypeError`.

        ```python
        >>> to_console_handler([1, 2, 3])
        Traceback (most recent call last):
            ...
        AssertionError:
            Expected
                `logging.Handler
                | collections.abc.Mapping[str, typing.Any]
                | True
                | int
                | str
                | rich.console.Console
                | 'stdout'
                | 'stderr'
                | typing.IO[str]`,
            given `list`: `[1, 2, 3]`

        ```
    """

    if value is True:
        return RichHandler()

    if isinstance(value, logging.Handler):
        return value

    if isinstance(value, Mapping):
        return RichHandler(**value)

    if is_to_rich_console(value):
        return RichHandler(console=value)

    if can_be_level(value):
        return RichHandler(level=value)

    assert_never(value, ToConsoleHandler)


@register("export")
def to_export_handler(value: ToExportHandler) -> logging.Handler:
    """
    Convert a {py:class}`~splatlog.types.ToExportHandler` value into a
    {py:class}`logging.Handler` for file/stream export (JSON Lines).

    ## Parameters

    -   `value`: The configuration value to convert. Accepted forms:

        -   {py:class}`collections.abc.Mapping` with a `"filename"` or
            `"stream"` key — used as keyword arguments to
            {py:class}`logging.FileHandler` or {py:class}`logging.StreamHandler`
            respectively. May also contain `"level"` and `"formatter"` keys.

        -   {py:class}`str` or {py:class}`pathlib.Path` — shorthand for a
            {py:class}`logging.FileHandler` with a default
            {py:class}`~splatlog.json.JSONFormatter`.

        -   {py:class}`typing.IO` — used as a stream for
            {py:class}`logging.StreamHandler` with a default
            {py:class}`~splatlog.json.JSONFormatter`.

    ## Returns

    A {py:class}`logging.Handler`.

    ## Raises

    -   {py:class}`KeyError`: if a {py:class}`collections.abc.Mapping` is given
        without `"filename"` or `"stream"`.

    -   {py:class}`TypeError`: if `value` cannot be converted.
    """
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
                    fmt(to_export_handler),
                    fmt(value),
                )
            )

        post_kwds, init_kwds = partition_mapping(value, {"level", "formatter"})

        handler = cls(**init_kwds)

        if "level" in post_kwds:
            Filter.apply(handler, post_kwds["level"])

        formatter = post_kwds.get("formatter")

        # If a `logging.Formatter` was provided just assign that
        if isinstance(formatter, logging.Formatter):
            handler.formatter = formatter
        else:
            # Cast to a `JSONFormatter`
            handler.formatter = JSONFormatter.of(formatter)

        return handler

    if isinstance(value, (str, Path)):
        handler = logging.FileHandler(filename=value)
        handler.formatter = JSONFormatter()
        return handler

    if satisfies(value, IO[str]):
        handler = logging.StreamHandler(value)
        handler.formatter = JSONFormatter()
        return handler

    raise TypeError(
        "Expected {}, given {}: {!r}".format(
            fmt(Union[None, logging.Handler, Mapping, str, Path]),
            fmt(type(value)),
            fmt(value),
        )
    )
