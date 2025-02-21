# meta developer: @sunshinelzt

from telethon import events
from .. import loader, utils
import os
from datetime import datetime

class SaveAndSendMod(loader.Module):
    """Сохраняет сообщения из закрытых чатов и отправляет в текущий чат"""

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
            parts = args.split("/")
            chat_id = int(parts[-3]) if parts[-3].isdigit() else parts[-3]
            message_id = int(parts[-1])

            # Получаем сообщение
            msg = await self.client.get_messages(chat_id, ids=message_id)
            if not msg:
                await message.edit("<b>❌ Не удалось получить сообщение!</b>")
                return

            # Удаляем команду
            await message.delete()

            # Получаем данные отправителя
            user = msg.sender
            user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" if user else "👤 Неизвестный"
            timestamp = msg.date.strftime("%d.%m.%Y %H:%M") if msg.date else "Неизвестно"
            header = f"📩 <b>Сообщение от {user_mention}</b>\n🕒 <i>{timestamp}</i>\n\n"

            # Текст сообщения
            text = msg.text or "📎 <i>Вложение</i>"

            # Добавляем ссылку на оригинал (если доступно)
            link = f"\n🔗 <a href='{args}'>Оригинал</a>" if "t.me/c/" in args or "t.me/" in args else ""

            # Итоговый текст
            final_text = header + text + link

            # Если есть медиа, скачиваем и отправляем
            if msg.media:
                file = await self.client.download_media(msg)
                await self.client.send_file(message.chat_id, file, caption=final_text, parse_mode="html")
                os.remove(file)
            else:
                await self.client.send_message(message.chat_id, final_text, link_preview=False, parse_mode="html")

        except Exception as e:
            await message.edit(f"<b>❌ Ошибка:</b> {str(e)}")
