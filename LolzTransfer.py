# meta developer

import logging
import requests
from telethon import loader, utils, Button

logger = logging.getLogger(__name__)

@loader.tds
class LolzTransferMod(loader.Module):
    """Мгновенные переводы на lolz.live прямо из Hikka Userbot"""
    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "🔑 API-ключ от lolz.live",
            "SECRET_PHRASE", "", "🔐 Секретная фраза для переводов",
            "HOLD_TIME", 0, "⏳ Длительность холда (0 — без холда)",
            "HOLD_OPTION", "hour", "⏳ Единица холда (hour/day)"
        )

    async def client_ready(self, client, db):
        self.client = client

    async def lolzmcmd(self, message):
        """Использование: .lolzm <ник> <сумма> [комментарий]"""
        args = utils.get_args_raw(message).split()
        if len(args) < 2:
            await message.edit("❌ <b>Ошибка:</b> Укажите <code>.lolzm ник сумма [комментарий]</code>")
            return

        nickname, amount, *comment = args
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await message.edit("❌ <b>Ошибка:</b> Сумма должна быть положительным числом.")
            return

        comment = " ".join(comment) if comment else "💬 Без комментария"

        user = self.get_user_by_nickname(nickname)
        if not user:
            await message.edit(f"❌ <b>Ошибка:</b> Пользователь <code>{nickname}</code> не найден.")
            return

        balance = self.get_balance()
        if balance is None:
            await message.edit("⚠️ <b>Ошибка:</b> Не удалось получить баланс.")
            return
        if amount > balance:
            await message.edit(f"❌ <b>Ошибка:</b> Недостаточно средств.\n💰 Баланс: <code>{balance} RUB</code>")
            return

        profile_url = f"https://lolz.live/members/{user['user_id']}/"
        text = (
            f"💸 <b>Вы собираетесь перевести:</b> <code>{amount} RUB</code>\n"
            f"👤 <b>Получатель:</b> <a href='{profile_url}'>{user['username']}</a>\n"
            f"💬 <b>Комментарий:</b> <i>{comment}</i>\n"
            f"⏳ <b>Холд:</b> {self.config['HOLD_TIME']} {self.config['HOLD_OPTION']}\n\n"
            f"🔒 <b>Проверьте данные перед подтверждением!</b>"
        )

        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{user['user_id']}_{amount}_{comment}"),
             Button.inline("❌ Отмена", data="cancel")]
        ]

        await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode="html")

    def get_user_by_nickname(self, nickname):
        """Поиск пользователя по нику"""
        url = f"https://api.zelenka.guru/users/find?username={nickname}"
        headers = {"Authorization": f"Bearer {self.config['API_KEY']}"}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data and "user_id" in data[0]:
                return data[0]
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка поиска {nickname}: {e}")
        return None

    def get_balance(self):
        """Получение текущего баланса"""
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
        """Обработка inline кнопок"""
        data = call.data.decode("utf-8")
        if data.startswith("confirm_"):
            _, user_id, amount, comment = data.split("_", 3)
            response = self.transfer_funds(user_id, amount, comment)
            if response.get("success"):
                await call.answer("✅ Перевод успешно выполнен!", alert=True)
            else:
                error = response.get("error", "Ошибка при переводе.")
                await call.answer(f"❌ {error}", alert=True)
        elif data == "cancel":
            await call.answer("❌ Перевод отменён.", alert=True)

    def transfer_funds(self, user_id, amount, comment):
        """Выполнение перевода"""
        url = "https://api.lzt.market/balance/transfer"
        headers = {"Authorization": f"Bearer {self.config['API_KEY']}"}
        data = {
            "amount": float(amount),
            "currency": "rub",
            "secret_answer": self.config["SECRET_PHRASE"],
            "user_id": int(user_id),
            "comment": comment,
            "hold": self.config["HOLD_TIME"],
            "hold_option": self.config["HOLD_OPTION"]
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка перевода: {e}")
            return {"error": "Ошибка перевода."}
