"""Cooperative cancellation scoped to one dashboard worker and its async tasks."""
from contextlib import contextmanager
from contextvars import ContextVar

_event = ContextVar('operation_cancellation', default=None)


class OperationCancelled(BaseException):
    """Bypass workflow retry handlers while allowing finally blocks to clean up."""


def check_cancelled():
    event = _event.get()
    if event is not None and event.is_set():
        raise OperationCancelled('Stopped at your request. Saved checkpoints retained.')


@contextmanager
def cancellation_scope(event):
    token = _event.set(event)
    try:
        check_cancelled()
        yield
    finally:
        _event.reset(token)


async def cancellable(coroutine):
    """Cancel a crawler task promptly and await its resource cleanup."""
    import asyncio
    task = asyncio.ensure_future(coroutine)
    try:
        while not task.done():
            check_cancelled()
            await asyncio.wait({task}, timeout=0.2)
        check_cancelled()
        return await task
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
