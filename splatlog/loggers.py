"""
Defines {py:class}`SplatLogger` and associated classes ({py:class}`ClassLogger`,
{py:class}`SelfLogger`, {py:class}`LoggerProperty`), as well as the global
factory functions {py:func}`get` and {py:func}`get_for`.

These are co-located in a single module because of circular dependencies between
the logger classes and the factory functions.
"""

from __future__ import annotations
from inspect import isclass
import logging
from functools import cache, wraps
from collections.abc import Generator, Callable
from types import GenericAlias, MappingProxyType
from typing import overload

import rich.repr

from splatlog.levels import fmt_level
from splatlog.lib.collections import partition_mapping
from splatlog.lib.text import fmt
from splatlog.types import ToLevel, Level, to_level

_NOT_FOUND = object()
"""
Unique sentinel used by {py:class}`LoggerProperty` to detect when a cached
logger has not ye been set.
"""


@cache
def get(name: str) -> SplatLogger:
    """
    Get a {py:class}`SplatLogger` by name.

    Calls {py:func}`logging.getLogger` and wraps it in a {py:class}`SplatLogger`
    adapter. Results are cached via {py:func}`functools.cache`.

    ## Parameters

    -   `name`: The logger name (typically a module name like `__name__`).

    ## Returns

    A {py:class}`SplatLogger` wrapping the underlying
    {py:class}`logging.Logger`.
    """
    return SplatLogger(logging.getLogger(name))


def get_for(obj: object) -> SplatLogger:
    """
    Get a {py:class}`SplatLogger` that is associated with an object.

    ## Parameters

    -   `obj`: The object to get a logger for. The type determines the logger
        kind:

        1.  {py:class}`str`: a regular _named logger_ is returned, same as
            calling {py:func}`get`. These are cached globally.

        2.  {py:class}`type`: a {py:class}`ClassLogger` is returned, named
            `{__module__}.{__qualname__}`.

        3.  Anything else: a {py:class}`SelfLogger` is returned. The type of
            `obj` initializes {py:class}`ClassLogger`, and a `self` attribute
            is added to processed {py:class}`logging.LogRecord` to identify
            `obj` as the record source. See {py:class}`SelfLogger` for details
            on how to hook into that.

            {py:class}`SelfLogger` instances are _not_ cached; store a
            reference on the class for repeated use (see
            {py:class}`LoggerProperty`).

    ## Examples

    First, we'll create a "module logger" in the usual way.

    ```python
    >>> module_logger = get_for(__name__)

    >>> isinstance(module_logger, SplatLogger)
    True

    >>> isinstance(module_logger, (ClassLogger, SelfLogger))
    False

    >>> module_logger.name
    'splatlog.loggers'

    ```

    Next we define a minimal class to associate loggers with. Instances have
    names and the `_splatlog_self_` property returns a dictionary with the name.

    ```python
    >>> class MyClass:
    ...     name: str
    ...
    ...     def __init__(self, name: str):
    ...         self.name = name
    ...
    ...     @property
    ...     def _splatlog_self_(self) -> object:
    ...         return dict(name=self.name)

    ```

    Now we can check out class and instance loggers for it.

    ```python
    >>> class_logger = get_for(MyClass)
    >>> isinstance(class_logger, SplatLogger)
    True
    >>> isinstance(class_logger, ClassLogger)
    True
    >>> isinstance(class_logger, SelfLogger)
    False
    >>> class_logger.name
    'splatlog.loggers.MyClass'
    >>> class_logger.class_name
    'MyClass'

    >>> instance = MyClass(name="xyz")
    >>> instance_logger = get_for(instance)
    >>> isinstance(instance_logger, SelfLogger)
    True
    >>> instance_logger.name
    'splatlog.loggers.MyClass'
    >>> instance_logger.class_name
    'MyClass'
    >>> instance_logger.get_identity()
    {'name': 'xyz'}

    ```
    """

    if isinstance(obj, str):
        return get(obj)

    if isclass(obj):
        return ClassLogger(obj)

    return SelfLogger(obj)


