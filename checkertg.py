#   Coded by sunshinelzt   #
#     t.me/sunshinelzt     #
# This code under AGPL-3.0 #

from .. import loader, utils
import aiohttp

@loader.tds
class CheckerTGMod(loader.Module):
    """Модуль для проверки пользователя на слитый номер через API"""

    strings = {
        "name": "CheckerTG",
        "checking": "🕵️‍♂️ <b>[CheckerAPI]</b> Выполняю проверку...",
        "getting_id": "🔍 <b>[CheckerAPI]</b> Определяю ID пользователя...",
        "response": (
            "✅ <b>[CheckerAPI]</b> <u>Результат проверки</u>\n\n"
            "👤 <b>ID:</b> <code>{user_id}</code>\n"
            "📞 <b>Номер телефона:</b> <code>{phone_number}</code>\n"
            "⏳ <b>Время выполнения:</b> <code>{time}</code> ms\n\n"
        ),
        "no_user": "⚠️ <b>[CheckerAPI]</b> Укажите ID, username или ответьте на сообщение.",
        "error": "🚨 <b>[CheckerAPI]</b> Ошибка запроса: <code>{}</code>",
        "user_not_found": "❌ <b>[CheckerAPI]</b> Пользователь <code>{}</code> не найден.",
    }

    async def get_user_id(self, username, client):
        """Получаем user ID по username с использованием Telegram API"""
        try:
            entity = await client.get_entity(username)
            return entity.id, entity.username  # Возвращаем ID и тэг
        except Exception as e:
            return None, None  # Если ошибка, возвращаем None для обоих значений

    @loader.owner
    async def checkcmd(self, m):
        """Основная команда для проверки пользователя на слитый номер"""
        reply = await m.get_reply_message()
        # Получаем идентификатор пользователя, если он передан в аргументах или в ответе на сообщение
        user_input = utils.get_args_raw(m) or (reply.sender_id if reply else None)

        if not user_input:
            return await m.edit(self.strings["no_user"])

        # Если передан username, пытаемся получить его ID и тег
        if isinstance(user_input, str) and user_input.startswith("@"):
            await m.edit(self.strings["getting_id"])
            user_id, tag = await self.get_user_id(user_input, m.client)
            if not user_id:
                return await m.edit(self.strings["user_not_found"].format(user_input))
        else:
            user_id = str(user_input)
            tag = None  # Если ID, то тэг не нужен

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

            # Извлекаем только номер телефона из данных
            phone_number = data.get("data", "").split(" | ")[0].replace("Phone: ", "")
            if "Not found!" in phone_number:
                phone_number = "Не найдено"


            # Формируем ответ с результатами проверки, включая только номер телефона
            result_message = self.strings["response"].format(
                user_id=user_id,
                phone_number=phone_number,
                time=round(data.get("time", 0), 3)
            )
            await m.edit(result_message)

        except Exception as e:
            # Логируем ошибку и показываем её пользователю
            await m.edit(self.strings["error"].format(str(e)))
