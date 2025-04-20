# meta developer: @sunshinelzt
# scope: hikka_min 1.3.0
# requires: telethon

import logging
from telethon import events
from telethon.errors.rpcerrorlist import MessageNotModifiedError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Message, PeerUser

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class MessageCollectorMod(loader.Module):
    """Собирает сообщения пользователя из чата и сохраняет их в текстовый файл"""
    
    strings = {
        "name": "MessageCollector",
        "starting": "<b>🔍 Начинаю сбор сообщений...</b>",
        "collected": "<b>✅ Собрано {count} текстовых сообщений.</b>",
        "saved": "<b>💾 Сообщения сохранены в файл: {filename}</b>",
        "no_reply": "<b>⚠️ Ответьте на сообщение пользователя, чтобы собрать его сообщения.</b>",
        "processing": "<b>⏳ Обработано {current} из примерно {total} сообщений...</b>",
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
            await utils.answer(message, self.strings["no_reply"])
            return
        
        user_id = reply.sender_id
        chat_id = message.chat_id
        status_msg = await utils.answer(message, self.strings["starting"])
        
        collected_messages = []
        
        # Оценка общего количества сообщений для прогресс-бара
        estimated_total = 1000  # Примерное значение, может быть скорректировано
        
        offset_id = 0
        limit = 100
        
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
            
            if not history.messages:
                break
                
            messages = history.messages
            
            for msg in messages:
                if msg.sender_id == user_id and isinstance(msg, Message) and msg.message:
                    collected_messages.append(msg.message)
                
            # Обновление статуса каждые 100 сообщений
            if len(collected_messages) % 100 == 0:
                try:
                    await utils.answer(
                        status_msg, 
                        self.strings["processing"].format(
                            current=len(collected_messages),
                            total=estimated_total
                        )
                    )
                except MessageNotModifiedError:
                    pass
                    
            offset_id = messages[-1].id
            
            if len(messages) < limit:
                break
        
        if not collected_messages:
            await utils.answer(status_msg, self.strings["no_messages"])
            return
            
        # Сохраняем сообщения в файл
        filename = f"messages_{user_id}.txt"
        with open(filename, "w", encoding="utf-8") as file:
            for text in collected_messages:
                file.write(f"{text}\n")
        
        # Отправляем файл в избранные сообщения
        await self.client.send_file(
            "me",
            file=filename,
            caption=f"Собрано {len(collected_messages)} сообщений от пользователя {user_id} из чата {chat_id}"
        )
        
        await utils.answer(
            status_msg, 
            self.strings["collected"].format(count=len(collected_messages)) + 
            "\n" + 
            self.strings["saved"].format(filename=filename)
        )
