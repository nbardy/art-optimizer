from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _RenderJob:
    job_id: str
    factory: Callable[[], Awaitable[Any]]
    future: asyncio.Future[Any]


class RenderJobQueue:
    """Bounded FIFO render queue with explicit worker ownership.

    Candidate workers may still be represented by tasks in the session runtime,
    but expensive renderer entry is serialized through this queue. Cancelling a
    queued caller cancels its future; stale in-flight renders are discarded by
    the service's round/version checks.
    """

    def __init__(self, *, workers: int = 1, max_pending: int = 64) -> None:
        if workers < 1:
            raise ValueError("workers must be positive")
        if max_pending < workers:
            raise ValueError("max_pending must be at least the worker count")
        self.workers = workers
        self.max_pending = max_pending
        self._queue: asyncio.Queue[_RenderJob | None] = asyncio.Queue(maxsize=max_pending)
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._start_lock = asyncio.Lock()
        self._closed = False

    async def submit(
        self,
        job_id: str,
        factory: Callable[[], Awaitable[T]],
    ) -> T:
        if self._closed:
            raise RuntimeError("render queue is closed")
        await self._ensure_started()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[T] = loop.create_future()
        job = _RenderJob(job_id=job_id, factory=factory, future=future)
        await self._queue.put(job)
        try:
            return await future
        except asyncio.CancelledError:
            future.cancel()
            raise

    async def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        tasks = list(self._worker_tasks)
        for _ in tasks:
            await self._queue.put(None)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._worker_tasks.clear()
        while not self._queue.empty():
            queued = self._queue.get_nowait()
            self._queue.task_done()
            if queued is not None and not queued.future.done():
                queued.future.cancel()

    async def _ensure_started(self) -> None:
        if self._worker_tasks:
            return
        async with self._start_lock:
            if self._worker_tasks:
                return
            if self._closed:
                raise RuntimeError("render queue is closed")
            self._worker_tasks = [
                asyncio.create_task(self._worker(index), name=f"render-worker-{index}")
                for index in range(self.workers)
            ]

    async def _worker(self, _index: int) -> None:
        while True:
            job = await self._queue.get()
            try:
                if job is None:
                    return
                if job.future.cancelled():
                    continue
                try:
                    result = await job.factory()
                except asyncio.CancelledError:
                    if not job.future.done():
                        job.future.cancel()
                    raise
                except Exception as error:
                    if not job.future.done():
                        job.future.set_exception(error)
                else:
                    if not job.future.done():
                        job.future.set_result(result)
            finally:
                self._queue.task_done()
