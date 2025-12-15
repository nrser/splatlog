splatlog.rich.formatter
==============================================================================

@pyscope splatlog.rich.formatter.rich_formatter
@pyscope splatlog.rich.formatter.rich_repr
@pyscope splatlog.rich.formatter.rich_text


Examples
------------------------------------------------------------------------------

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


### Prelude ###

Before anything we need to import `RichFormatter`, as well as the standard
library modules that we'll use in the examples.

```python
>>> from typing import *
>>> from dataclasses import dataclass

>>> import rich
>>> from rich.text import Text

>>> from splatlog.rich.formatter import RichFormatter

```


### General Use ###

`RichFormatter` instances combine literal text and interpolated objects into
`rich.text.Text` instances.

The default field formatting looks for a `__rich_text__` method on values and,
if found, invokes it to produce a `rich.text.Text` instance to interpolate. If
`__rich_text__` is not implemented, it falls back to `repr` formatting with
syntax highlighting.

Let's take a look at a _dataclass_, where the `dataclasses.dataclass` decorator
has generated a nice `__repr__` implementation for us.

> You won't be able to see the highlight coloring here because it's
> automatically stripped when writing to `sys.stdout` in the `doctest` (and it
> seems like it would be quite a pain to test for the control codes in the
> test), so you'll have to just trust us it will appear in normal use.

```python
>>> formatter = RichFormatter()

>>> @dataclass
... class Point:
...     x: float
...     y: float

>>> point = Point(x=1.23, y=4.56)
>>> text = formatter.format("The point is: {}, cool huh?", point)
>>> isinstance(text, Text)
True
>>> rich.print(text)
The point is: Point(x=1.23, y=4.56), cool huh?

```

> 📝 NOTE
> 
> Dataclasses are used in many of these examples simply due to their concise
> definitions. Unless otherwise mentioned the same approach applies to "normal"
> classes as well.


### Conversions ###

As of writing (2022-12-23, Python 3.10), `string.Formatter` defines three
_conversions_, invoked by a formate string suffix of `!` followed by the
conversion character:

1.  `!r` — `repr` conversion.
2.  `!s` — `str` conversion.
3.  `!a` — `ascii` conversion.

All are supported, plus one addition:

1.  `!t` — text conversion.

You can also overriding or provide additional conversions via the `conversions`
argument to the `RichFormatter` constructor.

The default conversions implementations are described below.


@anchor splatlog:lib:rich:formatter:repr_conversion
    :with{ text = "Repr Conversion" }

#### `!r` — Repr Conversion ####

Uses the {@link splatlog:lib:rich:formatter:rich_repr_protocol} if the value
supports it. Otherwise calls `repr` on the value and highlights the result with
`rich.highlighter.ReprHighlighter`.

```python
>>> rich.print(formatter.format("The point is: {!r}, cool huh?", point))
The point is: Point(x=1.23, y=4.56), cool huh?

```


#### `!s` — String Conversion ####

The `!s` conversion calls `str` on the interpolation value and wraps the result
in a `rich.text.Text`, without applying any highlighting.

To demonstrate, we define a class with a custom `__str__` implementation.

```python
>>> class SomeClass:
...     name: str
...     
...     def __init__(self, name: str):
...         self.name = name
...     
...     def __str__(self) -> str:
...         return f"{self.__class__.__name__} named '{self.name}'"

>>> rich.print(
...     formatter.format("We got {!s} over here!", SomeClass(name="Classy Class"))
... )
We got SomeClass named 'Classy Class' over here!

```


#### `!a` — `ascii` Conversion ####

Simply runs `ascii` on the value and highlights the result with
`rich.highlighter.ReprHighlighter`.

```python
>>> @dataclass
... class UnicodeNamed:
...     name: str
    
>>> rich.print(
...     formatter.format(
...         "Lookin' at {!a} in ascii.", UnicodeNamed(name="λ")
...     )
... )
Lookin' at UnicodeNamed(name='\u03bb') in ascii.

```


#### `!t` — Text Conversion ####

Uses the {@link splatlog:lib:rich:formatter:rich_text_protocol} if the value
supports it, otherwise falls back to
{@link splatlog:lib:rich:formatter:repr_conversion}.


#### Custom Conversions ####

For no really good reason, you can add or override conversions in the
`RichFormatter` constructor.

Conversions take the type `RichFormatterConverter`, which has form

    (typing.Any) -> rich.text.Text
    
and you need to provide a mapping of `str` to converter, which is merged over
the standard conversions, allowing you to override them if you really want.

```python
>>> weird_formatter = RichFormatter(
...     conversions=dict(
...         m=lambda v: Text.from_markup(str(v)),
...     ),
... )

>>> @dataclass
... class Smiles:
...     name: str
...     
...     def __str__(self) -> str:
...         return f":smile: {self.name} :smile:"

>>> rich.print(
...     weird_formatter.format("Hello, my name is {!s}", Smiles(name="nrser"))
... )
Hello, my name is :smile: nrser :smile:

>>> rich.print(
...     weird_formatter.format("Hello, my name is {!m}", Smiles(name="nrser"))
... )
Hello, my name is 😄 nrser 😄

```


@anchor splatlog:lib:rich:formatter:rich_text_protocol
    :with{ text = "Rich Text Protocol" }

### `__rich_text__` — Rich Text Protocol ###

For full control of formatting classes can implement the `RichText` protocol,
which consists of defining a single method `__rich_text__` that takes no
arguments and returns a `rich.text.Text` instance.

