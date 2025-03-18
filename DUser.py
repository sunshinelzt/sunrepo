# meta developer: @sunshinelzt

import io
import logging
import re
from telethon.tl.types import Message
from telethon.errors import RPCError
from .. import loader, utils

logger = logging.getLogger(__name__)

def register(cb):
    cb(DUsersMod())

class DUsersMod(loader.Module):
    """Дамп пользователей чата в CSV"""

    strings = {"name": "DUsers"}

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

    async def ducmd(self, message: Message):
        """<n> <m> <s>
        <n> - Только с открытыми номерами
        <m> - Отправить дамп в избранное
        <s> - Тихий режим (без уведомлений)
        """
        if not message.chat:
            await message.edit("<b>Это не чат!</b>")
            return

        try:
            args = utils.get_args_raw(message).lower() or ""
            num_only = "n" in args
            to_me = "m" in args
            silent = "s" in args

            chat = await self._client.get_entity(message.chat_id)
            chat_title = chat.title or "Без названия"
            chat_id = message.chat_id

            clean_chat_title = re.sub(r'[\\/*?:"<>|]', "_", chat_title)
            file_name = f"Dump_{clean_chat_title}_{chat_id}.csv"

            if not silent:
                status_msg = await message.edit(f"📥 Дампим чат: <b>{chat_title}</b>...")

            f = io.BytesIO()
            f.name = file_name

            header = f"Чат: {chat_title}\nID чата: {chat_id}\n\nИмя;Фамилия;Юзернейм;ID;Телефон\n"
            f.write(header.encode("utf-8"))

            me = await self._client.get_me()
            participants = await self._client.get_participants(chat_id)

            for user in participants:
                if user.id == me.id:
                    continue
                if num_only and not user.phone:
                    continue

                f.write(
                    f"{self._format_field(user.first_name)};"
                    f"{self._format_field(user.last_name)};"
                    f"{self._format_field(user.username)};"
                    f"{user.id};"
                    f"{self._format_field(user.phone)}\n".encode("utf-8")
                )

            f.seek(0)
            caption = f"📄 Дамп чата: <b>{chat_title}</b>\n🆔 ID: <code>{chat_id}</code>"

            if to_me:
                await self._client.send_file("me", f, caption=caption, force_document=True)
            else:
                await self._client.send_file(message.chat_id, f, caption=caption, force_document=True)

            if not silent:
                await status_msg.edit(f"✅ Дамп завершён!\nФайл сохранён для <b>{chat_title}</b>.")

            await message.delete()

        except RPCError as rpc_err:
            error_msg = f"❌ Ошибка RPC: <code>{rpc_err}</code>"
            await self._handle_error(message, error_msg)

        except (ValueError, TypeError, OSError) as e:
            error_msg = f"❌ Ошибка: <code>{str(e)}</code>"
            await self._handle_error(message, error_msg)

        except Exception as e:
            error_msg = "❌ Произошла непредвиденная ошибка. Подробности в логах."
            await self._handle_error(message, error_msg)

        finally:
            f.close()

    def _format_field(self, value):
        return f'"{value}"' if value else '"None"'

    async def _handle_error(self, message: Message, error_msg: str):
        try:
            await self._client.send_message("me", error_msg)
        except Exception as e:
            logger.error(f"Не удалось отправить ошибку в избранное: {e}")
        
        await message.edit(f"<b>{error_msg}</b>")
        await message.delete()
