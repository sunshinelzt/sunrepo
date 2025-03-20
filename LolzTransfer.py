# meta developer

import logging
import requests
import urllib.parse  # Кодирование URL
from telethon import Button
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class LolzTransferMod(loader.Module):
    """Перевод денег на lolz.live с подтверждением"""

    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "api_key", "", "API-ключ от lolz.live",
            "secret_phrase", "", "Секретная фраза для переводов"
        )

    async def client_ready(self, client, db):
        self.client = client

    async def lolzmcmd(self, message):
        """Перевод: .lolzm ник сумма [комментарий]"""
        args = utils.get_args_raw(message).split()

        if len(args) < 2:
            await message.edit("<b>Использование:</b> <code>.lolzm ник сумма [комментарий]</code>")
            return

        nickname, amount = args[:2]
        comment = " ".join(args[2:]) if len(args) > 2 else "Без комментария"

        # Кодируем ник для API
        encoded_nickname = urllib.parse.quote(nickname)

        # Получаем пользователя
        user = self.get_user_by_nickname(encoded_nickname)
        if not user:
            await message.edit(f"❌ Пользователь <code>{nickname}</code> не найден.")
            return

        profile_url = f"https://lolz.live/members/{user['id']}/"

        # Получаем баланс
        balance = self.get_balance()
        if balance is None:
            await message.edit("❌ Не удалось получить баланс. Проверьте API-ключ.")
            return

        if float(amount) > balance:
            await message.edit(f"❌ Недостаточно средств. Ваш баланс: <code>{balance} RUB</code>")
            return

        text = (
            f"<b>Вы собираетесь перевести:</b> <code>{amount} RUB</code>\n"
            f"<b>Получатель:</b> <a href='{profile_url}'>{user['name']}</a>\n"
            f"<b>Комментарий:</b> <i>{comment}</i>\n"
            f"<b>Перевод защищён секретной фразой.</b>"
        )

        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{user['id']}_{amount}_{comment}")],
            [Button.inline("❌ Отмена", data="cancel")]
        ]

        await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode="html")

    def get_user_by_nickname(self, encoded_nickname):
        """Поиск пользователя по нику на форуме"""
        url = f"https://api.zelenka.guru/users/find?username={encoded_nickname}"
        headers = {"Authorization": f"Bearer {self.config['api_key']}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            user_data = response.json()
            if "user_id" in user_data:
                return {"id": user_data["user_id"], "name": user_data["username"]}
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при поиске {encoded_nickname}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети при поиске {encoded_nickname}: {e}")
        return None

    def get_balance(self):
        """Получение текущего баланса"""
        url = "https://api.lzt.market/balance"
        headers = {"Authorization": f"Bearer {self.config['api_key']}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            balance_data = response.json()
            return balance_data.get("balance")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return None

    async def on_callback_query(self, call):
        """Обработка inline-кнопок"""
        data = call.data.decode("utf-8")

        if data.startswith("confirm_"):
            _, user_id, amount, comment = data.split("_", 3)
            response = self.transfer_funds(user_id, amount, comment)
            
            if response and response.get("success"):
                await call.answer("✅ Перевод успешно выполнен.", alert=True)
            else:
                error = response.get("error", "Ошибка при переводе.")
                await call.answer(f"❌ {error}", alert=True)

        elif data == "cancel":
            await call.answer("❌ Перевод отменен.", alert=True)

    def transfer_funds(self, user_id, amount, comment):
        """Выполнение перевода средств"""
        url = "https://api.lzt.market/balance/transfer"
        headers = {"Authorization": f"Bearer {self.config['api_key']}"}
        data = {
            "currency": "rub",
            "amount": float(amount),
            "recipient_id": int(user_id),
            "comment": comment,
            "secret_phrase": self.config["secret_phrase"]
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка перевода: {e}")
            return {"error": "Произошла ошибка при переводе."}
