"""Defines `SplatLogger` class."""

from __future__ import annotations
import logging
from typing import (
    Any,
    Optional,
    Mapping,
)
from functools import wraps
from threading import RLock
from contextlib import contextmanager

from splatlog.rich_handler import RichHandler
from splatlog.typings import ModuleType


class SplatLogger(logging.getLoggerClass()):
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

    _console_handler: Optional[RichHandler] = None
    _console_handler_lock: RLock
    _is_root: bool = False
    _module_role: Optional[ModuleType] = None

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self._console_handler_lock = RLock()

    def _log(
        self: SplatLogger,
        level: int,
        msg: Any,
        args,
        exc_info=None,
        extra: Optional[Mapping] = None,
        stack_info=False,
        **data,
    ) -> None:
        """
        Override to treat double-splat as a `"data"` extra.

        See `SplatLogger` doc for details.
        """

        if extra is not None:
            # This will fail if you give a non-`None` value that is not a
            # `Mapping` as `extra`, but it would have failed in
            # `logging.Logger.makeRecord` in that case anyways, so might as well
            # blow up here and save a cycle or two.
            extra = {"data": data, **extra}
        else:
            extra = {"data": data}

        super()._log(
            level,
            msg,
            args,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra,
        )

    def inject(self, fn):
        @wraps(fn)
        def log_inject_wrapper(*args, **kwds):
            if "log" in kwds:
                return fn(*args, **kwds)
            else:
                return fn(*args, log=self.getChild(fn.__name__), **kwds)

        return log_inject_wrapper

    @contextmanager
    def exclusive_console_handler(self):
        with self._console_handler_lock:
            yield self._console_handler

    def removeHandler(self, hdlr: logging.Handler) -> None:
        """
        Overridden to clear `SplatLogger.console_handler` if that is the handler
        that is removed.
        """
        with self.exclusive_console_handler() as current_handler:
            super().removeHandler(hdlr)
            if hdlr is current_handler:
                self._console_handler = None

    def get_console_handler(self) -> Optional[RichHandler]:
        return self._console_handler

    def set_console_handler(self, handler: logging.Handler) -> None:
        with self.exclusive_console_handler() as current_handler:
            if current_handler is not None:
                super().removeHandler(current_handler)
            self.addHandler(handler)
            self._console_handler = handler

    def del_console_handler(self) -> None:
        with self.exclusive_console_handler() as current_handler:
            if current_handler is not None:
                super().removeHandler(current_handler)
                self._console_handler = None

    console_handler = property(
        get_console_handler, set_console_handler, del_console_handler
    )
