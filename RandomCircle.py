# meta developer: @sunshinelzt

import random
from telethon.tl.types import InputPeerChannel, MessageMediaDocument
from telethon.tl.functions.messages import GetHistoryRequest

from .. import loader, utils

@loader.tds
class RandomCircleMod(loader.Module):
    """Модуль для отправки случайного мемного кружочка"""

    strings = {"name": "RandomCircle"}

    async def rccmd(self, message):
        """Отправляет случайный кружочек."""

        channels_ids = [
            -1001678673876,
            -1001829766952,
            -1001641159794,
            -1001719785599,
            -1001549768481,
            -1001662197039,
            -1001345824533,
            -1001869062957
        ]

        try:
            random_channel_id = random.choice(channels_ids)
            entity = await message.client.get_entity(random_channel_id)
            peer = InputPeerChannel(entity.id, entity.access_hash)

            history = await message.client(
                GetHistoryRequest(
                    peer=peer,
                    limit=100,
                    offset_date=None,
                    offset_id=0,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0,
                )
            )

            circles = [
                msg for msg in history.messages 
                if isinstance(msg.media, MessageMediaDocument) and 
                msg.media.document.attributes and 
                any(attr for attr in msg.media.document.attributes if attr.__class__.__name__ == "DocumentAttributeVideo" and getattr(attr, 'round_message', False))
            ]

            if circles:
                random_circle = random.choice(circles)
                await message.client.send_file(message.chat_id, file=random_circle.media.document)
            
            await message.delete()

        except:
            pass  # Игнорируем все ошибки
