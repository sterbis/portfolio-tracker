import asyncio
from typing import AsyncGenerator, Generator, TypeVar

TItem = TypeVar("TItem")


async def as_async_generator(
    sync_generator: Generator[TItem, None, None],
) -> AsyncGenerator[TItem, None]:
    for item in sync_generator:
        yield item
        await asyncio.sleep(0)
