"""
Defines `SplatLogger` and associated classes, as well as the global "get"
functions like `get_logger` and `get_logger_for` (because interdependency makes
it difficult or impossible to define them in separate files).
"""

from __future__ import annotations
from inspect import isclass
import logging
from functools import cache, wraps
from collections.abc import Generator
from types import GenericAlias, MappingProxyType
from typing import Callable, Optional, Type

from splatlog.levels import to_level_value
from splatlog.lib.collections import partition_mapping
from splatlog.lib.text import fmt
from splatlog.typings import Level, LevelValue

#: Unique sentinel object used by `LoggerProperty` to tell when a default
#: was returned.
_NOT_FOUND = object()


@cache
def get_logger(name: str) -> SplatLogger:
    """
    The core logger-getter method, equivalent to `logging.getLogger` but
    returning a `SplatLogger` adapter.
    """
    return SplatLogger(logging.getLogger(name))


#: `logging`-style camel-case alias of `get_logger`, though we prefer to use
#: the snake-case one in practice.
getLogger = get_logger


def get_logger_for(obj: object) -> SplatLogger:
    """
    Get a logger that is associated with an object.

    There are three types, depending on the type of `obj`:

    1.  When `obj` is a `str` a regular-old _named logger_ will be returned,
        same as calling `get_logger`. As such these instances are cached
        globally.

    2.  When `obj` is a class (via `inspect.isclass`) a `ClassLogger` instance
        will be returned.

        `ClassLogger` is an extension of `SplatLogger` (and hence a
        `logging.LoggerAdapter`) that adapts the `logging.Logger` for the module
        the class is defined in and adds the qualified name of the class to
        `logging.LogRecord` that it processes as a `class_name` attribute.

        `ClassLogger` instances are _not_ cached, and it is expected that the
        user will store a reference on the class for repeated use (see
        `LoggerProperty`).

    3.  When `obj` is anything else a `SelfLogger` instance will be returned.

        `SelfLogger` is an extension of `ClassLogger`, where:

        1.  The type of `obj` is used to initialize `ClassLogger`. Hence
            processed `logging.LogRecord` will have

            ```python
            record.class_name = obj.__class__.__qualname__
            ```

        2.  A `self` attribute is added to processed `logging.LogRecord` to
            identify `obj` itself as the record source. See `SelfLogger` for
            details on how to hook into that.

        `SelfLogger` instances are _not_ cached, and it is expected that the
        user will store a reference on the class for repeated use (see
        `LoggerProperty`).

    ##### Examples #####

    First, we'll create a "module logger" in the usual way.

    ```python
    >>> module_logger = get_logger_for(__name__)

    >>> isinstance(module_logger, SplatLogger)
    True

    >>> isinstance(module_logger, (ClassLogger, SelfLogger))
    False

    >>> module_logger.name
    'splatlog.splat_logger'

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
    >>> class_logger = get_logger_for(MyClass)
    >>> isinstance(class_logger, SplatLogger)
    True
    >>> isinstance(class_logger, ClassLogger)
    True
    >>> isinstance(class_logger, SelfLogger)
    False
    >>> class_logger.name
    'splatlog.splat_logger'
    >>> class_logger.class_name
    'MyClass'

    >>> instance = MyClass(name="xyz")
    >>> instance_logger = get_logger_for(instance)
    >>> isinstance(instance_logger, SelfLogger)
    True
    >>> instance_logger.name
    'splatlog.splat_logger'
    >>> instance_logger.class_name
    'MyClass'
    >>> instance_logger.get_identity()
    {'name': 'xyz'}

    ```
    """

    if isinstance(obj, str):
        return get_logger(obj)

    if isclass(obj):
        return ClassLogger(obj)

    return SelfLogger(obj)


