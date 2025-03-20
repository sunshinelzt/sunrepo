# meta developer

import logging
import requests
from telethon import Button
from .. import loader, utils  # Hikka loader

logger = logging.getLogger(__name__)

@loader.tds
class LolzTransferMod(loader.Module):
    """💸 Умный перевод денег на lolz.live с подтверждением"""

    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "🔑 API-ключ от lolz.live",
            "SECRET_PHRASE", "", "🔐 Секретная фраза для переводов"
        )

    async def client_ready(self, client, db):
        self.client = client

    async def lolzmcmd(self, message):
        """💰 Перевод: .lolzm ник сумма [комментарий]"""
        args = utils.get_args_raw(message).split()

        if len(args) < 2:
            await message.edit("<b>❌ Использование:</b> <code>.lolzm ник сумма [комментарий]</code>")
            return

        nickname, amount = args[:2]
        comment = " ".join(args[2:]) if len(args) > 2 else "Без комментария"

        # 🔍 Поиск пользователя
        user = self.get_user_by_nickname(nickname)
        if not user:
            await message.edit(f"❌ <b>Пользователь</b> <code>{nickname}</code> <b>не найден.</b>")
            return

        profile_url = f"https://lolz.live/members/{user['id']}/"

        # 💰 Проверка баланса
        balance = self.get_balance()
        if balance is None:
            await message.edit("⚠️ <b>Ошибка:</b> Не удалось получить баланс.")
            return

        if float(amount) > balance:
            await message.edit(f"🚫 <b>Недостаточно средств!</b> Ваш баланс: <code>{balance} RUB</code>")
            return

        text = (
            f"💸 <b>Вы собираетесь перевести</b>: <code>{amount} RUB</code>\n"
            f"👤 <b>Получатель</b>: <a href='{profile_url}'>{user['name']}</a>\n"
            f"💬 <b>Комментарий</b>: <i>{comment}</i>\n"
        )

        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{user['id']}_{amount}_{comment}")],
            [Button.inline("❌ Отмена", data="cancel")]
        ]

        await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode="html")

    def get_user_by_nickname(self, nickname):
        """🔍 Поиск пользователя"""
        url = f"https://api.zelenka.guru/users/find?username={nickname}"
        headers = {"Authorization": f"Bearer {self.config['API_KEY']}"}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data and "user_id" in data[0]:
                return {"id": data[0]["user_id"], "name": data[0]["username"]}
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка поиска {nickname}: {e}")
        return None

    def get_balance(self):
        """💰 Получение баланса"""
        url = "https://api.lzt.market/balance"
        headers = {"Authorization": f"Bearer {self.config['API_KEY']}"}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return float(data.get("rub", 0))
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка получения баланса: {e}")
        return None

    async def on_callback_query(self, call):
        """🔄 Обработка кнопок"""
        data = call.data.decode("utf-8")
        if data.startswith("confirm_"):
            _, user_id, amount, comment = data.split("_", 3)
            response = self.transfer_funds(user_id, amount, comment)
            if response.get("success"):
                await call.answer("✅ Перевод успешно выполнен!", alert=True)
                await call.edit(f"✅ <b>Перевод {amount} RUB успешно отправлен!</b>")
            else:
                error = response.get("error", "Ошибка при переводе.")
                await call.answer(f"❌ {error}", alert=True)
        elif data == "cancel":
            await call.answer("❌ Перевод отменён.", alert=True)
            await call.edit("⚠️ <b>Перевод отменён.</b>")

    def transfer_funds(self, user_id, amount, comment):
        """💸 Выполнение перевода"""
        url = "https://api.lzt.market/balance/transfer"
        headers = {"Authorization": f"Bearer {self.config['API_KEY']}"}
        data = {
            "amount": float(amount),
            "currency": "rub",
            "secret_answer": self.config["SECRET_PHRASE"],
            "user_id": int(user_id),
            "comment": comment
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка при переводе: {e}")
            return {"error": "Произошла ошибка при переводе."}
