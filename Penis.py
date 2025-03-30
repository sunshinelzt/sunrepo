# членикииипенис1

import aiohttp
import asyncio
import logging
from telethon.tl.types import Message
from telethon.errors import MessageNotModifiedError

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class LolzLiveMod(loader.Module):
    """Модуль для работы с API Lolz.live (Zelenka.guru)"""

    strings = {
        "name": "LolzLive",
        "api_error": "❌ Ошибка API: <code>{}</code>",
        "profile_not_found": "❌ Пользователь <b>{}</b> не найден!",
        "invalid_amount": "❌ Некорректная сумма!",
        "transfer_confirm": (
            "💸 <b>Подтверждение перевода</b>\n\n"
            "🔹 Получатель: {user}\n"
            "💰 Сумма: <code>{amount}</code>₽\n"
            "📜 Комментарий: <code>{comment}</code>\n\n"
            "⚠️ Проверьте данные перед подтверждением!"
        ),
        "transfer_success": (
            "✅ <b>Перевод выполнен!</b>\n\n"
            "🔹 Получатель: {user}\n"
            "💰 Сумма: <code>{amount}</code>₽\n"
            "📜 Комментарий: <code>{comment}</code>"
        ),
        "transfer_cancelled": "🚫 Перевод отменён!",
        "transfer_failed": "❌ Ошибка при переводе: <code>{}</code>"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token",
                None,
                "🔑 API-ключ Lolz.live",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "secret_phrase",
                None,
                "🔐 Секретная фраза для переводов",
                validator=loader.validators.String(),
            ),
        )
        self._lock = asyncio.Lock()  # Защита от одновременных запросов
        self._pending_transfers = {}

    async def _api_request(self, endpoint, params=None, method="GET"):
        """Запрос к API Lolz.live"""
        token = self.config["api_token"]
        if not token:
            return None, "API-ключ не настроен!"

        url = f"https://api.lolz.live/{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with self._lock:
                async with aiohttp.ClientSession() as session:
                    async with (session.get(url, headers=headers, params=params) if method == "GET"
                                else session.post(url, headers=headers, json=params)) as response:
                        if response.status != 200:
                            return None, f"Ошибка {response.status}"
                        return await response.json(), None
        except Exception as e:
            logger.error(f"Ошибка API: {e}")
            return None, str(e)

    async def _get_user_info(self, username):
        """Получение информации о пользователе"""
        data, error = await self._api_request(f"users/find?username={username}")
        if error:
            return None, error

        users = data.get("users", [])
        for user in users:
            if user["username"].lower() == username.lower():
                return user, None
        return None, "Пользователь не найден!"

    async def lolzp_cmd(self, message: Message):
        """Получает информацию о профиле Lolz.live"""
        args = utils.get_args(message)
        if not args:
            return await message.edit("❌ Укажите ник пользователя!")

        username = args[0]
        user, error = await self._get_user_info(username)
        if error:
            return await message.edit(self.strings("profile_not_found").format(username))

        text = (
            f"👤 <b>Профиль {user['username']}</b>\n"
            f"🔹 ID: <code>{user['user_id']}</code>\n"
            f"💰 Баланс: <code>{user['balance']}</code>₽\n"
            f"📌 Статус: <b>{user['status']}</b>\n"
            f"🎭 Группа: <b>{user['group']}</b>\n"
            f"🔗 <a href='https://lolz.live/members/{user['user_id']}/'>Профиль</a>"
        )
        await message.edit(text)

    async def lolzt_cmd(self, message: Message):
        """Переводит деньги пользователю Lolz.live"""
        args = utils.get_args(message)
        if len(args) < 2:
            return await message.edit("❌ Используйте: <code>.lolzt ник сумма [комментарий]</code>")

        username, amount, *comment = args
        try:
            amount = float(amount)
            if amount <= 0:
                return await message.edit(self.strings("invalid_amount"))
        except ValueError:
            return await message.edit(self.strings("invalid_amount"))

        comment = " ".join(comment) if comment else "Нет комментария"
        user, error = await self._get_user_info(username)
        if error:
            return await message.edit(self.strings("profile_not_found").format(username))

        user_id = user["user_id"]
        user_link = f'<a href="https://lolz.live/members/{user_id}/">{username}</a>'

        msg = await message.edit(
            self.strings("transfer_confirm").format(user=user_link, amount=amount, comment=comment),
            buttons=[
                [
                    {"text": "✅ Подтвердить", "callback": self._confirm_transfer, "args": (message, user_id, amount, comment)},
                    {"text": "❌ Отмена", "callback": self._cancel_transfer, "args": (message,)}
                ]
            ]
        )

        self._pending_transfers[message.id] = msg

    async def _confirm_transfer(self, call, message: Message, user_id, amount, comment):
        """Подтверждение перевода"""
        token = self.config["api_token"]
        secret = self.config["secret_phrase"]

        if not token or not secret:
            return await call.answer("❌ API-ключ и секретная фраза не настроены!", show_alert=True)

        data, error = await self._api_request(
            "market/pay",
            {
                "user_id": user_id,
                "amount": amount,
                "secret_phrase": secret,
                "comment": comment
            },
            method="POST"
        )

        if error:
            return await message.edit(self.strings("transfer_failed").format(error))

        user_link = f'<a href="https://lolz.live/members/{user_id}/">{user_id}</a>'
        await message.edit(
            self.strings("transfer_success").format(user=user_link, amount=amount, comment=comment)
        )

    async def _cancel_transfer(self, call, message: Message):
        """Отмена перевода"""
        await message.edit(self.strings("transfer_cancelled"))