class LoggerProperty:
    """
    A property that resolves to a `ClassLogger` when accessed through the
    class object and a `SelfLogger` when accessed through instances.

    The `ClassLogger` is cached in an attribute on the class' `__dict__` and
    each `SelfLogger` is cached in an attribute on said instance.

    ##### Examples #####

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

    _attr_name: Optional[str] = None

    @property
    def attr_name(self) -> Optional[str]:
        return self._attr_name

    def __set_name__(self, owner: Type[object], name: str) -> None:
        attr_name = f"_splatlog_logger_{name}"
        if self._attr_name is None:
            self._attr_name = attr_name
        elif self._attr_name != attr_name:
            raise TypeError(
                f"Cannot assign the same {self.__class__.__name__} to two "
                f"different names ({self._attr_name!r} and {attr_name!r})"
            )

    def __get__(
        self, instance: Optional[object], owner: Optional[Type[object]] = None
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
        if attr_name := self._attr_name:
            # Using `getattr` here doesn't work because it resolves the class
            # attribute if it exists
            logger = obj.__dict__.get(attr_name, _NOT_FOUND)
            if logger is _NOT_FOUND:
                logger = get_logger_for(obj)

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
    """\
    A `logging.Logger` extension that overrides the `logging.Logger._log` method
    the underlies all "log methods" (`logging.Logger.debug`,
    `logging.Logger.info`, etc) to treat the double-splat keyword arguments
    as a map of names to values to be logged.

    This map is added as `"data"` to the `extra` mapping that is part of the
    log method API, where it eventually is assigned as a `data` attribute
    on the emitted `logging.LogRecord`.

    This allows logging invocations like:

        logger.debug(
            "Check this out!",
            x="hey,
            y="ho",
            z={"lets": "go"},
        )

    which I (obviously) like much better.
    """

    def process(self, msg, kwargs):
        new_kwargs, data = partition_mapping(
            kwargs, {"exc_info", "extra", "stack_info", "stacklevel"}
        )
        if extra := new_kwargs.get("extra"):
            extra["_splatlog_"] = True
            extra["data"] = data
        else:
            new_kwargs["extra"] = {"_splatlog_": True, "data": data}
            # new_kwargs["extra"] = {"data": data}
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
    def level(self) -> LevelValue:
        return self.logger.level

    def setLevel(self, level: Level) -> None:
        super().setLevel(to_level_value(level))

    def getChild(self, suffix):
        if self.logger.root is not self.logger:
            suffix = ".".join((self.logger.name, suffix))
        return get_logger(suffix)

    def inject(self, fn):
        @wraps(fn)
        def log_inject_wrapper(*args, **kwds):
            if "log" in kwds:
                return fn(*args, **kwds)
            else:
                return fn(*args, log=self.getChild(fn.__name__), **kwds)

        return log_inject_wrapper


class ClassLogger(SplatLogger):
    """
    `ClassLogger` is an extension of `SplatLogger` (and hence a
    `logging.LoggerAdapter`) that adapts the `logging.Logger` for the module the
    class is defined in and adds the qualified name of the class to
    `logging.LogRecord` that it processes as a `class_name` attribute.
    """

    _class_name: str

    def __init__(self, cls: type[object]):
        super().__init__(logging.getLogger(cls.__module__))
        self._class_name = cls.__qualname__

    @property
    def class_name(self) -> str:
        return self._class_name

    def process(self, msg, kwargs):
        msg, new_kwargs = super().process(msg, kwargs)
        new_kwargs["extra"]["class_name"] = self._class_name
        return msg, new_kwargs


class SelfLogger(ClassLogger):
    """
    `SelfLogger` is an extension of `ClassLogger`, where for an object `obj`:

    1.  The type of `obj` is used to initialize `ClassLogger`. Hence
        processed `logging.LogRecord` will have

        ```python
        record.class_name = obj.__class__.__qualname__
        ```

    2.  A `self` attribute is added to processed `logging.LogRecord` to
        identify `obj` itself as the record source. See `SelfLogger` for
        details on how to hook into that.

    If `obj` has an attribute named `_splatlog_self_` then the value of
    that attribute is used as `record.self`.

    If the attribute value is a `typing.Callable` then it will be called
    (with no arguments) **_each and every time_** that a record is
    processed by the `SelfLogger` to get the value for `record.self`.

    This allows for _dynamic identity_, but between performance overhead
    and possible confusion you probably shouldn't use it unless you've
    thoroughly thought it through.

    If no `_splatlog_self_` attribute is present on `obj` then a hex
    representation of it's unique object `id` will be used:

    ```python
    hex(id(obj))
    ```
    """

    get_identity: Callable[[], object]

    def __init__(self, obj: object):
        super().__init__(obj.__class__)

        self.set_identity(getattr(obj, "_splatlog_self_", hex(id(obj))))

    def set_identity(self, identity):
        if isinstance(identity, Callable):
            self.get_identity = identity
        else:
            self.get_identity = lambda: identity

    def process(self, msg, kwargs):
        msg, new_kwargs = super().process(msg, kwargs)
        new_kwargs["extra"]["self"] = self.get_identity()
        return msg, new_kwargs
