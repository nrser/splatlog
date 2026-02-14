Formatting Type Hints
==============================================================================

> 📝 NOTE
> 
> You can verify these example using [doctest][] with a command similar to
> 
>       python -m doctest -v -o NORMALIZE_WHITESPACE -o ELLIPSIS <file>
> 
> [doctest]: https://docs.python.org/3.10/library/doctest.html
> 
> Note that `splatlog` and it's dependencies must be available to Python. If 
> you've checked out the repository just stick `poetry run` in front of the
> command and it should work.
> 

Prelude
------------------------------------------------------------------------------

Before anything we need to import `splatlog.lib.text.fmt_type_hint`, as well as
the standard library modules that we'll use in the examples.

```python
>>> from typing import *
>>> import types
>>> from collections import abc

>>> from splatlog.lib.text import fmt_type_hint

```

`typing.Union` and `typing.Literal`
------------------------------------------------------------------------------

Unions and literals both have their formatted members joined with `|`
characters.

```python
>>> fmt_type_hint(Union[int, str])
'int | str'

>>> fmt_type_hint(Literal["a", "b"])
"'a' | 'b'"

>>> fmt_type_hint(Union[abc.Mapping, abc.Sequence])
'collections.abc.Mapping | collections.abc.Sequence'

>>> fmt_type_hint(Union[abc.Mapping, abc.Sequence], module_names=False)
'Mapping | Sequence'

```

We even smush union and literal combinations together, as they mean about the 
same thing and the differences in member formatting seem clear enough to tell
what's going on.

```python
>>> fmt_type_hint(Union[int, str, Literal["a", "b"]])
"int | str | 'a' | 'b'"

```

`typing.Optional`
------------------------------------------------------------------------------

Optional types (which are really 2-arg `typing.Union` where one arg is
`types.NoneType`) are formatting the type arg that is _not_ none and appending a
`?` character.

```python
>>> fmt_type_hint(Optional[int])
'int?'

>>> fmt_type_hint(Union[None, int])
'int?'

>>> fmt_type_hint(Optional[Literal["a", "b"]])
"None | 'a' | 'b'"

```

`Callable`
------------------------------------------------------------------------------

Simple example.

```python
>>> fmt_type_hint(Callable[[int, int], float])
'(int, int) -> float'

```

Return types are _not_ considered _nested_ (they are _not_ wrapped in
parenthesis when they contain multiple tokens without start and end delimiters).

```python
>>> fmt_type_hint(Callable[[int, int], Union[int, float]])
'(int, int) -> int | float'

```

However, callables themselves will be paren-wrapped when nested, such as in
unions. I feel like this makes it easier to pick the callables out as coherent
terms.

```python
>>> fmt_type_hint(
...     Union[
...         Callable[[int, int], Union[int, float]],
...         Callable[[float, float], Union[int, float]],
...     ]
... )
'((int, int) -> int | float) | ((float, float) -> int | float)'

```

[PEP 585][] — Type Hinting Generics In Standard Collections
------------------------------------------------------------------------------

Using the standard collections as type hints, which I _think_ is what we're
_supposed_ to be doing going forward? Even though it has some screwiness (as of
2022-09-27, Python 3.10). As if Python type hints needed more screwiness, right?

[PEP 585]: https://peps.python.org/pep-0585/

### Dictionaries ###

```python
>>> fmt_type_hint(dict[str, list])
'{str: list}'

>>> fmt_type_hint(dict[str, list[int]])
'{str: int[]}'

>>> fmt_type_hint(dict[str, Optional[int]])
'{str: int?}'

```

### Tuples ###

```python

>>> fmt_type_hint(tuple[int, int])
'(int, int)'

>>> fmt_type_hint(tuple[str, ...])
'(str, ...)'

```

### Sets ###

```python
>>> fmt_type_hint(set[str])
'{str}'

```

### Lists ###

```python
>>> fmt_type_hint(list[int])
'int[]'

>>> T = TypeVar("T")
>>> fmt_type_hint(list[T])
'~T[]'

```

### Callables ###

```python
>>> fmt_type_hint(abc.Callable[[int, int], float])
'(int, int) -> float'

```

### Screwiness ###

You _can_ give more args than makes sense using standard collections as type
hints (try it using `typing.Dict` and it will barf). Type checkers should barf
on it too:

https://mypy-play.net/?mypy=latest&python=3.10&gist=d4ba8ac1d3c3e85de35b32ed6679c6e9

We simply ignore the extra args.

```python
>>> fmt_type_hint(set[int, str])
'{int}'

>>> fmt_type_hint(dict[str, int, float])
'{str: int}'

```
