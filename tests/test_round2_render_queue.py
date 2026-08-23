from __future__ import annotations

import asyncio

from art_optimizer.round2.render_queue import RenderJobQueue


async def exercise_render_queue() -> None:
    queue = RenderJobQueue(workers=1, max_pending=8)
    active = 0
    peak = 0
    started: list[int] = []

    async def render(index: int) -> int:
        nonlocal active, peak
        started.append(index)
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.005)
        active -= 1
        return index

    try:
        results = await asyncio.gather(
            *[
                queue.submit(
                    f"job_{index}",
                    lambda index=index: render(index),
                )
                for index in range(5)
            ]
        )
    finally:
        await queue.shutdown()

    assert results == [0, 1, 2, 3, 4]
    assert started == [0, 1, 2, 3, 4]
    assert peak == 1


def test_render_queue_bounds_concurrency_and_preserves_fifo() -> None:
    asyncio.run(exercise_render_queue())
