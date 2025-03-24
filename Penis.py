# членикииипенис111

import asyncio
import aiohttp
from typing import Optional, Dict, Any, Tuple
from telethon import Button
from urllib.parse import quote_plus

from .. import loader, utils

@loader.tds
class LolzTransferMod(loader.Module):
    """💰 Продвинутый модуль безопасных переводов Lolz.live"""

    strings = {
        "name": "LolzTransfer",
        "transfer_header": "💸 <b>Безопасный перевод средств</b>",
        "config_api_token": "🔑 API токен Lolz.live",
        "config_secret_phrase": "🔐 Секретная фраза для переводов",
        "transfer_confirm": (
            "🔔 Подтверждение перевода:\n\n"
            "• Сумма: <code>{amount}</code> руб.\n"
            "• Получатель: {user_link}\n"
            "• Комментарий: <code>{comment}</code>\n\n"
            "⚠️ Тщательно проверьте данные!"
        ),
        "transfer_success": (
            "✅ Перевод выполнен!\n\n"
            "• Сумма: <code>{amount}</code> руб.\n"
            "• Получатель: {user_link}\n"
            "• Комментарий: <code>{comment}</code>"
        ),
        "transfer_failed": "❌ Ошибка перевода: {error}",
        "user_not_found": "🔍 Пользователь <code>{username}</code> не найден",
        "invalid_amount": "❗ Некорректная сумма. Введите положительное число.",
        "missing_arguments": "❓ Формат: .transfer <ник> <сумма> [комментарий]",
        "no_config": "❌ Настройте API токен и секретную фразу!"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token", 
                None, 
                doc=lambda: self.strings["config_api_token"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "secret_phrase", 
                None, 
                doc=lambda: self.strings["config_secret_phrase"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "hold", 
                0, 
                doc="Время холда в днях",
                validator=loader.validators.Integer(minimum=0)
            )
        )

    async def client_ready(self, client, db):
        self.client = client

    async def _validate_config(self) -> bool:
        """Проверка конфигурации"""
        if not self.config['api_token'] or not self.config['secret_phrase']:
            return False
        return True

    async def _get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        if not await self._validate_config():
            return None

        username_encoded = quote_plus(username)
        headers = {"Authorization": f"Bearer {self.config['api_token']}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.lolz.live/users/find?username={username_encoded}", 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    users = data.get("users", [])
                    matching_users = [
                        user for user in users 
                        if user["username"].lower() == username.lower()
                    ]
                    return matching_users[0] if matching_users else None
                return None

    async def _send_transfer(
        self, 
        user_id: str, 
        amount: float, 
        comment: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Выполнение перевода через API"""
        headers = {"Authorization": f"Bearer {self.config['api_token']}"}
        payload = {
            "user_id": user_id,
            "amount": amount,
            "secret_phrase": self.config["secret_phrase"],
            "hold": self.config.get("hold", 0),
            "comment": comment
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.lolz.live/market/pay", 
                json=payload, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                result = await response.json()
                return result.get("success", False), result

    @loader.command(ru_doc="Перевести средства пользователю")
    async def transfercmd(self, message):
        """Инициировать безопасный перевод"""
        if not await self._validate_config():
            await utils.answer(message, self.strings["no_config"])
            return

        args = utils.get_args_raw(message).split(maxsplit=2)
        if len(args) < 2:
            await utils.answer(message, self.strings["missing_arguments"])
            return

        username, amount, *comment = args
        comment = comment[0] if comment else "Без комментария"

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await utils.answer(message, self.strings["invalid_amount"])
            return

        user_info = await self._get_user_info(username)
        if not user_info:
            await utils.answer(
                message, 
                self.strings["user_not_found"].format(username=username)
            )
            return

        user_id = user_info["user_id"]
        user_link = f"[{username}](https://lolz.live/members/{user_id}/)"

        buttons = [
            [
                Button.inline(
                    "✅ Подтвердить", 
                    data=f"lolz_confirm_{user_id}_{amount}_{quote_plus(comment)}"
                ),
                Button.inline("❌ Отмена", data="lolz_cancel")
            ]
        ]

        await utils.answer(
            message, 
            self.strings["transfer_confirm"].format(
                amount=f"{amount:.2f}", 
                user_link=user_link, 
                comment=comment
            ),
            buttons=buttons
        )

    @loader.callback_handler()
    async def transfer_callback(self, event):
        """Обработчик инлайн-коллбэков"""
        data = event.data.decode()

        if data == "lolz_cancel":
            await event.edit(self.strings["transfer_failed"].format(error="Отменено пользователем"))
            return

        if data.startswith("lolz_confirm_"):
            _, user_id, amount, comment = data.split("_", 3)
            amount = float(amount)
            comment = quote_plus(comment, safe='')

            user_info = await self._get_user_info_by_id(user_id)
            if not user_info:
                await event.edit(
                    self.strings["user_not_found"].format(username=user_id)
                )
                return

            username = user_info["username"]
            user_link = f"[{username}](https://lolz.live/members/{user_id}/)"

            success, result = await self._send_transfer(user_id, amount, comment)

            if success:
                await event.edit(
                    self.strings["transfer_success"].format(
                        amount=f"{amount:.2f}", 
                        user_link=user_link, 
                        comment=comment
                    )
                )
            else:
                await event.edit(
                    self.strings["transfer_failed"].format(
                        error=result.get("error", "Неизвестная ошибка")
                    )
                )

    async def _get_user_info_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе по ID"""
        headers = {"Authorization": f"Bearer {self.config['api_token']}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.lolz.live/users/{user_id}", 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("user")
                return None
