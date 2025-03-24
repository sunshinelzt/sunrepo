# член

from telethon import events, Button
from .. import loader, utils
import requests
import asyncio

@loader.tds
class LolzTransferMod(loader.Module):
    """Модуль для перевода средств на форуме lolz.live через Hikka Userbot"""

    strings = {
        "name": "LolzTransfer",
        "transfer_confirm": (
            "🔔 Подтверждение перевода:\n\n"
            "Сумма: {amount} руб.\n"
            "Получатель: {user_link}\n"
            "Комментарий: {comment}\n\n"
            "Проверьте все данные перед подтверждением."
        ),
        "transfer_success": (
            "✅ Перевод успешно выполнен!\n\n"
            "Сумма: {amount} руб.\n"
            "Получатель: {user_link}\n"
            "Комментарий: {comment}"
        ),
        "transfer_failed": "❌ Ошибка перевода: {error}",
        "user_not_found": "🔍 Пользователь {username} не найден.",
        "invalid_amount": "❗ Некорректная сумма. Введите положительное число.",
        "missing_arguments": "❓ Используйте: .transfer <ник> <сумма> [комментарий]",
        "transfer_cancelled": "🚫 Перевод отменен.",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token", 
                None, 
                doc="API токен для доступа к форуму и маркету lolz.live"
            ),
            loader.ConfigValue(
                "secret_phrase", 
                None, 
                doc="Секретная фраза для подтверждения перевода"
            ),
        )

    async def client_ready(self, client, db):
        self.client = client

    async def transfercmd(self, message):
        """Команда для безопасного перевода средств с подтверждением."""
        args = utils.get_args_raw(message).split(maxsplit=2)
        if len(args) < 2:
            await message.reply(self.strings["missing_arguments"])
            return

        username, amount = args[:2]
        comment = args[2] if len(args) == 3 else "Без комментария"

        try:
            amount = float(amount)

            user_info = await self.get_user_info(username)
            if not user_info:
                await message.reply(self.strings["user_not_found"].format(username=username))
                return

            user_id = user_info["user_id"]
            user_link = f"https://lolz.live/members/{user_id}/"

            confirm_message = self.strings["transfer_confirm"].format(
                amount=amount, 
                user_link=f"[{username}]({user_link})", 
                comment=comment
            )
            buttons = [
                [
                    Button.inline("✅ Подтвердить", data=f"confirm_transfer_{user_id}_{amount}_{comment}"),
                    Button.inline("❌ Отмена", data="cancel_transfer")
                ]
            ]

            await self.client.send_message(
                message.chat_id, confirm_message, buttons=buttons
            )
        except Exception as e:
            await message.reply(self.strings["transfer_failed"].format(error=str(e)))

    @loader.callback_handler()
    async def callback_handler(self, event):
        """Обработчик инлайн-кнопок с логикой перевода."""
        data = event.data.decode("utf-8")
        try:
            if data.startswith("confirm_transfer_"):
                _, user_id, amount, comment = data.split("_", 3)
                amount = float(amount)

                user_info = await self.get_user_info_by_id(user_id)
                if not user_info:
                    raise ValueError(self.strings["user_not_found"].format(username=user_id))

                username = user_info["username"]
                user_link = f"https://lolz.live/members/{user_id}/"

                success, result = await self.send_money(user_id, amount, comment)
                if success:
                    success_message = self.strings["transfer_success"].format(
                        amount=amount, 
                        user_link=f"[{username}]({user_link})", 
                        comment=comment
                    )
                    await event.edit(success_message)
                else:
                    error_message = self.strings["transfer_failed"].format(error=result)
                    await event.edit(error_message)

            elif data == "cancel_transfer":
                await event.edit(self.strings["transfer_cancelled"])

        except Exception as e:
            await event.answer(str(e), alert=True)

    async def get_user_info(self, username):
        """Получение информации о пользователе по нику"""
        try:
            headers = {"Authorization": f"Bearer {self.config['api_token']}"}
            response = requests.get(
                f"https://api.lolz.live/users/find?username={username}", 
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            users = response.json().get("users", [])
            
            matching_users = [
                user for user in users 
                if user["username"].lower() == username.lower()
            ]
            
            return matching_users[0] if matching_users else None
        
        except requests.RequestException as e:
            raise RuntimeError(f"Ошибка API: {e}")

    async def get_user_info_by_id(self, user_id):
        """Получение информации о пользователе по ID"""
        try:
            headers = {"Authorization": f"Bearer {self.config['api_token']}"}
            response = requests.get(
                f"https://api.lolz.live/users/{user_id}", 
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            user = response.json().get("user", {})
            return user
        
        except requests.RequestException as e:
            raise RuntimeError(f"Ошибка API: {e}")

    async def send_money(self, user_id, amount, comment):
        """Отправка средств."""
        try:
            headers = {"Authorization": f"Bearer {self.config['api_token']}"}
            data = {
                "user_id": user_id,
                "amount": amount,
                "secret_phrase": self.config["secret_phrase"],
                "comment": comment,
            }
            
            response = requests.post(
                "https://api.lolz.live/market/pay", 
                json=data, 
                headers=headers,
                timeout=15
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return True, result
            else:
                return False, result.get("error", "Неизвестная ошибка")
        
        except requests.RequestException as e:
            return False, str(e)
