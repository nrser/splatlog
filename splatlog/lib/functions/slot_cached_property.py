"""
A cached property decorator compatible with `__slots__`.
"""

from __future__ import annotations
from threading import RLock
from typing import Callable, Generic, TypeVar, overload, Any


_NOT_FOUND = object()
"""
A unique {py:class}`object` instance used as a default value when getting an
attribute to tell if it's not found, as {py:data}`None` is a valid value.
"""


T = TypeVar("T")


class SlotCachedProperty(Generic[T]):
    """
    A cached property that works with classes using `__slots__`. Generic over
    the property's value type `T`.

    This is an adaptation of {py:func}`functools.cached_property` for slotted
    classes. The cached value is stored in a slot named with a leading
    underscore (e.g., property `blah` uses slot `_blah`).

    Thread-safe via {py:class}`threading.RLock`.

    ## Examples

    ```python
    >>> class Example:
    ...     __slots__ = ("_value",)
    ...     @SlotCachedProperty
    ...     def value(self) -> int:
    ...         print("Computing...")
    ...         return 42
    >>> ex = Example()
    >>> ex.value
    Computing...
    42
    >>> ex.value  # Cached, no "Computing..." printed
    42

    ```
    """

    def __init__(self, func: Callable[[Any], T]):
        """
        Create a cached property from a method.

        ## Parameters

        -   `func`: The method to wrap. Its return value will be cached.
        """
        self.func = func
        self.attrname: str | None = None
        self.__doc__ = func.__doc__
        self.lock = RLock()

    def __set_name__(self, owner: type, name: str) -> None:
        """
        Record the attribute name when the descriptor is assigned to a class.

        The slot name is derived by prepending an underscore to the property
        name.
        """
        attrname = "_" + name
        if self.attrname is None:
            self.attrname = attrname
        elif attrname != self.attrname:
            raise TypeError(
                f"Cannot assign the same {self.__class__.__name__} to two "
                f"different names ({self.attrname!r} and {attrname!r})"
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.func!r})"

    @overload
    def __get__(self, instance: None, owner: None) -> SlotCachedProperty[T]: ...

    @overload
    def __get__(self, instance: Any, owner: type) -> T: ...

    def __get__(self, instance, owner=None):
        """
        Get the cached value, computing it if necessary.

        When accessed on the class, returns the descriptor itself. When
        accessed on an instance, returns the cached value (computing and
        caching it on first access).
        """
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                f"Cannot use {self.__class__.__name__} instance without "
                "calling __set_name__ on it."
            )
        val = getattr(instance, self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            with self.lock:
                # check if another thread filled cache while we awaited lock
                val = getattr(instance, self.attrname, _NOT_FOUND)
                if val is _NOT_FOUND:
                    val = self.func(instance)
                    setattr(instance, self.attrname, val)
        return val
