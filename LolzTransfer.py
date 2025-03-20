# meta developer

import requests
from bs4 import BeautifulSoup
from telethon import events, Button
from hikka import loader, utils
from telethon.tl.custom import Message

class LolzTransferMod(loader.Module):
    """Модуль для перевода средств на Lolz.live с улучшенным поиском через BeautifulSoup"""
    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "api_key", "", "API-ключ для Zelenka (Lolz.live)",
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
        """Поиск пользователя по нику с использованием BeautifulSoup"""
        url = f"https://zelenka.guru/search?query={nickname}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Генерирует исключение, если статус ответа не 200
            soup = BeautifulSoup(response.text, 'html.parser')

            # Поиск нужной информации, предполагаем что результаты будут в каком-то контейнере с классом 'user-item'
            user_item = soup.find("div", class_="user-item")
            if not user_item:
                return None  # Если пользователя не найдено

            user_id = user_item["data-user-id"]
            user_name = user_item.find("span", class_="username").text.strip()

            return {"id": user_id, "name": user_name}
        except requests.exceptions.RequestException as e:
            return None

    async def on_callback_query(self, call):
        """Обработка inline кнопок для подтверждения или отмены перевода"""
        data = call.data.decode("utf-8")
        if data.startswith("confirm_"):
            _, user_id, amount, currency, comment = data.split("_", 4)
            response = await self.transfer_funds(user_id, amount, currency, comment)
            if response.get("success"):
                await call.answer("✅ Перевод успешно выполнен!", alert=True)
            else:
                error = response.get("error", "Ошибка при переводе.")
                await call.answer(f"❌ {error}", alert=True)
        elif data == "cancel":
            await call.answer("❌ Перевод отменён.", alert=True)

    async def transfer_funds(self, user_id, amount, currency, comment):
        """Функция для выполнения перевода средств"""
        try:
            url = "https://api.lzt.market/balance/transfer"
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            data = {
                "amount": float(amount),
                "currency": currency.lower(),
                "secret_answer": self.config["secret_phrase"],
                "user_id": user_id,
                "comment": comment,
                "hold_time": self.config["hold_time"],
                "hold_unit": self.config["hold_unit"]
            }
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()  # Генерирует исключение для ненормальных ответов
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": "Произошла ошибка при переводе."}
