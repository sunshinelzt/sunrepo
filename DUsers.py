# meta developer: @sunshinelzt

import io
import logging
import re
from telethon.tl.types import Message
from .. import loader, utils  # type: ignore

logger = logging.getLogger(__name__)

def register(cb):
    cb(DUsersMod())

class DUsersMod(loader.Module):
    """📊 Дамп пользователей чата в CSV"""

    strings = {"name": "DUsers"}

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

    async def ducmd(self, message: Message):
        """.du <n> <m> <s>
        📄 Дамп пользователей чата в CSV
        <n> - Только с открытыми номерами
        <m> - Отправить дамп в избранное
        <s> - Тихий режим (без уведомлений)
        """
        if not message.chat:
            await message.edit("<b>🚫 Это не чат!</b>")
            return

        args = utils.get_args_raw(message)
        num_only = "n" in args
        to_me = "m" in args
        silent = "s" in args

        chat = await self._client.get_entity(message.chat_id)
        chat_title = chat.title or "Без названия"
        chat_id = message.chat_id

        clean_chat_title = re.sub(r'[\\/*?:"<>|]', "_", chat_title)
        file_name = f"Dump_{clean_chat_title}_{chat_id}.csv"

        if not silent:
            status_msg = await message.edit(f"📊 <b>Дампим чат</b>: <a href='tg://resolve?domain={chat.username}'>{chat_title}</a>...")

        f = io.BytesIO()
        f.name = file_name
        f.write(f"Название чата:;{chat_title}\n".encode())
        f.write("Имя;Фамилия;Юзернейм;ID;Телефон\n".encode())

        try:
            me = await self._client.get_me()
            participants = await self._client.get_participants(chat_id)

            for user in participants:
                if user.id == me.id:
                    continue
                if num_only and not user.phone:
                    continue

                f.write(
                    f"{user.first_name or ''};{user.last_name or ''};{user.username or ''};"
                    f"{user.id};{user.phone or ''}\n".encode()
                )

            f.seek(0)
            caption = f"📄 <b>Дамп чата:</b> <a href='tg://resolve?domain={chat.username}'>{chat_title}</a>\n🆔 <code>{chat_id}</code>"

            if to_me:
                await self._client.send_file("me", f, caption=caption)
            else:
                await message.reply(file=f, caption=caption)

            if not silent:
                await status_msg.edit(f"✅ <b>Дамп завершён!</b>\n📂 Файл сохранён для <a href='tg://resolve?domain={chat.username}'>{chat_title}</a>.")

        except Exception as e:
            logger.error(f"Ошибка при дампе чата {chat_id}: {e}")
            await message.edit(f"❌ Ошибка: {str(e)}")

        finally:
            f.close()
