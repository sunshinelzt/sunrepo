# членикииипенис

import requests
from telethon import loader, utils
from telethon.tl.custom import Message
from telethon import events, Button

class LolzTransferMod(loader.Module):
    """Модуль для перевода средств с поиском пользователя через API Zelenka"""
    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "API-ключ для Zelenka",
            "SECRET_PHRASE", "", "Секретная фраза для переводов",
            "HOLD_TIME", 0, "Длительность холда (0 = без холда)",
            "HOLD_UNIT", "hour", "Единица времени холда (hour/day)"
        )

    async def client_ready(self, client, db):
        self.client = client

    async def lolzmcmd(self, message: Message):
        """Перевод: .lolzm ник сумма валюта [комментарий]"""
        args = utils.get_args_raw(message).split()

        if len(args) < 3:
            await message.edit("<b>Использование:</b> <code>.lolzm ник сумма валюта [комментарий]</code>")
            return

        nickname, amount, currency = args[:3]
        comment = " ".join(args[3:]) if len(args) > 3 else "Без комментария"

        # Поиск пользователя через API Zelenka
        user = await self.find_user(nickname)
        if not user:
            await message.edit(f"❌ <b>Пользователь</b> <code>{nickname}</code> <b>не найден.</b>")
            return

        # Составляем текст с информацией о переводе
        profile_url = f"https://lolz.live/members/{user['id']}/"
        text = (
            f"💸 <b>Вы собираетесь перевести:</b> <code>{amount} {currency.upper()}</code>\n"
            f"👤 <b>Получатель:</b> <a href='{profile_url}'>{user['name']}</a>\n"
            f"💬 <b>Комментарий:</b> <i>{comment}</i>\n"
            f"⏳ <b>Холд:</b> {self.config['HOLD_TIME']} {self.config['HOLD_UNIT']}"
        )

        # Кнопки подтверждения или отмены
        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{user['id']}_{amount}_{currency}_{comment}"),
             Button.inline("❌ Отмена", data="cancel")]
        ]

        # Отправляем сообщение с кнопками
        await self.client.send_message(message.chat_id, text, buttons=buttons, parse_mode='html')

    async def find_user(self, nickname: str):
        """Поиск пользователя по нику через API Zelenka"""
        url = f"https://api.zelenka.guru/users/find?username={nickname}"
        headers = {
            "Authorization": f"Bearer {self.config['API_KEY']}",
            "User-Agent": "Mozilla/5.0"
        }
        
        # Отправка GET запроса
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Проверка на ошибки
            data = response.json()
            if data.get("status") == "success":
                return {"id": data['user']['id'], "name": data['user']['username']}
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при поиске пользователя: {e}")
            return None

    async def on_callback_query(self, call):
        """Обработка callback запросов на кнопки"""
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
        url = "https://api.lzt.market/balance/transfer"
        headers = {
            "Authorization": f"Bearer {self.config['API_KEY']}",
            "Content-Type": "application/json"
        }

        # Параметры для перевода
        payload = {
            "amount": amount,
            "currency": currency,
            "secret_answer": self.config["SECRET_PHRASE"],
            "user_id": user_id,
            "comment": comment,
            "hold": self.config["HOLD_TIME"],
            "hold_unit": self.config["HOLD_UNIT"]
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при выполнении перевода: {e}")
            return {"error": "Произошла ошибка при выполнении перевода."}