class LoggerProperty:
    """
    A property that resolves to a {py:class}`ClassLogger` when accessed through
    the class object and a {py:class}`SelfLogger` when accessed through
    instances.

    The {py:class}`ClassLogger` is cached in an attribute on the class'
    `__dict__` and each {py:class}`SelfLogger` is cached on the instance.

    ## Examples

    A "standard" class.

    ```python
    >>> class AnotherClass:
    ...     _log = LoggerProperty()
    ...
    ...     name: str
    ...
    ...     def __init__(self, name: str):
    ...         self.name = name
    ...
    ...     @property
    ...     def _splatlog_self_(self) -> object:
    ...         return dict(name=self.name)

    >>> isinstance(AnotherClass._log, ClassLogger)
    True
    >>> AnotherClass._log.class_name
    'AnotherClass'

    >>> instance = AnotherClass(name="blah")
    >>> isinstance(instance._log, SelfLogger)
    True
    >>> instance._log.class_name
    'AnotherClass'
    >>> instance._log.get_identity()
    {'name': 'blah'}

    ```

    A frozen dataclass, which has different set semantics.

    ```python
    >>> from dataclasses import dataclass

    >>> @dataclass(frozen=True)
    ... class Chiller:
    ...     _log = LoggerProperty()
    ...
    ...     name: str
    ...
    ...     @property
    ...     def _splatlog_self_(self) -> object:
    ...         return dict(name=self.name)

    >>> isinstance(Chiller._log, ClassLogger)
    True

    >>> Chiller._log.class_name
    'Chiller'

    >>> cold_one = Chiller(name="brrrr!")
    >>> isinstance(cold_one._log, SelfLogger)
    True

    >>> cold_one._log.class_name
    'Chiller'
    >>> cold_one._log.get_identity()
    {'name': 'brrrr!'}

    ```
    """

    _attr_name: str | None = None
    """Internal storage name derived from the descriptor name."""

    @property
    def attr_name(self) -> str | None:
        """The attribute name used to cache loggers, or {py:data}`None` if
        {py:meth}`__set_name__` has not been called."""
        return self._attr_name

    def __set_name__(self, owner: type[object], name: str) -> None:
        attr_name = f"_splatlog_logger_{name}"
        if self._attr_name is None:
            self._attr_name = attr_name
        elif self._attr_name != attr_name:
            raise TypeError(
                f"Cannot assign the same {self.__class__.__name__} to two "
                f"different names ({self._attr_name!r} and {attr_name!r})"
            )

    def __get__(
        self, instance: object | None, owner: type[object] | None = None
    ) -> SplatLogger:
        if instance is None:
            if owner is None:
                raise TypeError(
                    "`owner` and `instance` arguments can not both be `None`"
                )
            return self.get_logger_from(owner)
        return self.get_logger_from(instance)

    __class_getitem__ = classmethod(GenericAlias)

    def get_logger_from(self, obj: object) -> SplatLogger:
        """
        Retrieve or create a cached logger for `obj`.

        ## Parameters

        -   `obj`: A class or instance to get a logger for.

        ## Returns

        A {py:class}`ClassLogger` (if `obj` is a class) or a
        {py:class}`SelfLogger` (if `obj` is an instance).
        """
        if attr_name := self._attr_name:
            # Using `getattr` here doesn't work because it resolves the class
            # attribute if it exists
            logger = obj.__dict__.get(attr_name, _NOT_FOUND)
            if logger is _NOT_FOUND:
                logger = get_for(obj)

                if isinstance(obj.__dict__, MappingProxyType):
                    # Can't assign to `__dict__` of a class because it's a
                    # `mappingproxy` so use `setattr`
                    setattr(obj, attr_name, logger)
                else:
                    # Can't use `setattr` here because it will fail on
                    # frozen dataclass instances
                    obj.__dict__[attr_name] = logger

            if not isinstance(logger, SplatLogger):
                raise TypeError(
                    "Expected {}.__dict__[{}] to be {}, found {}: {}".format(
                        fmt(obj),
                        fmt(self._attr_name),
                        fmt(SplatLogger),
                        fmt(type(logger)),
                        fmt(logger),
                    )
                )
            return logger
        raise TypeError(
            f"Cannot use {self.__class__.__name__} instance without "
            "calling __set_name__ on it."
        )


