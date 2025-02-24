# meta developer: @sunshinelzt

import random
import asyncio
from telethon.tl.types import MessageMediaDocument, DocumentAttributeVideo
from telethon.tl.functions.messages import GetHistoryRequest

from .. import loader


@loader.tds
class RandomCircleMod(loader.Module):
    """Отправляет случайный кружочек."""

    strings = {"name": "RandomCircle"}

    def __init__(self):
        self.circles = []

    async def fetch_circles(self, client, channel_id):
        circles = []
        try:
            offset_id = 0
            while True:
                history = await client(GetHistoryRequest(channel_id, 100, offset_id=offset_id, hash=0))
                if not history.messages:
                    break
                circles.extend(
                    msg.media.document for msg in history.messages
                    if isinstance(msg.media, MessageMediaDocument) and
                    any(isinstance(attr, DocumentAttributeVideo) and attr.round_message
                        for attr in msg.media.document.attributes)
                )
                offset_id = history.messages[-1].id
        except:
            pass
        return circles

    async def update_circles(self, client):
        channels = [
            -1001678673876, -1001829766952, -1001641159794,
            -1001719785599, -1001549768481, -1001345824533,
            -1001869062957
        ]
        results = await asyncio.gather(*[self.fetch_circles(client, cid) for cid in channels])
        self.circles = [c for r in results if isinstance(r, list) for c in r]

    async def rccmd(self, message):
        """Отправляет случайный кружочек."""
        if not self.circles:
            await self.update_circles(message.client)
        if self.circles:
            await message.client.send_file(message.chat_id, random.choice(self.circles))
        await message.delete()
