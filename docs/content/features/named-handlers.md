Named Handlers
==============================================================================

Overview
------------------------------------------------------------------------------

Splatlog has an idea of _named handlers_ which:

1.  Have a unique, non-empty `name` (type `str`).
    
2.  Allow get, set and delete by `name`, like a global version of a `property`.
    
3.  Have an associated `cast` function that creates instances from simple and
    convenient values (type `(object) -> None | logging.Handler`).
    
    For instance, a `cast` function might accept a `typing.IO` and
    return a handler that writes to that I/O stream.

There are two built-in _named handlers_:

1.  _console_ — For logging to STDIO. Defaults to using
    `splatlog.rich_handler.RichHandler` to produce nice, tabular output.
    Intended for people to read.
    
2.  _export_ — For exporting logs in machine readable format for another system
    to consume. The `cast` function helps writing JSON to files and streams
    using the [splatlog.json](/splatlog/json) functionality.

You can easily add your own _named handlers_ as well.

The motivation is:

1.  Encode best practices for configuring handlers for common purposes (I want
    to log to the console, I want to log to a file, etc.).
    
2.  Make handlers easy to access, inspect and replace. 


Usage
------------------------------------------------------------------------------

### Console Handler ###

Say you simply want to log to the console. You can do this:

```python
>>> import splatlog

>>> splatlog.setup(console=True)

```

That creates a `splatlog.rich_handler.RichHandler` logging to
`sys.stderr` and adds it to the root logger. Check it out:

```python
>>> import logging
>>> import sys

>>> console_handler = splatlog.get_named_handler("console")

>>> console_handler in logging.getLogger().handlers
True

>>> console_handler.console.file is sys.stderr
True

```

Since `doctest` doesn't capture STDERR, let's log to STDOUT instead.

```python
>>> splatlog.set_named_handler("console", sys.stdout)

>>> log = splatlog.getLogger(__name__)
>>> log.warning("Now we're talking!")
WARNING   __main__
msg       Now we're talking!

```

Notice that the first handler we created is no logger attached, but our new
STDOUT one is. _Named handlers_ takes care of all this for ya.

```python
>>> console_handler in logging.getLogger().handlers
False

>>> new_console_handler = splatlog.get_named_handler("console")

>>> new_console_handler in logging.getLogger().handlers
True

>>> new_console_handler.console.file is sys.stdout
True

```

You can remove the handler, setting it back to `None` like:

```python
>>> splatlog.set_named_handler("console", None)

```

### Export Handler ###

Suppose you'd like to dump all your logs to a file or stream for processing by
an external system. In this example we use a temporary directory for testing
purposes, and a "pretty" JSON formatting to make the output easier for us humans
to read, but the approach is applicable in general.

First, just some imports and file preperation.

```python
>>> from tempfile import TemporaryDirectory

>>> tmp = TemporaryDirectory()
>>> filename = f"{tmp.name}/log.json"

```

Now we setup Splatlog, setting the level to _DEBUG_ so we get all the logs, and
configuring an _export_ handler to write to our temporary file using the
"pretty" formatting.

```python
>>> splatlog.setup(
...     level=splatlog.DEBUG,
...     export=dict(filename=filename, formatter="pretty")
... )

```

Now let's emit some logs and check out the file contents!

```python
>>> log = splatlog.getLogger(__name__)
>>> log.info("File style!")
>>> log.debug("Some values", x=1, y=22)

>>> with open(filename, "r") as file:
...     print(file.read())
{
    "t": ...,
    "level": "INFO",
    "name": "__main__",
    "file": "<doctest named-handlers.md[...]>",
    "line": 1,
    "msg": "File style!"
}
{
    "t": ...,
    "level": "DEBUG",
    "name": "__main__",
    "file": "<doctest named-handlers.md[...]>",
    "line": 1,
    "msg": "Some values",
    "data": {
        "x": 1,
        "y": 22
    }
}

```

Seems to work pretty well. You can of course setup both _console_ and _export_
handlers; the [verbosity feature](/features/verbosity) page has a nice example
using the _verbosity_ system to control log levels in a useful way.

### Custom Handlers ###