class SplatLogger(logging.LoggerAdapter):
    """
    A {py:class}`logging.LoggerAdapter` that treats double-splat keyword
    arguments as a map of names to values to be logged.

    This map is added as `"data"` to the `extra` mapping that is part of the
    log method API, where it eventually is assigned as a `data` attribute on
    the emitted {py:class}`logging.LogRecord`.

    This allows logging invocations like:

    ```python
    logger.debug(
        "Check this out!",
        x="hey",
        y="ho",
        z={"lets": "go"},
    )
    ```
    """

    def process(self, msg, kwargs):
        """
        Override {py:meth}`logging.LoggerAdapter.process` to extract
        non-standard keyword arguments into a `data` dict attached to the
        {py:class}`logging.LogRecord`.
        """
        new_kwargs, data = partition_mapping(
            kwargs, {"exc_info", "extra", "stack_info", "stacklevel"}
        )
        if extra := new_kwargs.get("extra"):
            extra["_splatlog_"] = True
            extra["data"] = data
        else:
            new_kwargs["extra"] = {"_splatlog_": True, "data": data}
        return msg, new_kwargs

    def iter_handlers(self) -> Generator[logging.Handler, None, None]:
        """
        Iterate through the applicable {py:class}`logging.Handler`.

        Always yields from {py:attr}`logging.Logger.handlers` of the
        {py:class}`logging.Logger` that this adapter wraps. If that logger is
        set to {py:attr}`logging.Logger.propagate` then continues walking up the
        {py:attr}`logging.Logger.parent` chain, yielding the ancestor handlers
        as well.
        """
        logger = self.logger
        while logger:
            yield from logger.handlers
            if not logger.propagate:
                break
            else:
                logger = logger.parent

    def addHandler(self, hdlr: logging.Handler) -> None:
        """
        Delegate to the underlying logger.
        """
        return self.logger.addHandler(hdlr)

    def removeHandler(self, hdlr: logging.Handler) -> None:
        """
        Delegate to the underlying logger.
        """
        return self.logger.removeHandler(hdlr)

    @property
    def level(self) -> Level:
        """The logging level of the underlying {py:class}`logging.Logger`."""
        return self.logger.level

    def setLevel(self, level: ToLevel) -> None:
        """Set the logging level, accepting names or integers."""
        super().setLevel(to_level(level))

    def getChild(self, suffix: str) -> SplatLogger:
        """
        Get a child logger with the given suffix appended to this logger's
        name.
        """
        if self.logger.root is not self.logger:
            suffix = ".".join((self.logger.name, suffix))
        return get(suffix)

    @overload
    def inject(self, fn: Callable, /) -> Callable: ...

    @overload
    def inject(self, *, level: ToLevel | None = None) -> Callable[[Callable], Callable]: ...

    def inject(self, *args, **kwds) -> Callable:
        """
        Decorator that injects a child logger as a `log` keyword argument.

        If the wrapped function is called without a `log` kwarg, a child
        logger named after the function is automatically provided.
        """
        match args:
            case (fn,) if isinstance(fn, Callable):
                @wraps(fn)
                def log_inject_wrapper(*args, **kwds):
                    if "log" in kwds:
                        return fn(*args, **kwds)
                    else:
                        return fn(*args, log=self.getChild(fn.__name__), **kwds)

                return log_inject_wrapper

            case _:
                level = kwds.get("level")

                def decorator(fn):
                    child = self.getChild(fn.__name__)
                    if level is not None:
                        child.setLevel(level)

                    @wraps(fn)
                    def log_inject_wrapper(*args, **kwds):
                        if "log" in kwds:
                            return fn(*args, **kwds)
                        else:
                            return fn(*args, log=child, **kwds)

                    return log_inject_wrapper

                return decorator

    def __rich_repr__(self) -> rich.repr.Result:
        """
        Custom rich representation, consisting of the logger name, level, and
        lists of attached handlers and filters.
        """
        yield self.logger.name
        yield "level", fmt_level(self.logger.level)

        if handlers := self.logger.handlers:
            yield "handlers", handlers

        if filters := self.logger.filters:
            yield "filters", filters


