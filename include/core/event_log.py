# -*- coding: utf-8 -*-
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator, Optional

EventSink = Callable[[str], None]

_event_sink: ContextVar[Optional[EventSink]] = ContextVar(
    "quanzhi_event_sink", default=None
)
_events_muted: ContextVar[bool] = ContextVar("quanzhi_events_muted", default=False)


def emit(*values, sep: str = " ", end: str = "\n", file=None, flush: bool = False):
    """Print-compatible domain event output with an optional sink."""
    if file is not None:
        print(*values, sep=sep, end=end, file=file, flush=flush)
        return

    message = sep.join(str(value) for value in values) + end
    if _events_muted.get():
        return

    sink = _event_sink.get()
    if sink is not None:
        sink(message)
        return

    print(message, end="", flush=flush)


@contextmanager
def event_sink(sink: EventSink) -> Iterator[None]:
    token = _event_sink.set(sink)
    try:
        yield
    finally:
        _event_sink.reset(token)


@contextmanager
def silence_events() -> Iterator[None]:
    token = _events_muted.set(True)
    try:
        yield
    finally:
        _events_muted.reset(token)
