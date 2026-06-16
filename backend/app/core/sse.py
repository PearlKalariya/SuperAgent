import json
from collections.abc import AsyncIterator

from app.models.streaming import StreamEvent


def encode_sse(event: StreamEvent) -> str:
    payload = event.model_dump(mode="json")
    return f"event: {event.type}\ndata: {json.dumps(payload)}\n\n"


async def as_sse(events: AsyncIterator[StreamEvent]) -> AsyncIterator[str]:
    async for event in events:
        yield encode_sse(event)
