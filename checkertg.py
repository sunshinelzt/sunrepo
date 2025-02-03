#   Codes by sunshinelzt   #
#     t.me/sunshinelzt     #
# This code under AGPL-3.0 #

from .. import loader, utils
import aiohttp
import logging

logger = logging.getLogger(__name__)

@loader.tds
class CheckerTGMod(loader.Module):
    """Проверка пользователя на слитый номер через API"""

    strings = {
        "name": "CheckerTG",
        "checking": "<emoji id=5312761529620724326>🕵</emoji> <b>[CheckerAPI]</b> Выполняю проверку...",
        "getting_id": "<emoji id=5312761529620724326>🔍</emoji> <b>[CheckerAPI]</b> Определяю ID пользователя...",
        "response": (
            "<emoji id=6021527789754852614>✅</emoji> <b>[CheckerAPI]</b> <u>Результат проверки</u>\n\n"
            "<emoji id=5466067023296850447>👤</emoji> <b>ID:</b> <code>{user_id}</code>\n"
            "<emoji id=5460910603862105027>📊</emoji> <b>Статус:</b> <code>{status}</code>\n"
            "<emoji id=5464222038336177963>📞</emoji> <b>Данные:</b> <code>{data}</code>\n"
            "<emoji id=5203282991565838731>⏳</emoji> <b>Время выполнения:</b> <code>{time}</code> ms"
        ),
        "no_user": "<emoji id=5312149028952733148>⚠️</emoji> <b>[CheckerAPI]</b> Укажите ID, username или ответьте на сообщение.",
        "error": "<emoji id=6022549192248977621>🚨</emoji> <b>[CheckerAPI]</b> Ошибка запроса: <code>{}</code>",
        "user_not_found": "<emoji id=5312149028952733148>❌</emoji> <b>[CheckerAPI]</b> Пользователь <code>{}</code> не найден.",
    }

    async def get_user_id(self, username, client):
        """Асинхронно получает user ID по username"""
        try:
            entity = await client.get_entity(username)
            return entity.id
        except Exception as e:
            logger.error(f"Ошибка при получении ID {username}: {e}")
            return None

    @loader.owner
    async def checkcmd(self, m):
        """Проверяет ID на слитый номер (по ID, username или reply)"""
        reply = await m.get_reply_message()
        user_input = utils.get_args_raw(m) or (reply.sender_id if reply else None)

        if not user_input:
            return await m.edit(self.strings["no_user"])

        # Определение ID, если передан username
        if isinstance(user_input, str) and user_input.startswith("@"):
            await m.edit(self.strings["getting_id"])
            user_id = await self.get_user_id(user_input, m.client)
            if not user_id:
                return await m.edit(self.strings["user_not_found"].format(user_input))
        else:
            user_id = str(user_input)

        await m.edit(self.strings["checking"])

        url = f"https://api.d4n13l3k00.ru/tg/leaked/check?uid={user_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise ValueError(f"HTTP {resp.status}")
                    data = await resp.json()

            await m.edit(
                self.strings["response"].format(
                    user_id=user_id,
                    status=data.get("status", "unknown"),
                    data=data.get("data", "Нет данных"),
                    time=round(data.get("time", 0), 3),
                )
            )

        except Exception as e:
            logger.error(f"Ошибка запроса: {e}")
            await m.edit(self.strings["error"].format(str(e)))
