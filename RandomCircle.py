# meta developer: @sunshinelzt

import random
from telethon.tl.types import InputPeerChannel
from telethon.tl.functions.messages import GetHistoryRequest

from .. import loader, utils

@loader.tds
class RandomCircleMod(loader.Module):
    strings = {"name": "RandomCircle"}

    async def get_all_messages(self, client, peer):
        all_messages = []
        offset_id = 0

        while True:
            history = await client(
                GetHistoryRequest(
                    peer=peer,
                    limit=100,
                    offset_id=offset_id,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0,
                )
            )

            if not history.messages:
                break

            all_messages.extend(history.messages)
            offset_id = history.messages[-1].id

        return all_messages

    async def rccmd(self, message):
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

        random.shuffle(channels_ids)

        try:
            for channel_id in channels_ids:
                entity = await message.client.get_entity(channel_id)
                peer = InputPeerChannel(entity.id, entity.access_hash)

                all_messages = await self.get_all_messages(message.client, peer)

                circles = [
                    msg for msg in all_messages if msg.media and msg.media.document.mime_type == "video/mp4"
                ]

                if circles:
                    random_circle = random.choice(circles)
                    await message.client.send_message(
                        message.chat_id, file=random_circle.media.document
                    )
                    await message.delete()
                    return

            await message.edit("Не удалось найти кружочки.")

        except Exception as e:
            await message.edit(f"Произошла ошибка: {str(e)}")
