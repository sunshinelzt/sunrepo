# членикииипенис123

from .. import loader, utils
import logging
import aiohttp
from telethon.tl.types import Message
from typing import Dict, Any, Union, List, Tuple
import asyncio

logger = logging.getLogger(__name__)


@loader.tds
class LolzLiveAPIMod(loader.Module):
    """Модуль для взаимодействия с API Lolz.live (Zelenka.guru)"""

    strings = {
        "name": "LolzLiveAPI",
        "api_key_error": "❌ <b>API ключ не установлен!</b>\nУстановите его через команду <code>.lolzapi</code>",
        "api_key_set": "✅ <b>API ключ установлен успешно!</b>",
        "user_not_found": "❌ <b>Пользователь не найден!</b>",
        "transfer_success": "✅ <b>Перевод успешно выполнен!</b>",
        "invalid_amount": "❌ <b>Неверная сумма перевода!</b>",
        "api_error": "❌ <b>Ошибка API:</b> {}",
        "no_username": "❌ <b>Укажите имя пользователя!</b>",
        "transfer_confirmation": """💸 <b>Подтверждение перевода</b>
🔹 Получатель: @{}
💰 Сумма: {}₽
📜 Комментарий: "{}"

⚠️ Проверьте данные перед подтверждением!""",
        "transfer_cancelled": "🚫 <b>Перевод отменен!</b>",
        "transfer_timeout": "⏱️ <b>Время ожидания подтверждения истекло!</b>",
        "user_info": """👤 Пользователь: @{}
├ 🔗 Профиль LZT: {}
├ ℹ️ Группа: {}
├ 📝 Статус: {}
├ 💬 Сообщений: {}
├ 💚 Симпатий: {}
├ 👍 Лайков: {}
├ 🎁 Розыгрышей: {}
├ 🏆 Трофеев: {}
├ 👥 Подписчиков: {}
├ 👤 Подписок: {}
├ ⏳ Дата регистрации: {}
└ ✅ Заблокирован: {}""",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "api_key", None, "API ключ для Lolz.live",
            "api_url", "https://api.lolz.live", "URL API Lolz.live",
            "secret_phrase", None, "Секретная фраза для подтверждения переводов"
        )
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self._client = client
        self._db = db

    async def lolzapicmd(self, message: Message):
        """
        Установка API ключа
        Использование: .lolzapi <ваш_api_ключ>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["api_key_error"])
            return

        self._db.set("lolzliveapi", "api_key", args)
        await utils.answer(message, self.strings["api_key_set"])

    async def lolzpcmd(self, message: Message):
        """
        Получение информации о пользователе
        Использование: .lolzp <username>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_username"])
            return

        api_key = self._db.get("lolzliveapi", "api_key", None)
        if not api_key:
            await utils.answer(message, self.strings["api_key_error"])
            return

        async with aiohttp.ClientSession() as session:
            try:
                user_info = await self._fetch_user_info(session, args, api_key)
                if not user_info:
                    await utils.answer(message, self.strings["user_not_found"])
                    return

                user_data = user_info["data"]
                is_blocked = "Да" if user_data.get("is_blocked", False) else "Нет"
                profile_url = f"https://lolz.live/members/{user_data['id']}"

                response = self.strings["user_info"].format(
                    user_data["username"],
                    profile_url,
                    user_data.get("group", "Неизвестно"),
                    user_data.get("status", "Неизвестно"),
                    user_data.get("messages_count", 0),
                    user_data.get("likes_count", 0),
                    user_data.get("likes_given", 0),
                    user_data.get("giveaways_count", 0),
                    user_data.get("trophies_count", 0),
                    user_data.get("followers_count", 0),
                    user_data.get("subscriptions_count", 0),
                    user_data.get("registration_date", "Неизвестно"),
                    is_blocked
                )

                await utils.answer(message, response)
            except Exception as e:
                logger.error(f"Error fetching user info: {e}")
                await utils.answer(message, self.strings["api_error"].format(str(e)))

    async def lolztcmd(self, message: Message):
        """
        Перевод средств пользователю
        Использование: .lolzt <username> <amount> <comment>
        """
        args = utils.get_args(message)
        if len(args) < 2:
            await utils.answer(message, "❌ <b>Неверный формат команды!</b>\nИспользование: <code>.lolzt username amount [comment]</code>")
            return

        api_key = self._db.get("lolzliveapi", "api_key", None)
        secret_phrase = self.config["secret_phrase"]
        
        if not api_key:
            await utils.answer(message, self.strings["api_key_error"])
            return
            
        if not secret_phrase:
            await utils.answer(message, "❌ <b>Секретная фраза не установлена!</b>\nУстановите её в конфигурации модуля.")
            return

        username = args[0]
        try:
            amount = float(args[1])
            if amount <= 0:
                await utils.answer(message, self.strings["invalid_amount"])
                return
        except ValueError:
            await utils.answer(message, self.strings["invalid_amount"])
            return

        comment = " ".join(args[2:]) if len(args) > 2 else "Автоматический перевод by sunshinelzt"

        async with aiohttp.ClientSession() as session:
            try:
                user_info = await self._fetch_user_info(session, username, api_key)
                if not user_info:
                    await utils.answer(message, self.strings["user_not_found"])
                    return

                user_id = user_info["data"]["id"]
                username = user_info["data"]["username"]

                confirmation_message = await utils.answer(
                    message, 
                    self.strings["transfer_confirmation"].format(username, amount, comment)
                )
                
                await self._client.edit_message(
                    confirmation_message.chat_id,
                    confirmation_message.id,
                    self.strings["transfer_confirmation"].format(username, amount, comment),
                    buttons=[
                        [{"text": "✅ Подтвердить", "callback": f"lolz_confirm_{user_id}_{amount}_{comment}"}],
                        [{"text": "❌ Отменить", "callback": "lolz_cancel"}]
                    ]
                )
                
            except Exception as e:
                logger.error(f"Error in transfer preparation: {e}")
                await utils.answer(message, self.strings["api_error"].format(str(e)))

    async def _fetch_user_info(self, session: aiohttp.ClientSession, username: str, api_key: str) -> Dict[str, Any]:
        """Получение информации о пользователе по логину"""
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        async with session.get(
            f"{self.config['api_url']}/users/find",
            headers=headers,
            params={"username": username}
        ) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None
            else:
                raise Exception(f"API error: {response.status}")

    async def _make_transfer(self, session: aiohttp.ClientSession, user_id: int, amount: float, comment: str, api_key: str) -> Dict[str, Any]:
        """Выполнение перевода средств пользователю"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "user_id": user_id,
            "amount": amount,
            "secret_phrase": self.config["secret_phrase"],
            "comment": comment
        }
        
        async with session.post(
            f"{self.config['api_url']}/market/pay",
            headers=headers,
            json=data
        ) as response:
            return await response.json()

    async def lolz_confirm_callback(self, call):
        """Обработка подтверждения перевода"""
        try:
            _, user_id, amount, comment = call.data.split("_", 3)
            user_id = int(user_id)
            amount = float(amount)
        except (ValueError, IndexError):
            await call.edit("❌ <b>Ошибка обработки запроса!</b>")
            return

        api_key = self._db.get("lolzliveapi", "api_key", None)
        if not api_key:
            await call.edit(self.strings["api_key_error"])
            return

        async with aiohttp.ClientSession() as session:
            try:
                result = await self._make_transfer(session, user_id, amount, comment, api_key)
                if result.get("status") == 200:
                    await call.edit(self.strings["transfer_success"])
                else:
                    await call.edit(self.strings["api_error"].format(result.get("message", "Неизвестная ошибка")))
            except Exception as e:
                logger.error(f"Error in transfer execution: {e}")
                await call.edit(self.strings["api_error"].format(str(e)))

    async def lolz_cancel_callback(self, call):
        """Обработка отмены перевода"""
        await call.edit(self.strings["transfer_cancelled"])
