# meta developer: @sunshinelzt

from telethon import events
from .. import loader, utils
import os
import re

class SaveAndSendMod(loader.Module):
    """Сохраняет сообщения из любых чатов/каналов"""

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
            # Разбираем ссылку
            match = re.search(r"t\.me/(c/)?(\d+|\w+)/(\d+)", args)
            if not match:
                await message.edit("<b>❌ Некорректная ссылка!</b>")
                return

            is_private = bool(match.group(1))  # Если есть 'c/', значит приватный чат
            chat_id = int("-100" + match.group(2)) if is_private else match.group(2)
            message_id = int(match.group(3))

            # Пробуем получить сообщение
            try:
                msg = await self.client.get_messages(chat_id, ids=message_id)
            except:
                await message.edit("<b>❌ Ошибка доступа к сообщению!</b>")
                return

            # Удаляем команду
            await message.delete()

            # Оформляем сообщение
            user = msg.sender
            user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" if user else "👤 Неизвестный"
            header = f"📩 <b>Сообщение от {user_mention}</b>\n\n"
            text = msg.text or "📎 <i>Вложение</i>"
            link = f"\n🔗 <a href='{args}'>Оригинал</a>"
            final_text = header + text + link

            # Проверяем медиа
            if msg.media:
                file = await self.client.download_media(msg)
                await self.client.send_file(message.chat_id, file, caption=final_text, parse_mode="html")
                os.remove(file)
            else:
                await self.client.send_message(message.chat_id, final_text, link_preview=False, parse_mode="html")

        except Exception as e:
            await message.edit(f"<b>❌ Ошибка:</b> {str(e)}")
