#   Coded by sunshinelzt   #
#     t.me/sunshinelzt     #
# This code under AGPL-3.0 #

# meta developer @sunshinelzt

__version__ = (1, 0, 0, 0)

from .. import loader, utils
import aiohttp
from typing import Optional, Tuple

@loader.tds
class CheckerTGMod(loader.Module):
    """Модуль для проверки пользователя на слитый номер через API"""

    strings = {
        "name": "CheckerTG",
        "checking": "<emoji document_id=5348282577662778261>🔍</emoji> <b>[CheckerAPI]</b> Выполняю проверку...",
        "getting_id": "<emoji document_id=5348282577662778261>🔍</emoji> <b>[CheckerAPI]</b> Определяю ID пользователя...",
        "response": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>[CheckerAPI]</b> <u>Результат проверки</u>\n\n"
            "<emoji document_id=5879770735999717115>👤</emoji> <b>ID:</b> <code>{user_id}</code>\n"
            "<emoji document_id=5897488197650223178>📞</emoji> <b>Номер телефона:</b> <code>{phone_number}</code>\n"
            "<emoji document_id=5960751816084820359>⏲️</emoji> <b>Время выполнения:</b> <code>{time}</code> ms\n"
        ),
        "no_user": "<emoji document_id=5775887550262546277>❗️</emoji> <b>[CheckerAPI]</b> Укажите ID, username или ответьте на сообщение.",
        "error": "<emoji document_id=5778527486270770928>❌</emoji> <b>[CheckerAPI]</b> Ошибка запроса: <code>{}</code>",
        "user_not_found": "<emoji document_id=5778527486270770928>❌</emoji> <b>[CheckerAPI]</b> Пользователь <code>{}</code> не найден.",
        "invalid_uid": "<emoji document_id=5778527486270770928>❌</emoji> <b>[CheckerAPI]</b> UID должен быть целым числом!",
    }

    API_URL = "https://api.d4n13l3k00.ru/tg/leaked/check"
    REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

    async def get_user_id(self, username: str, client) -> Tuple[Optional[int], Optional[str]]:
        """Получает user ID и username по идентификатору через Telegram API"""
        try:
            entity = await client.get_entity(username)
            return entity.id, getattr(entity, 'username', None)
        except Exception:
            return None, None

    def parse_phone_number(self, data: dict) -> str:
        """Парсит номер телефона из ответа API"""
        raw_data = data.get("data", "")
        
        if "Not found" in raw_data:
            return "Не найден!"
        
        if "UID must be int!" in raw_data:
            return "UID должен быть целым числом!"
        
        if " | " in raw_data:
            phone = raw_data.split(" | ")[0].replace("Phone: ", "").strip()
            return phone if phone else "Не найден!"
        
        return "Не найден!"

    async def fetch_user_data(self, user_id: str) -> dict:
        """Выполняет запрос к API для получения данных пользователя"""
        async with aiohttp.ClientSession(timeout=self.REQUEST_TIMEOUT) as session:
            async with session.get(f"{self.API_URL}?uid={user_id}") as resp:
                if resp.status != 200:
                    raise ValueError(f"HTTP {resp.status}")
                return await resp.json()

    @loader.owner
    async def checkcmd(self, m):
        """.check <user_id/@username/reply> - проверка пользователя на слитый номер"""
        reply = await m.get_reply_message()
        user_input = utils.get_args_raw(m) or (reply.sender_id if reply else None)

        if not user_input:
            return await m.edit(self.strings["no_user"])

        if isinstance(user_input, str) and user_input.startswith("@"):
            await m.edit(self.strings["getting_id"])
            user_id, _ = await self.get_user_id(user_input, m.client)
            
            if not user_id:
                return await m.edit(self.strings["user_not_found"].format(user_input))
        else:
            user_id = str(user_input).strip()
            
            if not user_id.isdigit():
                return await m.edit(self.strings["invalid_uid"])

        await m.edit(self.strings["checking"])

        try:
            data = await self.fetch_user_data(user_id)
            phone_number = self.parse_phone_number(data)
            
            result_message = self.strings["response"].format(
                user_id=user_id,
                phone_number=phone_number,
                time=round(data.get("time", 0), 3)
            )
            
            await m.edit(result_message)

        except aiohttp.ClientError as e:
            await m.edit(self.strings["error"].format(f"Ошибка сети: {type(e).__name__}"))
        except ValueError as e:
            await m.edit(self.strings["error"].format(str(e)))
        except Exception as e:
            await m.edit(self.strings["error"].format(f"Неизвестная ошибка: {type(e).__name__}"))
