# meta developer: @sunshinelzt
# scope: hikka_min 1.3.0
# requires: telethon

import logging
import asyncio
import os
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class MessageCollectorMod(loader.Module):
    """Собирает сообщения пользователя из чата и сохраняет их в текстовый файл"""
    
    strings = {
        "name": "MessageCollector",
        "starting": "<b>🔍 Начинаю сбор сообщений...</b>",
        "collected": "<b>✅ Собрано {count} текстовых сообщений.</b>",
        "saved": "<b>💾 Сообщения сохранены и отправлены в избранное.</b>",
        "no_reply": "<b>⚠️ Ответьте на сообщение пользователя, чтобы собрать его сообщения.</b>",
        "no_messages": "<b>❌ Не найдено текстовых сообщений от этого пользователя.</b>"
    }

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

    @loader.command(ru_doc="Собрать сообщения пользователя по реплею")
    async def collectmsg(self, message):
        """Собирает текстовые сообщения пользователя по реплею и сохраняет в файл"""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, self.strings["no_reply"])

        user_id = reply.sender_id
        chat_id = message.chat_id
        status_msg = await utils.answer(message, self.strings["starting"])

        filename = f"messages_{user_id}.txt"
        count = 0
        offset_id = 0
        limit = 100

        with open(filename, "w", encoding="utf-8") as file:
            while True:
                history = await self.client(GetHistoryRequest(
                    peer=chat_id,
                    offset_id=offset_id,
                    offset_date=None,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))

                msgs = history.messages
                if not msgs:
                    break

                for msg in msgs:
                    if msg.sender_id == user_id and isinstance(msg, Message) and msg.message:
                        file.write(f"{msg.message}\n")
                        count += 1

                offset_id = msgs[-1].id
                if len(msgs) < limit:
                    break
                await asyncio.sleep(0)

        if count == 0:
            os.remove(filename)
            return await utils.answer(status_msg, self.strings["no_messages"])

        await self.client.send_file(
            "me",
            file=filename,
            caption=f"Собрано {count} сообщений от пользователя {user_id} из чата {chat_id}"
        )

        try:
            os.remove(filename)
        except Exception as e:
            logger.warning(f"Не удалось удалить файл: {e}")

        await utils.answer(
            status_msg,
            self.strings["collected"].format(count=count) + "\n" + self.strings["saved"]
        )
