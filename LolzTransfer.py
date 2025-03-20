# meta developer

import requests
import urllib.parse
from telethon import events, Button
from telethon.tl.custom import Message
from hikka import loader, utils

class LolzTransferMod(loader.Module):
    """Модуль для перевода денег на Lolz.live"""
    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "api_key", "", "API-ключ от LolzTeam (Lolz.live)",
            "secret_phrase", "", "Секретная фраза для переводов",
            "hold_time", 0, "Длительность холда (0 = без холда)",
            "hold_unit", "hour", "Единица времени холда (hour/day)"
        )

    async def client_ready(self, client, db):
        self.client = client

    async def lolzmcmd(self, message: Message):
        """Перевод: .lolzm <ник> <сумма> <валюта> [комментарий]"""
        args = utils.get_args_raw(message).split()

        if len(args) < 3:
            return await message.edit("<b>Использование:</b> <code>.lolzm ник сумма валюта [комментарий]</code>")

        nickname, amount, currency = args[:3]
        comment = " ".join(args[3:]) if len(args) > 3 else "Без комментария"

        user = await self.find_user(nickname)
        if not user:
            return await message.edit(f"❌ <b>Пользователь</b> <code>{nickname}</code> <b>не найден.</b>")

        profile_url = f"https://lolz.live/members/{user['id']}/"
        text = (
            f"💸 <b>Вы собираетесь перевести:</b> <code>{amount} {currency.upper()}</code>\n"
            f"👤 <b>Получатель:</b> <a href='{profile_url}'>{user['name']}</a>\n"
            f"💬 <b>Комментарий:</b> <i>{comment}</i>\n"
            f"⏳ <b>Холд:</b> {self.config['hold_time']} {self.config['hold_unit']}"
        )

        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{user['id']}_{amount}_{currency}_{comment}"),
             Button.inline("❌ Отмена", data="cancel")]
        ]

        await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode='html')

    async def find_user(self, nickname: str):
        """Поиск пользователя по нику"""
        url = f"https://api.zelenka.guru/users/find?username={urllib.parse.quote(nickname)}"
        headers = {"Authorization": f"Bearer {self.config['api_key']}"}

        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            if response.status_code == 200 and "user_id" in data:
                return {"id": data["user_id"], "name": data["username"]}
        except requests.RequestException as e:
            return None

    async def on_callback_query(self, call):
        """Обработка кнопок"""
        data = call.data.decode("utf-8")
        if data.startswith("confirm_"):
            _, user_id, amount, currency, comment = data.split("_", 4)
            response = await self.transfer_funds(user_id, amount, currency, comment)
            if response.get("success"):
                await call.answer("✅ Перевод выполнен!", alert=True)
            else:
                error = response.get("error", "Ошибка при переводе.")
                await call.answer(f"❌ {error}", alert=True)
        elif data == "cancel":
            await call.answer("❌ Перевод отменён.", alert=True)

    async def transfer_funds(self, user_id, amount, currency, comment):
        """Перевод денег"""
        url = "https://api.lzt.market/balance/transfer"
        headers = {"Authorization": f"Bearer {self.config['api_key']}"}
        data = {
            "amount": float(amount),
            "currency": currency.lower(),
            "secret_answer": self.config["secret_phrase"],
            "user_id": int(user_id),
            "comment": comment,
            "hold": self.config["hold_time"],
            "hold_option": self.config["hold_unit"]
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            return response.json()
        except requests.RequestException:
            return {"error": "Ошибка при отправке запроса."}
