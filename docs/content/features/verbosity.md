Verbosity
==============================================================================

Splatlog has a _verbosity_ system that allows you to configure which loggers
are set to which level as you twist the knob on a single _verbosity_ parameter.

Verbosity Values (`splatlog.typing.Verbosity`)
------------------------------------------------------------------------------

-   A _verbosity_ is an `int`.
-   It can _not_ be negative.
-   It must be _less_ than `sys.maxint`.
-   In practice it usually ranges from `0` to `4`-or-so.
-   The higher the verbosity, the more logging you see.

You can test if a value is a verbosity with `splatlog.typings.isVerbosity` and
cast to a verbosity with `splatlog.typings.asVerbosity`. See documentation for
those function for examples.

Verbosity is directly inspired by the `-v`, `-vv`, `-vvv`, ... pattern of option
flags common in command line interfaces on unix-like systems.

Verbosity Levels
------------------------------------------------------------------------------

To use verbosity, you provide a _verbosity levels_ mapping.

-   Each key is a logger name (type `str`).
-   The coresponding value is a sequence of `tuple` pairs.
    -   The first element is a _verbosity_, as discussed above.
    -   The second element is the log level to take effect at that verbosity.

To apply verbosity levels globally, pass a mapping to `splatlog.setup`.

Here we apply verbosity levels to an example logger named `verbosity-feature`.

1.  Setting verbosity to `0` or `1` will set the `verbosity-feature` logger's 
    level to `WARNING`.
2.  Setting verbosity to `2` will set the logger's level to `INFO`.
3.  Setting verbosity to `3` or more will set the logger's level to `DEBUG`.

```python
>>> import splatlog

>>> splatlog.del_verbosity_levels()
>>> splatlog.del_verbosity()

>>> splatlog.setup(
...     console="stdout",
...     verbosity_levels={
...         "verbosity-feature": (
...             (0, splatlog.WARNING),
...             (2, splatlog.INFO),
...             (3, splatlog.DEBUG),
...         ),
...     },
... )

```

We can verify this behavior by getting the logger and changing the _verbosity_.

```python
>>> log = splatlog.get_logger(name="verbosity-feature")

>>> log.level is splatlog.NOTSET
True

>>> splatlog.set_verbosity(0)
>>> log.level is splatlog.WARNING
True

>>> splatlog.set_verbosity(1)
>>> log.level is splatlog.WARNING
True

>>> splatlog.set_verbosity(2)
>>> log.level is splatlog.INFO
True

>>> splatlog.set_verbosity(3)
>>> log.level is splatlog.DEBUG
True

>>> splatlog.set_verbosity(4)
>>> log.level is splatlog.DEBUG
True

```

Handler-Specific Verbosity Levels
------------------------------------------------------------------------------

Global verbosity levels are convenient if you only have a single handler or want
to control the level of logging reaching all handlers, but there are use cases
where handlers have significantly different purposes and need their levels
specifically controlled.

The primary example is logging important information to stdio for people to look
at and logging a more comprehensive set of records to a file or stream for a log
management system to ingest.

To support this use case, verbosity levels can be assigned to specific logging
handlers instead of the loggers themselves.

In this example, we will log everything from `verbosity-feature` to a JSON
stream, and control what goes to stdout with verbosity.

First, we need to quickly reset the verbosity and verbosity levels.

```python
>>> splatlog.del_verbosity_levels()
>>> splatlog.del_verbosity()

```

Now we create a JSON handler to receive records. For testing purposes this will
simply write to an `io.StringIO` instance. We'll also use the `pretty`
configuration to make the output easier to read.

```python
>>> import logging
>>> from io import StringIO

>>> json_io = StringIO()

```

Here is the setup:

-   The root log level is `DEBUG` in order to allow all records through to our
    JSON handler, which is assigned as the `export` handler.
-   The `console` handler writes to stdout (doctest doesn't capture stderr!) and
    has the same verbosity levels configuration as the previous section.
-   Verbosity is set to `0` to start.

```python
>>> splatlog.setup(
...     level=splatlog.DEBUG,
...     export=dict(
...         stream=json_io,
...         level=splatlog.DEBUG,
...         formatter="pretty"
...     ),
...     console=dict(
...         console="stdout",
...         verbosity_levels={
...             "verbosity-feature": (
...                 (0, splatlog.WARNING),
...                 (2, splatlog.INFO),
...                 (3, splatlog.DEBUG),
...             ),
...         },
...     ),
...     verbosity=0,
... )

```

Let's quickly confirm the setup did what we expect:

```python
>>> splatlog.get_verbosity() == 0
True

>>> log.getEffectiveLevel() is splatlog.DEBUG
True

>>> splatlog.get_named_handler("console").verbosity_levels[log.name].get_level(
...     splatlog.get_verbosity(),
... ) == splatlog.WARNING
True

```

When logging a `WARNING` we will see it both in stdout and the JSON stream.

```python
>>> log.warning("Watch out now!")
    WARNING     verbosity-feature
    msg         Watch out now!

>>> print(json_io.getvalue())
{
    "t": ...,
    "level": "WARNING",
    "name": "verbosity-feature",
    "file": "<doctest verbosity.md[...]>",
    "line": 1,
    "msg": "Watch out now!"
}

```

However, when logging a `DEBUG` message, it will only appear in the JSON stream.

```python
>>> log.debug("Won't show in stdout, because verbosity's too low!")

>>> print(json_io.getvalue())
{
    "t": ...,
    "level": "WARNING",
    "name": "verbosity-feature",
    "file": "<doctest verbosity.md[...]>",
    "line": 1,
    "msg": "Watch out now!"
}
{
    "t": ...,
    "level": "DEBUG",
    "name": "verbosity-feature",
    "file": "<doctest verbosity.md[...]>",
    "line": 1,
    "msg": "Won't show in stdout, because verbosity's too low!"
}

```

Now we turn up the verbosity to see a `DEBUG` message appear in both.

```python
>>> splatlog.set_verbosity(3)

>>> log.debug(
...     "Ok, now we should see it in stdout",
...     verbosity=splatlog.get_verbosity(),
... )
DEBUG       verbosity-feature
msg         Ok, now we should see it in stdout
data        verbosity         int     3

>>> print(json_io.getvalue())
{
    "t": ...,
    "level": "WARNING",
    "name": "verbosity-feature",
    "file": "<doctest verbosity.md[...]>",
    "line": 1,
    "msg": "Watch out now!"
}
{
    "t": ...,
    "level": "DEBUG",
    "name": "verbosity-feature",
    "file": "<doctest verbosity.md[...]>",
    "line": 1,
    "msg": "Won't show in stdout, because verbosity's too low!"
}
{
    "t": ...,
    "level": "DEBUG",
    "name": "verbosity-feature",
    "file": "<doctest verbosity.md[...]>",
    "line": 1,
    "msg": "Ok, now we should see it in stdout",
    "data": {
        "verbosity": 3
    }
}

```
