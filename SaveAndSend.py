#meta developer @sunshinelzt

from telethon import events
from .. import loader, utils
import os
import re

class SaveAndSendMod(loader.Module):
    """Скачивает сообщение по ссылке и отправляет его в текущий чат"""

    strings = {"name": "SaveAndSend"}

    async def client_ready(self, client, db):
        self.client = client

    async def savecmd(self, message):
        """Использование: .save <ссылка на сообщение>"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("<b>⚠ Укажи ссылку на сообщение!</b>")
            return

        try:
            # Разбираем ссылку на сообщение
            match = re.search(r"t\.me/(c/)?(\d+|\w+)/(\d+)", args)
            if not match:
                await message.edit("<b>❌ Некорректная ссылка!</b>")
                return

            # Если ссылка указывает на приватный чат, вычисляем его ID
            is_private = bool(match.group(1))  
            chat_id = int("-100" + match.group(2)) if is_private else match.group(2)
            message_id = int(match.group(3))

            # Пытаемся получить сообщение
            try:
                msg = await self.client.get_messages(chat_id, ids=message_id)
            except Exception as e:
                await message.edit(f"<b>❌ Ошибка доступа к сообщению:</b> {str(e)}")
                return

            # Удаляем команду
            await message.delete()

            # Проверяем, есть ли медиа
            if msg.media:
                # Скачиваем медиа
                file = await self.client.download_media(msg)
                # Отправляем в текущий чат
                await self.client.send_file(message.chat_id, file)
                # Удаляем скачанный файл после отправки
                os.remove(file)
            else:
                # Если это текстовое сообщение
                await self.client.send_message(message.chat_id, msg.text)

        except Exception as e:
            await message.edit(f"<b>❌ Ошибка:</b> {str(e)}")
