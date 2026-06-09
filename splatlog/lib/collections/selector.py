from collections.abc import Callable, Mapping
import dataclasses as dc
import sys
from typing import Protocol, overload

if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs


class Selector(Protocol):
    def __call__(self, value: object) -> bool: ...


@dc.dataclass(frozen=True)
class IsA[T](Selector):
    t: type[T]

    def __call__(self, value: object) -> TypeIs[T]:
        return isinstance(value, self.t)


@dc.dataclass(frozen=True)
class HasFields(Selector):
    fields: Mapping[str, Selector]

    def __call__(self, value: object) -> bool:
        for name, selector in self.fields.items():
            if isinstance(value, Mapping):
                if not (name in value and selector(value[name])):
                    return False
            else:
                if not (
                    hasattr(value, name) and selector(getattr(value, name))
                ):
                    return False
        return True


@dc.dataclass(frozen=True)
class IsEqual[T](Selector):
    to: T

    def __call__(self, value: object) -> TypeIs[T]:
        return value == self.to


@dc.dataclass(frozen=True)
class Predicate(Selector):
    fn: Callable[[object], bool]

    def __call__(self, value: object) -> bool:
        return self.fn(value)


@overload
def where[T](cls: type[T]) -> IsA[T]: ...


@overload
def where(**fields) -> HasFields: ...


@overload
def where(predicate: Callable[[object], bool]) -> Predicate: ...


@overload
def where[T](value: T) -> IsEqual[T]: ...


def where(*args, **kwds):
    match (args, kwds):
        case ((type() as t,), {}):
            return IsA(t)

        case ((), fields):
            return HasFields({
                name: where(field) for name, field in fields.items()
            })

        case ((fn,), {}) if isinstance(fn, Callable):
            return Predicate(fn=fn)

        case ((value,), {}):
            return IsEqual(to=value)

        case other:
            raise Exception(f"Can't convert to a selector: {other!r}")