```python
>>> @dataclass
... class CustomFormatted:
...     name: str
...     
...     def __rich_text__(self) -> Text:
...         return Text.from_markup(f":smile: {self.name} :smile:")

>>> custom_formatted = CustomFormatted(name="Hey yo!")
>>> rich.print(
...     formatter.format(
...         "Rendered with RichText protocol: {}. Pretty neat!",
...         custom_formatted
...     )
... )
Rendered with RichText protocol: 😄 Hey yo! 😄. Pretty neat!

```

`RichText` is a `typing.Protocol` that is `typing.runtime_checkable`, allowing
`isinstance` checks, should you have a use for them.

```python
>>> from splatlog.rich.formatter import RichText
>>> isinstance(custom_formatted, RichText)
True

```


@anchor splatlog:lib:rich:formatter:rich_repr_protocol
    :with{ text = "Rich Repr Protocol" }

### `__rich_repr__` — Rich Repr Protocol ###

The [Rich Repr Protocol][] is some-what supported... `RichFormatter` will
iterate over the fields provided by `__rich_repr__` and respect the omission of
those set to their default, but `RichFormatter` does not traverse into the child
attrbiutes (it simply does `repr` formatting and highlighting on them).

More could be done; a bit of a todo.

[Rich Repr Protocol]: https://rich.readthedocs.io/en/latest/pretty.html?highlight=__rich_repr__#rich-repr-protocol

```python
>>> from rich.repr import RichReprResult

>>> class RichRepred:
...     BEST_NAME = "nrser"
...     BEST_QUEST = "get rich"
...     BEST_COLOR = "blue"
...     
...     name: str
...     quest: str
...     fav_color: str
...
...     def __init__(
...         self,
...         name: str,
...         quest: str = BEST_QUEST,
...         fav_color: str = BEST_COLOR,
...     ):
...         self.name = name
...         self.quest = quest
...         self.fav_color = fav_color
...     
...     def __rich_repr__(self) -> RichReprResult:
...         yield "name", self.name
...         yield "quest", self.quest, self.BEST_QUEST
...         yield "fav_color", self.fav_color, self.BEST_COLOR

>>> using_defaults = RichRepred(name="Finn")

>>> rich.print(formatter.format("Got {} here!", using_defaults))
Got RichRepred(name='Finn') here!

>>> no_defaults = RichRepred(
...     name="Smokey",
...     quest="eat food",
...     fav_color="red",
... )

>>> rich.print(formatter.format("Got {} here!", no_defaults))
Got RichRepred(name='Smokey', quest='eat food', fav_color='red') here!

```


### Field Formatting ###

_Field formatting_ is some-what supported, though the effects have not been
thoroughly explored at this time (2022-12-27).

The general approach that seems to have emerged during development is:

1.  If no conversion or field format spec is provided then format the value
    with the text conversion (`!t`). This defaults to the `text_convert`
    function, which uses `__rich_text__` if available and falls back to 
    `repr_convert`.
    
    This the `RichFormatter` analog to how `string.Formatter` defaults to `str`
    conversion. The fallback to `repr_convert` is because repr formatting is
    generally a lot more interesting and useful in the "rich sense" than
    plain string formatting.

2.  You should be able to field-format `rich.text.Text` like it was a `str`.
    
    The same as `string.Formatter` allows you to convert to a `str` with 
    `!s` or `!r` then apply string formatting, like
    
    ```python
    >>> "{!r:<24}  {!r:>24}".format(Point(1, 2), Point(333, 444))
    'Point(x=1, y=2)                Point(x=333, y=444)'
    
    ```
    
    you should be able to do something similar with `RichFormatter`, even though
    it works with `rich.text.Text`:
    
    ```python
    >>> rich.print(
    ...     formatter.format(
    ...         "{!r:<24}  {!r:>24}", Point(1, 2), Point(333, 444)
    ...     )
    ... )
    Point(x=1, y=2)                Point(x=333, y=444)
    
    ```

    This is accomplished by applying the formatting to the
    `rich.text.Text.plain` representation (which is a `str`).

2.  Field format specs that work with `string.Formatter` should also work with
    `RichFormatter`.
    
    In essence, this means that if you provide a (non-empty) field format spec
    and an object whose `__format__` method knows what to do with it, it should
    produce the expected result.
    
    An example of this is `datetime.datetime` instances, which have a
    `__format__` method that understands a specific date/time format spec.
    
    ```python
    >>> from datetime import datetime

    >>> today = datetime(2022, 12, 27)

    >>> "Today is: {:%a %b %d %Y}".format(today)
    'Today is: Tue Dec 27 2022'

    >>> rich.print(formatter.format("Today is: {:%a %b %d %Y}", today))
    Today is: Tue Dec 27 2022

    ```
    
    > 📝 NOTE
    > 
    > This complicates things quite a bit, as `object` itself also provides a
    > `__format__` method, which we call the _trivial implementation_: if the
    > format spec is empty, it calls `str` on itself and returns the value.
    > Otherwise it raises a `TypeError`.
    > 
    > Considering the different ways an object can (loosely-speaking) "have a
    > method" — Python method, built-in method, descriptor that returns a
    > function, function slapped in `__dict__` or `__slots__`, etc. — and the
    > wonkyness of class and instance methods sharing the same namespace, it's
    > less than strait-forward to figure out what a `typing.Callable` attribute
    > is and where it came from, so we play it safe and invoke `__format__` on
    > the object when:
    > 
    > 1.  We were given a non-empty field format specification, and
    > 2.  the object is not a `rich.text.Text` (either provided that way or as
    >     the result of a conversion).
    > 
    > There is likely room to improve here in the future, but this seems tenable
    > for the initial implementation.


@pydoc splatlog.rich.formatter