You can add your own _named handlers_, and {@pylink splatlog.setup} will treat
them the same as _console_ and _export_.

I don't have any great ideas at the moment regarding what would make sense to
add, but the whole feature came about from wanting the _export_ handler, so it
doesn't seem too crazy to think that something else may make sense given some
use case at some point.

The following example creates a "basic" handler that is like the ones
{@pylink logging.basicConfig} sets up but handles the "splat" of data when it's present.

First, some imports we'll need.

```python
>>> from typing import Optional
>>> import io
>>> from collections.abc import Mapping

```

Here we create the "splat" version of basic `logging` formatting (the default
formatting when you use `logging.basicConfig`). When a `splatlog.SplatLogger` is
used to log, the record will have a `data` dictionary attached as an attribute.
If regular `logging.Logger` is used, `data` won't be there.

So, what we do is create a subclass of {@pylink logging.Formatter} that creates
an additional `_splat_style` that appends `" %(data)s"` to the format string.
Then we override {@pylink logging.Formatter.FormatMessage} to switch styles when
the `data` attribute is present (and not empty).

Since this is simply to serve as an example, the "style type" is fixed to `"%"`,
which coresponds to `logging.PercentStyle`.

```python
>>> class SplatFormatter(logging.Formatter):
...     def __init__(
...         self,
...         fmt=logging.BASIC_FORMAT,
...         datefmt=None,
...         validate=True,
...         *,
...         defaults=None,
...         splat_fmt="%(data)r",
...     ):
...         super().__init__(fmt, datefmt, "%", validate, defaults=defaults)
...         self._splat_style = logging.PercentStyle(
...             fmt + " " + splat_fmt,
...             defaults=defaults
...         )
...         if validate:
...             self._splat_style.validate()
...     
...     def formatMessage(self, record: logging.LogRecord):
...         if getattr(record, "data", None):
...             return self._splat_style.format(record)
...         return super().formatMessage(record)

```

Now we register the `basic` _named handler_, which you can do with a decorator
around the _cast_ function. You can do all sorts of fancy things in the cast 
function if you like, but our example is minimal:

1.  It maps `None` and `False` to `None`, which means "no handler".
2.  It maps "text I/O" objects to a {@pylink logging.StreamHandler} using our
    `SplatFormatter` that write to that I/O.
3.  It raises on anything else.

> 📝 NOTE
> 
> By convention, _cast_ functions map both `None` and `False` to `None`, which
> results in the named handler being set to `None`. The reason for this is that
> {@pylink splatlog.setup} considers `None` to be a "not provided" value with
> regard to named handlers and ignores it when it sees it. On the other hand
> `False` will be passed through to the _cast_ function, resulting in the named
> handled being set to `None`.

```python
>>> @splatlog.named_handler("basic")
... def cast_basic_handler(value: object) -> Optional[logging.Handler]:
...     if value is None or value is False:
...         return None
...     if isinstance(value, io.TextIOBase):
...         handler = logging.StreamHandler(stream=value)
...         handler.setFormatter(SplatFormatter())
...         return handler
...     raise TypeError("bad value")

```

Next we create a {@pylink io.StringIO} instance to write to and call {@pylink
splatlog.setup}:

1.  Setting to root log level to {@pylink logging.INFO}.
2.  Unsetting any `console` and `export` handlers we may have added above.
3.  Sending our {@pylink io.StringIO} to be cast to a "basic" handler.

```python
>>> stream = io.StringIO()
>>> splatlog.setup(
...     level=logging.INFO,
...     console=False,
...     export=False,
...     basic=stream,
... )

```

Let's test out a "splat" logging with attached `data`.

```python
>>> log = splatlog.getLogger(__name__)
>>> log.info("Howdy", a="aye!", b="bee")
>>> print(stream.getvalue())
INFO:__main__:Howdy {'a': 'aye!', 'b': 'bee'}

```

And also a "stdlib" logging.

```python
>>> builtin_log = logging.getLogger(__name__)
>>> builtin_log.info("Doody")
>>> print(stream.getvalue())
INFO:__main__:Howdy {'a': 'aye!', 'b': 'bee'}
INFO:__main__:Doody

```

Both of which succeed in the expected manner.
