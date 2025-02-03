#   Codes by sunshinelzt   #
#     t.me/sunshinelzt     #
# This code under AGPL-3.0 #

from .. import loader, utils
import aiohttp

@loader.tds
class CheckerTGMod(loader.Module):
    """Модуль для проверки пользователя на слитый номер через API"""

    strings = {
        "name": "CheckerTG",
        "checking": "🕵 <b>[CheckerAPI]</b> Выполняю проверку...",
        "getting_id": "🔍 <b>[CheckerAPI]</b> Определяю ID пользователя...",
        "response": (
            "✅ <b>[CheckerAPI]</b> <u>Результат проверки</u>\n\n"
            "👤 <b>ID:</b> <code>{user_id}</code>\n"
            "📞 <b>Данные:</b> <code>{data}</code>\n"
            "⏳ <b>Время выполнения:</b> <code>{time}</code> ms"
        ),
        "no_user": "⚠️ <b>[CheckerAPI]</b> Укажите ID, username или ответьте на сообщение.",
        "error": "🚨 <b>[CheckerAPI]</b> Ошибка запроса: <code>{}</code>",
        "user_not_found": "❌ <b>[CheckerAPI]</b> Пользователь <code>{}</code> не найден.",
    }

    async def get_user_id(self, username, client):
        """Получаем user ID по username с использованием Telegram API"""
        try:
            entity = await client.get_entity(username)
            return entity.id
        except Exception as e:
            return None  # Если возникла ошибка, возвращаем None

    @loader.owner
    async def checkcmd(self, m):
        """Основная команда для проверки пользователя на слитый номер"""
        reply = await m.get_reply_message()
        # Получаем идентификатор пользователя, если он передан в аргументах или в ответе на сообщение
        user_input = utils.get_args_raw(m) or (reply.sender_id if reply else None)

        if not user_input:
            return await m.edit(self.strings["no_user"])

        # Если передан username, пытаемся получить его ID
        if isinstance(user_input, str) and user_input.startswith("@"):
            await m.edit(self.strings["getting_id"])
            user_id = await self.get_user_id(user_input, m.client)
            if not user_id:
                return await m.edit(self.strings["user_not_found"].format(user_input))
        else:
            user_id = str(user_input)

        # Отправляем запрос к API для проверки
        await m.edit(self.strings["checking"])

        url = f"https://api.d4n13l3k00.ru/tg/leaked/check?uid={user_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    # Проверяем статус ответа
                    if resp.status != 200:
                        raise ValueError(f"HTTP {resp.status}")
                    data = await resp.json()

            # Формируем ответ с результатами проверки
            result_message = self.strings["response"].format(
                user_id=user_id,
                data=data.get("data", "Нет данных"),
                time=round(data.get("time", 0), 3)
            )
            await m.edit(result_message)

        except Exception as e:
            # Логируем ошибку и показываем её пользователю
            await m.edit(self.strings["error"].format(str(e)))
