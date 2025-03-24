# meta developer: @sunshinelzt

from telethon.tl.types import Message
from telethon import events
from .. import loader, utils
import logging
import re
import requests
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import json
import hashlib
from typing import Union
import urllib.parse

logger = logging.getLogger(__name__)

@loader.tds
class LolzTransferMod(loader.Module):
    """Модуль перевода денег для форума lolz.live и lzt.market"""
    
    strings = {
        "name": "LolzTransfer",
        "no_api": "⚠️ <b>API ключ не установлен. Используйте .lzconfig</b>",
        "no_secret": "⚠️ <b>Секретная фраза не установлена. Используйте .lzconfig</b>",
        "config_saved": "✅ <b>Конфигурация успешно сохранена!</b>",
        "invalid_amount": "⚠️ <b>Неверная сумма. Пожалуйста, введите корректное число.</b>",
        "user_not_found": "⚠️ <b>Пользователь не найден на форуме.</b>",
        "transfer_success": "✅ <b>Успешно переведено {amount} {currency} пользователю {username}!</b>",
        "transfer_error": "❌ <b>Ошибка при переводе средств: {error}</b>",
        "transfer_confirm": "💸 <b>Вы собираетесь перевести {amount} {currency} пользователю <a href='{profile_url}'>{username}</a>.</b>\n\n<b>Комментарий:</b> {comment}",
        "confirm": "✅ Подтвердить",
        "cancel": "❌ Отменить",
        "operation_cancelled": "❌ <b>Операция отменена.</b>",
        "checking_user": "🔍 <b>Проверка пользователя {username}...</b>",
        "help_text": (
            "<b>🔹 Помощь по модулю LolzTransfer:</b>\n\n"
            "<code>.lzconfig</code> - Настроить API ключ и секретную фразу\n"
            "<code>.lztransfer [username] [сумма] [валюта] [комментарий]</code> - Перевести деньги\n"
            "<code>валюта</code> - Необязательно, по умолчанию 'rub'\n"
            "<code>комментарий</code> - Необязательно, комментарий к платежу"
        )
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "API Ключ Lolz.Market",
            "SECRET_PHRASE", "", "Секретная фраза для подтверждения переводов",
            "DEFAULT_CURRENCY", "rub", "Валюта по умолчанию (rub, usd и т.д.)",
            "DEFAULT_HOLD", 0, "Срок холда по умолчанию (0 для отсутствия холда)",
            "DEFAULT_HOLD_OPTION", "day", "Опция холда по умолчанию (day, month)",
        )
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        """Вызывается, когда клиент готов."""
        self.client = client
        self.db = db
        self._ratelimit = []
        
        # Регистрация обработчика инлайн-запросов
        client.on(events.InlineQuery(pattern=r"lztransfer (.+)"))
        
        # Регистрация обработчика колбэков бота
        self.bot = self.inline.bot
        self.bot.add_callback_query_handler(
            self.inline_callback_handler,
            lambda query: query.data.startswith("lztransfer_")
        )
    
    def get_user_id(self, username):
        """Получение ID пользователя по имени через API форума"""
        try:
            # URL-кодирование имени пользователя для поддержки русских ников
            encoded_username = urllib.parse.quote(username)
            
            # Поиск пользователя на форуме
            url = f"https://api.lolz.live/users/find?username={encoded_username}"
            headers = {"Authorization": f"Bearer {self.config['API_KEY']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("user_id"):
                    return data["user_id"], f"https://lolz.live/members/{data['user_id']}"
            
            # Если первый метод не сработал, попробуем найти по точному совпадению
            url = "https://api.lolz.live/users/search"
            params = {"username": username}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    for user in data:
                        if user.get("username").lower() == username.lower():
                            return user["user_id"], f"https://lolz.live/members/{user['user_id']}"
            
            return None, None
        except Exception as e:
            logger.error(f"Ошибка получения ID пользователя: {e}")
            return None, None
    
    async def transfer_money(self, user_id, amount, currency, comment, secret_answer):
        """Перевод денег через API lzt.market"""
        try:
            url = "https://api.lzt.market/balance/transfer"
            headers = {"Authorization": f"Bearer {self.config['API_KEY']}"}
            
            payload = {
                "amount": float(amount),
                "currency": currency,
                "secret_answer": secret_answer,
                "user_id": int(user_id),
                "comment": comment,
                "hold": self.config["DEFAULT_HOLD"],
                "hold_option": self.config["DEFAULT_HOLD_OPTION"]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return True, None
            else:
                error_data = response.json()
                return False, error_data.get("message", "Неизвестная ошибка")
                
        except Exception as e:
            logger.error(f"Ошибка перевода: {e}")
            return False, str(e)
    
    def generate_callback_data(self, user_id, amount, currency, username, comment):
        """Генерация безопасных данных для callback"""
        # Создаем уникальный идентификатор для операции
        operation_id = hashlib.md5(f"{user_id}_{amount}_{currency}_{username}_{comment}".encode()).hexdigest()[:10]
        
        # Сохраняем данные в базу
        self.db.set(self.name, f"op_{operation_id}", {
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "username": username,
            "comment": comment
        })
        
        return f"lztransfer_confirm_{operation_id}", f"lztransfer_cancel_{operation_id}"
    
    @loader.owner
    async def lzconfigcmd(self, message: Message):
        """Настроить API ключ и секретную фразу"""
        args = utils.get_args_raw(message).split(maxsplit=1)
        
        if len(args) < 2:
            await utils.answer(
                message,
                "<b>🔧 Настройка LolzTransfer</b>\n\n"
                "<code>.lzconfig [API_KEY] [SECRET_PHRASE]</code>"
            )
            return
        
        api_key, secret_phrase = args
        
        self.config["API_KEY"] = api_key.strip()
        self.config["SECRET_PHRASE"] = secret_phrase.strip()
        
        await utils.answer(message, self.strings["config_saved"])
    
    @loader.owner
    async def lztransfercmd(self, message: Message):
        """Перевести деньги пользователю на lolz.live"""
        if not self.config["API_KEY"]:
            await utils.answer(message, self.strings["no_api"])
            return
        
        if not self.config["SECRET_PHRASE"]:
            await utils.answer(message, self.strings["no_secret"])
            return
        
        args = utils.get_args_raw(message).split(maxsplit=3)
        
        if len(args) < 2:
            await utils.answer(message, self.strings["help_text"])
            return
        
        # Парсинг аргументов
        username = args[0]
        
        try:
            amount = float(args[1])
        except ValueError:
            await utils.answer(message, self.strings["invalid_amount"])
            return
        
        currency = args[2] if len(args) > 2 else self.config["DEFAULT_CURRENCY"]
        comment = args[3] if len(args) > 3 else f"Перевод для {username}"
        
        # Отправка сообщения о процессе проверки
        status_msg = await utils.answer(
            message, 
            self.strings["checking_user"].format(username=username)
        )
        
        # Получение ID пользователя
        user_id, profile_url = self.get_user_id(username)
        
        if not user_id:
            await utils.answer(status_msg, self.strings["user_not_found"])
            return
        
        # Генерация данных для callback
        confirm_data, cancel_data = self.generate_callback_data(
            user_id, amount, currency, username, comment
        )
        
        # Создание инлайн-клавиатуры для подтверждения
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                text=self.strings["confirm"],
                callback_data=confirm_data
            ),
            InlineKeyboardButton(
                text=self.strings["cancel"],
                callback_data=cancel_data
            )
        )
        
        # Отправка запроса на подтверждение
        await utils.answer(
            status_msg,
            self.strings["transfer_confirm"].format(
                amount=amount,
                currency=currency.upper(),
                username=username,
                profile_url=profile_url,
                comment=comment
            ),
            reply_markup=keyboard
        )
    
    async def inline_callback_handler(self, query: CallbackQuery):
        """Обработчик колбэков инлайн-клавиатуры"""
        data = query.data
        
        if data.startswith("lztransfer_cancel_"):
            operation_id = data.split("_", 2)[2]
            
            # Удаляем данные операции
            self.db.set(self.name, f"op_{operation_id}", None)
            
            await self.bot.edit_message_text(
                self.strings["operation_cancelled"],
                inline_message_id=query.inline_message_id,
                parse_mode="HTML"
            )
            return
        
        if data.startswith("lztransfer_confirm_"):
            operation_id = data.split("_", 2)[2]
            
            # Получение данных операции
            operation_data = self.db.get(self.name, f"op_{operation_id}")
            
            if not operation_data:
                await self.bot.edit_message_text(
                    "❌ <b>Данные операции устарели или были удалены.</b>",
                    inline_message_id=query.inline_message_id,
                    parse_mode="HTML"
                )
                return
            
            user_id = operation_data["user_id"]
            amount = operation_data["amount"]
            currency = operation_data["currency"]
            username = operation_data["username"]
            comment = operation_data["comment"]
            
            # Перевод денег
            success, error = await self.transfer_money(
                user_id, 
                amount, 
                currency, 
                comment, 
                self.config["SECRET_PHRASE"]
            )
            
            # Удаляем данные операции
            self.db.set(self.name, f"op_{operation_id}", None)
            
            if success:
                await self.bot.edit_message_text(
                    self.strings["transfer_success"].format(
                        amount=amount,
                        currency=currency.upper(),
                        username=username
                    ),
                    inline_message_id=query.inline_message_id,
                    parse_mode="HTML"
                )
            else:
                await self.bot.edit_message_text(
                    self.strings["transfer_error"].format(error=error),
                    inline_message_id=query.inline_message_id,
                    parse_mode="HTML"
                )
    
    async def lztransfer_inline_handler(self, query: InlineQuery):
        """Обработчик инлайн-запросов"""
        query_text = query.query.strip()
        
        # Разбиваем с учетом кавычек для поддержки имен с пробелами
        args = []
        current_arg = ""
        in_quotes = False
        
        for char in query_text:
            if char == '"' and (not current_arg or current_arg[-1] != '\\'):
                in_quotes = not in_quotes
                if not in_quotes and current_arg:
                    args.append(current_arg)
                    current_arg = ""
            elif char == ' ' and not in_quotes:
                if current_arg:
                    args.append(current_arg)
                    current_arg = ""
            else:
                current_arg += char
        
        if current_arg:
            args.append(current_arg)
        
        if len(args) < 3:
            return
        
        command, username, amount_str = args[:3]
        
        if command != "lztransfer":
            return
        
        try:
            amount = float(amount_str)
        except ValueError:
            return
        
        currency = args[3] if len(args) > 3 else self.config["DEFAULT_CURRENCY"]
        comment = " ".join(args[4:]) if len(args) > 4 else f"Перевод для {username}"
        
        # Получение ID пользователя
        user_id, profile_url = self.get_user_id(username)
        
        if not user_id:
            return
        
        # Генерация данных для callback
        confirm_data, cancel_data = self.generate_callback_data(
            user_id, amount, currency, username, comment
        )
        
        # Создание инлайн-результата
        result = InlineQueryResultArticle(
            id=hashlib.md5(f"{username}_{amount}_{currency}".encode()).hexdigest(),
            title=f"Перевести {amount} {currency.upper()} пользователю {username}",
            description=f"Комментарий: {comment}",
            input_message_content=InputTextMessageContent(
                self.strings["transfer_confirm"].format(
                    amount=amount,
                    currency=currency.upper(),
                    username=username,
                    profile_url=profile_url,
                    comment=comment
                ),
                parse_mode="HTML"
            ),
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton(
                    text=self.strings["confirm"],
                    callback_data=confirm_data
                ),
                InlineKeyboardButton(
                    text=self.strings["cancel"],
                    callback_data=cancel_data
                )
            )
        )
        
        await query.answer([result], cache_time=0)
    
    async def helpcmd(self, message: Message):
        """Показать справку по модулю"""
        await utils.answer(message, self.strings["help_text"])
