# членикииипенис111

import requests
import asyncio
from telethon import loader, utils
from telethon.tl.custom import Message
from telethon import events, Button
from datetime import datetime

class LolzTransferMod(loader.Module):
    """Модуль для перевода средств с поиском пользователя через API lolz.live"""
    strings = {"name": "LolzTransfer"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "API-ключ для lolz.live",
            "SECRET_PHRASE", "", "Секретная фраза для переводов",
            "HOLD_TIME", 0, "Длительность холда (0 = без холда)",
            "HOLD_UNIT", "hour", "Единица времени холда (hour/day)",
            "DEFAULT_CURRENCY", "rub", "Валюта по умолчанию (rub/usd)",
        )
        self.active_transfers = {}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def lolzmcmd(self, message: Message):
        """Перевод: .lolzm ник сумма валюта [комментарий]"""
        if not self.config["API_KEY"] or not self.config["SECRET_PHRASE"]:
            await message.edit("<b>❌ Настройте API_KEY и SECRET_PHRASE в конфиге модуля.</b>")
            return
            
        args = utils.get_args_raw(message).split()
        
        if len(args) < 2:
            await message.edit("<b>Использование:</b> <code>.lolzm ник сумма валюта [комментарий]</code>")
            return
            
        nickname = args[0]
        amount = args[1]
        
        # Проверка валюты, использование значения по умолчанию, если не указано
        if len(args) >= 3 and args[2].lower() in ["rub", "usd"]:
            currency = args[2].lower()
            comment_start = 3
        else:
            currency = self.config["DEFAULT_CURRENCY"]
            comment_start = 2
            
        comment = " ".join(args[comment_start:]) if len(args) > comment_start else "Перевод от пользователя Telegram"
        
        # Анимированное сообщение при поиске пользователя
        search_msg = await message.edit(f"🔍 <b>Поиск пользователя</b> <code>{nickname}</code>...")
        
        # Поиск пользователя через API
        user = await self.find_user(nickname)
        if not user:
            await search_msg.edit(f"❌ <b>Пользователь</b> <code>{nickname}</code> <b>не найден.</b>")
            return
            
        # Составляем текст с информацией о переводе
        profile_url = f"https://lolz.live/members/{user['id']}/"
        text = (
            f"💸 <b>Вы собираетесь перевести:</b> <code>{amount} {currency.upper()}</code>\n"
            f"👤 <b>Получатель:</b> <a href='{profile_url}'>{user['name']}</a>\n"
            f"💬 <b>Комментарий:</b> <i>{comment}</i>\n"
            f"⏳ <b>Холд:</b> {'Без холда' if self.config['HOLD_TIME'] == 0 else f'{self.config['HOLD_TIME']} {self.config['HOLD_UNIT']}'}"
        )
        
        # Уникальный ID для этого перевода
        transfer_id = f"{message.chat_id}_{message.id}_{datetime.now().timestamp()}"
        
        # Кнопки подтверждения или отмены
        buttons = [
            [Button.inline("✅ Подтвердить", data=f"confirm_{transfer_id}"),
             Button.inline("❌ Отмена", data=f"cancel_{transfer_id}")]
        ]
        
        # Сохраняем информацию о переводе
        self.active_transfers[transfer_id] = {
            "user_id": user['id'],
            "amount": amount,
            "currency": currency,
            "comment": comment,
            "message": None,
        }
        
        # Отправляем сообщение с кнопками
        confirm_msg = await self.client.send_message(
            message.chat_id, 
            text, 
            buttons=buttons, 
            parse_mode='html',
            reply_to=message.id
        )
        
        # Сохраняем сообщение
        self.active_transfers[transfer_id]["message"] = confirm_msg

    async def find_user(self, nickname: str):
        """Поиск пользователя по нику через API lolz.live"""
        url = f"https://api.lzt.market/users/find?username={nickname}"
        headers = {
            "Authorization": f"Bearer {self.config['API_KEY']}",
            "User-Agent": "Mozilla/5.0"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("user"):
                return {"id": data['user']['id'], "name": data['user']['username']}
            return None
        except Exception:
            return None

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
            "comment": comment
        }
        
        # Добавляем параметры холда только если холд не равен 0
        if self.config["HOLD_TIME"] > 0:
            payload["hold"] = self.config["HOLD_TIME"]
            payload["hold_unit"] = self.config["HOLD_UNIT"]

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @loader.owner
    async def watcher(self, event):
        """Наблюдатель для обработки нажатий на кнопки"""
        if not isinstance(event, events.CallbackQuery.Event):
            return
            
        data = event.data.decode("utf-8")
        
        if data.startswith("confirm_"):
            transfer_id = data[len("confirm_"):]
            
            if transfer_id in self.active_transfers:
                transfer_data = self.active_transfers[transfer_id]
                
                # Обновляем сообщение
                await event.edit(
                    f"🔄 <b>Выполняется перевод...</b>\n"
                    f"<i>Пожалуйста, подождите.</i>"
                )
                
                # Выполняем перевод
                response = await self.transfer_funds(
                    transfer_data["user_id"],
                    transfer_data["amount"],
                    transfer_data["currency"],
                    transfer_data["comment"]
                )
                
                if "error" not in response:
                    # Успешный перевод
                    await event.edit(
                        f"✅ <b>Перевод выполнен успешно!</b>\n\n"
                        f"💸 <b>Сумма:</b> <code>{transfer_data['amount']} {transfer_data['currency'].upper()}</code>\n"
                        f"🆔 <b>ID перевода:</b> <code>{response.get('transfer_id', 'Н/Д')}</code>",
                        buttons=[
                            [Button.url("🔍 Просмотреть на сайте", f"https://lolz.live/market/balance/history")]
                        ]
                    )
                else:
                    # Ошибка при переводе
                    await event.edit(
                        f"❌ <b>Ошибка при выполнении перевода:</b>\n"
                        f"<code>{response.get('error', 'Неизвестная ошибка')}</code>"
                    )
                
                # Удаляем информацию о переводе
                del self.active_transfers[transfer_id]
                
        elif data.startswith("cancel_"):
            transfer_id = data[len("cancel_"):]
            
            if transfer_id in self.active_transfers:
                transfer_data = self.active_transfers[transfer_id]
                
                # Обновляем сообщение
                await event.edit(f"❌ <b>Перевод отменен.</b>")
                
                # Удаляем информацию о переводе
                del self.active_transfers[transfer_id]