class ClassLogger(SplatLogger):
    """
    A {py:class}`SplatLogger` for a specific class, wrapping the
    {py:class}`logging.Logger` for the fully-qualified class name
    (`{__module__}.{__qualname__}`).

    Adds the qualified name of the class to each
    {py:class}`logging.LogRecord` it processes as a `class_name` attribute.

    ## Examples

    Use through the {py:class}`LoggerProperty`:

    ```python
    >>> class SomeClass:
    ...     _log = LoggerProperty()
    ...
    ...     @classmethod
    ...     def do_something(cls):
    ...         cls._log.info("doing something!")

    >>> isinstance(SomeClass._log, ClassLogger)
    True

    ```
    """

    _class_name: str
    """The qualified name of the class this logger is for."""

    def __init__(self, cls: type[object]):
        """
        ## Parameters

        -   `cls`: The class to create a logger for.
        """
        super().__init__(
            logging.getLogger(f"{cls.__module__}.{cls.__qualname__}")
        )
        self._class_name = cls.__qualname__

    @property
    def class_name(self) -> str:
        """The qualified name of the class."""
        return self._class_name

    def process(self, msg, kwargs):
        """Add `class_name` to the record's extra data."""
        msg, new_kwargs = super().process(msg, kwargs)
        new_kwargs["extra"]["class_name"] = self._class_name
        return msg, new_kwargs


class SelfLogger(ClassLogger):
    """
    A {py:class}`ClassLogger` for a specific _instance_, adding a `self`
    attribute to each {py:class}`logging.LogRecord` to identify the instance.

    Only use this when you need to know _which_ instance a log record was
    emitted from.

    ## The `self` Identifier

    A `self` attribute is added to each log record emitted by `SelfLogger`,
    which will be displayed by {py:class}`splatlog.rich.RichHandler`. At
    construction, `SelfLogger` checks the target `obj` for an attribute named
    `_splatlog_self_`.

    If that attribute is a {py:class}`~collections.abc.Callable`, it will be
    called with zero arguments **each and every time** a record is processed to
    get the value for `self`. Otherwise the attribute value itself will be used
    as `self`.

    If no `_splatlog_self_` attribute is present on `obj` then
    `hex(id(obj))` is used.
    """

    get_identity: Callable[[], object]
    """Callable that returns the identity value for this instance."""

    def __init__(self, obj: object):
        """
        Construct a {py:class}`SelfLogger` for a particular object `obj`.

        ## Parameters

        -   `obj`: The instance to create a logger for.
        """
        super().__init__(obj.__class__)

        self.set_identity(getattr(obj, "_splatlog_self_", hex(id(obj))))

    def set_identity(self, identity: object) -> None:
        """
        Set the identity source. If `identity` is callable it will be invoked
        on each log record; otherwise the value is captured.
        """
        if isinstance(identity, Callable):
            self.get_identity = identity
        else:
            self.get_identity = lambda: identity

    def process(self, msg, kwargs):
        """Add `self` identity to the record's extra data."""
        msg, new_kwargs = super().process(msg, kwargs)
        new_kwargs["extra"]["self"] = self.get_identity()
        return msg, new_kwargs
