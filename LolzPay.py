# -*- coding: utf-8 -*-
# meta developer: @sunshinelzt

"""
   _____ __  ___   _______ __  _______   __________ _____ ______
  / ___// / / / | / / ___// / / /  _/ | / / ____/ //__  //_  __/
  \__ \/ / / /  |/ /\__ \/ /_/ // //  |/ / __/ / /   / /  / /   
 ___/ / /_/ / /|  /___/ / __  // // /|  / /___/ /___/ /__/ /    
/____/\____/_/ |_//____/_/ /_/___/_/ |_/_____/_____/____/_/     
                                                                

    Name: LolzPay
    Developer: @sunshinelzt
    Commands: .pay, .balance
    Version: 1.0.0 (Heroku Edition)
    
"""

__version__ = (1, 0, 0)

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Tuple, Union

import aiohttp
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Исключение для ошибок API"""
    pass


class UserNotFoundError(APIError):
    """Исключение для случая, когда пользователь не найден"""
    pass


class InsufficientFundsError(APIError):
    """Исключение для недостатка средств"""
    pass


class RateLimitError(APIError):
    """Исключение для превышения лимита запросов"""
    pass


@loader.tds
class LolzPayMod(loader.Module):
    """Переводы денег через Lolzteam API"""

    strings = {
        "name": "LolzPay",
        "cfg_api_key": "Ваш API ключ от Lolzteam Market",
        "cfg_confirm": "Показывать диалог подтверждения перед переводом",
        "cfg_show_balance": "Показывать баланс после перевода",
        "cfg_min_amount": "Минимальная сумма для перевода",
        "cfg_max_amount": "Максимальная сумма для перевода",
        
        "no_api_key": (
            "🔐 <b>API ключ не настроен!</b>\n\n"
            "📋 <i>Для получения ключа:</i>\n"
            "1️⃣ Перейдите на <a href=\"https://lolz.live/account/api\">lolz.live/account/api</a>\n"
            "2️⃣ Создайте новый токен\n"
            "3️⃣ Укажите его в конфигурации модуля\n\n"
            "⚙️ <code>.config LolzPay</code>"
        ),
        
        "invalid_args": (
            "📝 <b>Использование команды:</b>\n\n"
            "💡 <code>.pay [сумма] [получатель] [комментарий]</code>\n\n"
            "🔹 <b>Примеры:</b>\n"
            "• <code>.pay 100 username</code>\n"
            "• <code>.pay 50.5 @telegram_nick</code>\n"
            "• <code>.pay 25 user За отличную работу</code>\n\n"
            "ℹ️ <i>Получатель может быть указан как ник Lolz или Telegram (@nick)</i>"
        ),
        
        "invalid_amount": (
            "❌ <b>Неверная сумма:</b> <code>{amount}</code>\n\n"
            "💰 <b>Допустимый диапазон:</b> <code>{min} - {max} ₽</code>\n"
            "💡 <i>Используйте точку или запятую для дробных чисел</i>"
        ),
        
        "searching": "🔍 <b>Поиск получателя...</b>\n⏳ <i>Обрабатываем запрос</i>",
        "user_not_found": (
            "❌ <b>Пользователь не найден:</b> <code>{user}</code>\n\n"
            "💡 <b>Проверьте:</b>\n"
            "• Правильность написания ника\n"
            "• Существование пользователя на Lolz\n"
            "• Указание @ для Telegram никнеймов"
        ),
        
        "processing": "⚡ <b>Обработка перевода...</b>\n💸 <i>Выполняем транзакцию</i>",
        
        "rate_limit": (
            "⏰ <b>Превышен лимит запросов</b>\n\n"
            "🕐 <b>Подождите:</b> <code>{seconds} сек.</code>\n"
            "💡 <i>Попробуйте повторить команду позже</i>"
        ),
        
        "insufficient_funds": (
            "💳 <b>Недостаточно средств!</b>\n\n"
            "💰 <b>Ваш баланс:</b> <code>{balance}</code>\n"
            "📊 <i>Пополните баланс для продолжения</i>"
        ),
        
        "api_error": (
            "⚠️ <b>Ошибка API Lolzteam:</b>\n\n"
            "🔴 <code>{error}</code>\n\n"
            "💡 <i>Если ошибка повторяется, обратитесь к администрации</i>"
        ),
        
        "network_error": (
            "🌐 <b>Ошибка подключения</b>\n\n"
            "🔧 <b>Возможные причины:</b>\n"
            "• Проблемы с интернетом\n"
            "• Временная недоступность API\n"
            "• Неверные настройки прокси\n\n"
            "🔄 <i>Попробуйте повторить позже</i>"
        ),
        
        "confirm_transfer": (
            "💸 <b>Подтверждение перевода</b>\n\n"
            "💰 <b>Сумма:</b> <code>{amount}</code>\n"
            "👤 <b>Получатель:</b> {recipient}\n"
            "{comment_line}\n"
            "⚠️ <i>Проверьте данные перед подтверждением!</i>"
        ),
        
        "confirm_transfer_with_balance": (
            "💸 <b>Подтверждение перевода</b>\n\n"
            "💰 <b>Сумма:</b> <code>{amount}</code>\n"
            "👤 <b>Получатель:</b> {recipient}\n"
            "{comment_line}"
            "💳 <b>Ваш баланс:</b> <code>{balance}</code>\n"
            "📊 <b>Останется:</b> <code>{remaining}</code>\n\n"
            "⚠️ <i>Проверьте данные перед подтверждением!</i>"
        ),
        
        "comment_line": "💬 <b>Комментарий:</b> <i>{comment}</i>\n",
        
        "success": (
            "✅ <b>Перевод выполнен успешно!</b>\n\n"
            "💰 <b>Сумма:</b> <code>{amount}</code>\n"
            "👤 <b>Получатель:</b> {recipient}\n"
            "{comment_line}"
            "{balance_line}"
            "🕐 <b>Время:</b> <code>{time}</code>"
        ),
        
        "balance_line": "💳 <b>Новый баланс:</b> <code>{balance}</code>\n",
        "cancelled": "❌ <b>Перевод отменен</b>",
        
        "balance_info": "💰 <b>Ваш баланс:</b> <code>{balance}</code>",
        "balance_error": "❌ <b>Не удалось получить баланс</b>",
        "getting_balance": "💰 <b>Получаем баланс...</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                lambda: self.strings["cfg_api_key"],
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "confirm_transfers",
                True,
                lambda: self.strings["cfg_confirm"],
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "show_balance",
                True,
                lambda: self.strings["cfg_show_balance"],
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "min_amount",
                1.0,
                lambda: self.strings["cfg_min_amount"],
                validator=loader.validators.Float(minimum=1.0),
            ),
            loader.ConfigValue(
                "max_amount",
                1000000.0,
                lambda: self.strings["cfg_max_amount"],
                validator=loader.validators.Float(minimum=1.0),
            ),
        )
        
        self._api_base = "https://api.lzt.market"
        self._forum_api = "https://api.lolz.live"
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request = 0.0
        self._rate_limit_delay = 0.5
        
    async def client_ready(self):
        """Инициализация модуля"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            headers={
                "User-Agent": "SunshineLZT-LolzPay/2.2-Heroku",
                "Accept": "application/json",
            }
        )
        
    async def on_unload(self):
        """Очистка при выгрузке"""
        if self._session:
            await self._session.close()

    def _format_user_display(self, user_data: Dict, search_query: str) -> str:
        """Форматирует отображение пользователя"""
        username = user_data.get("username", "Unknown")
        
        telegram_username = None
        for field in user_data.get("fields", []):
            if field.get("id") == "telegram" and field.get("value"):
                telegram_username = field.get("value").replace("@", "")
                break
        
        profile_link = user_data.get("links", {}).get("permalink")
        
        if profile_link:
            display = f'<a href="{profile_link}">{username}</a>'
        else:
            display = f"<code>{username}</code>"
        
        if telegram_username and not search_query.startswith("@"):
            display += f" (@{telegram_username})"
        
        return display

    def _format_amount(self, amount: float) -> str:
        """Форматирует сумму"""
        if amount == int(amount):
            return f"{int(amount)} ₽"
        else:
            return f"{amount:.2f}".rstrip('0').rstrip('.') + " ₽"

    async def _make_request(
        self, method: str, url: str, **kwargs
    ) -> Tuple[bool, Union[Dict, str]]:
        """Выполняет HTTP запрос с обработкой ошибок"""
        if not self._session:
            return False, "Session not initialized"
        
        now = time.time()
        if now - self._last_request < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - (now - self._last_request))
        
        headers = kwargs.pop("headers", {})
        if self.config["api_key"]:
            headers["Authorization"] = f"Bearer {self.config['api_key']}"
        
        try:
            async with self._session.request(method, url, headers=headers, **kwargs) as resp:
                self._last_request = time.time()
                
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        return True, data
                    except Exception:
                        text = await resp.text()
                        return True, text
                
                elif resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    raise RateLimitError(f"Rate limit exceeded, retry after {retry_after}s")
                
                else:
                    try:
                        error_data = await resp.json()
                        if "errors" in error_data:
                            errors = error_data["errors"]
                            if isinstance(errors, list) and errors:
                                error_msg = str(errors[0])
                            else:
                                error_msg = str(errors)
                        else:
                            error_msg = error_data.get("message", f"HTTP {resp.status}")
                    except Exception:
                        error_msg = f"HTTP {resp.status}"
                    
                    if "недостаточно средств" in error_msg.lower():
                        raise InsufficientFundsError(error_msg)
                    elif "пользователь не найден" in error_msg.lower():
                        raise UserNotFoundError(error_msg)
                    elif "подождать" in error_msg.lower():
                        match = re.search(r"(\d+)\s*секунд", error_msg)
                        seconds = int(match.group(1)) if match else 60
                        raise RateLimitError(f"Необходимо подождать {seconds} секунд")
                    else:
                        raise APIError(error_msg)
        
        except (RateLimitError, InsufficientFundsError, UserNotFoundError, APIError):
            raise
        except Exception as e:
            logger.exception("Network request failed")
            return False, f"Network error: {str(e)}"

    async def _get_balance(self) -> Optional[float]:
        """Получает текущий баланс"""
        try:
            success, data = await self._make_request("GET", f"{self._api_base}/me")
            if success and isinstance(data, dict):
                return float(data.get("user", {}).get("balance", 0))
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
        return None

    async def _find_user(self, query: str) -> Optional[Dict]:
        """Поиск пользователя по нику или Telegram с улучшенной обработкой"""
        try:
            # Сначала пробуем точный поиск
            if query.startswith("@"):
                tg_username = query[1:]
                params = {"custom_fields[telegram]": tg_username}
            else:
                params = {"username": query}
            
            success, data = await self._make_request(
                "GET", f"{self._forum_api}/users/find", params=params
            )
            
            if success and isinstance(data, dict):
                users = data.get("users", [])
                if users:
                    return users[0]
            
            if not query.startswith("@"):
                if query.islower():
                    capitalized_query = query.capitalize()
                    params = {"username": capitalized_query}
                    
                    success, data = await self._make_request(
                        "GET", f"{self._forum_api}/users/find", params=params
                    )
                    
                    if success and isinstance(data, dict):
                        users = data.get("users", [])
                        if users:
                            return users[0]
                
                # Пробуем полностью в нижнем регистре
                if not query.islower():
                    lower_query = query.lower()
                    params = {"username": lower_query}
                    
                    success, data = await self._make_request(
                        "GET", f"{self._forum_api}/users/find", params=params
                    )
                    
                    if success and isinstance(data, dict):
                        users = data.get("users", [])
                        if users:
                            return users[0]
            
            return None
            
        except UserNotFoundError:
            return None
        except Exception as e:
            logger.error(f"User search failed: {e}")
            return None

    async def _transfer_money(
        self, amount: float, username: str, comment: str = ""
    ) -> Dict:
        """Выполняет перевод денег"""
        params = {
            "username": username,
            "amount": amount,
            "currency": "rub"
        }
        
        if comment.strip():
            params["comment"] = comment.strip()
        
        success, result = await self._make_request(
            "POST", f"{self._api_base}/balance/transfer", params=params
        )
        
        if not success:
            raise APIError(result)
        
        return result

    def _validate_amount(self, amount_str: str) -> Tuple[bool, Optional[float], str]:
        """Валидирует сумму перевода"""
        try:
            amount_str = amount_str.replace(",", ".").replace(" ", "")
            amount = float(amount_str)
            
            min_amount = self.config["min_amount"]
            max_amount = self.config["max_amount"]
            
            if amount < min_amount or amount > max_amount:
                return False, None, self.strings["invalid_amount"].format(
                    amount=amount_str, min=min_amount, max=max_amount
                )
            
            return True, amount, ""
            
        except ValueError:
            return False, None, self.strings["invalid_amount"].format(
                amount=amount_str, 
                min=self.config["min_amount"], 
                max=self.config["max_amount"]
            )

    @loader.command()
    async def paycmd(self, message: Message):
        """[сумма] [получатель] [комментарий] - Перевести деньги через Lolzteam"""
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return
        
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["invalid_args"])
            return
        
        parts = args.split(None, 2)
        if len(parts) < 2:
            await utils.answer(message, self.strings["invalid_args"])
            return
        
        amount_str, recipient = parts[0], parts[1]
        comment = parts[2] if len(parts) > 2 else ""
        
        valid, amount, error = self._validate_amount(amount_str)
        if not valid:
            await utils.answer(message, error)
            return
        
        try:
            await utils.answer(message, self.strings["searching"])
            
            user_data = await self._find_user(recipient)
            if not user_data:
                await utils.answer(
                    message, 
                    self.strings["user_not_found"].format(user=recipient)
                )
                return
            
            recipient_username = user_data.get("username")
            recipient_display = self._format_user_display(user_data, recipient)
            
            if self.config["confirm_transfers"]:
                comment_line = ""
                if comment:
                    comment_line = self.strings["comment_line"].format(comment=comment)
                
                if self.config["show_balance"]:
                    balance = await self._get_balance()
                    if balance is None:
                        await utils.answer(message, self.strings["network_error"])
                        return
                    
                    if balance < amount:
                        await utils.answer(
                            message,
                            self.strings["insufficient_funds"].format(
                                balance=self._format_amount(balance)
                            )
                        )
                        return
                    
                    confirm_text = self.strings["confirm_transfer_with_balance"].format(
                        amount=self._format_amount(amount),
                        recipient=recipient_display,
                        comment_line=comment_line,
                        balance=self._format_amount(balance),
                        remaining=self._format_amount(balance - amount)
                    )
                else:
                    confirm_text = self.strings["confirm_transfer"].format(
                        amount=self._format_amount(amount),
                        recipient=recipient_display,
                        comment_line=comment_line
                    )
                
                await self.inline.form(
                    message=message,
                    text=confirm_text,
                    reply_markup=[
                        [
                            {
                                "text": "✅ Подтвердить",
                                "callback": self._confirm_transfer,
                                "args": (amount, recipient_username, comment, recipient_display),
                            },
                            {
                                "text": "❌ Отмена", 
                                "callback": self._cancel_transfer,
                            },
                        ]
                    ],
                )
            else:
                await self._execute_transfer(
                    message, amount, recipient_username, comment, recipient_display
                )
                
        except RateLimitError as e:
            match = re.search(r"(\d+)", str(e))
            seconds = int(match.group(1)) if match else 60
            
            await utils.answer(
                message,
                self.strings["rate_limit"].format(seconds=seconds)
            )
            
        except InsufficientFundsError:
            balance = await self._get_balance() or 0
            await utils.answer(
                message,
                self.strings["insufficient_funds"].format(
                    balance=self._format_amount(balance)
                )
            )
            
        except UserNotFoundError:
            await utils.answer(
                message,
                self.strings["user_not_found"].format(user=recipient)
            )
            
        except APIError as e:
            await utils.answer(
                message,
                self.strings["api_error"].format(error=str(e))
            )
            
        except Exception as e:
            logger.exception("Transfer failed")
            await utils.answer(message, self.strings["network_error"])

    async def _confirm_transfer(self, call, amount, recipient, comment, recipient_display):
        """Подтверждение перевода"""
        await call.edit(self.strings["processing"])
        
        try:
            await self._execute_transfer(
                call, amount, recipient, comment, recipient_display
            )
        except Exception as e:
            logger.exception("Transfer execution failed")
            await call.edit(self.strings["network_error"])

    async def _cancel_transfer(self, call):
        """Отмена перевода"""
        await call.edit(self.strings["cancelled"])

    async def _execute_transfer(
        self, message_or_call, amount, recipient, comment, recipient_display
    ):
        """Выполняет перевод денег"""
        try:
            await self._transfer_money(amount, recipient, comment)
            
            comment_line = ""
            if comment:
                comment_line = self.strings["comment_line"].format(comment=comment)
            
            balance_line = ""
            if self.config["show_balance"]:
                new_balance = await self._get_balance()
                if new_balance is not None:
                    balance_line = self.strings["balance_line"].format(
                        balance=self._format_amount(new_balance)
                    )
            
            success_text = self.strings["success"].format(
                amount=self._format_amount(amount),
                recipient=recipient_display,
                comment_line=comment_line,
                balance_line=balance_line,
                time=time.strftime("%H:%M:%S")
            )
            
            if hasattr(message_or_call, 'edit'):
                await message_or_call.edit(success_text)
            else:
                await utils.answer(message_or_call, success_text)
                
        except Exception as e:
            error_text = self.strings["api_error"].format(error=str(e))
            
            if hasattr(message_or_call, 'edit'):
                await message_or_call.edit(error_text)
            else:
                await utils.answer(message_or_call, error_text)

    @loader.command()
    async def balancecmd(self, message: Message):
        """Показать баланс"""
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return
        
        await utils.answer(message, self.strings["getting_balance"])
        
        try:
            balance = await self._get_balance()
            if balance is not None:
                await utils.answer(
                    message,
                    self.strings["balance_info"].format(
                        balance=self._format_amount(balance)
                    )
                )
            else:
                await utils.answer(message, self.strings["balance_error"])
                
        except APIError as e:
            await utils.answer(
                message,
                self.strings["api_error"].format(error=str(e))
            )
        except Exception as e:
            logger.exception("Balance check failed")
            await utils.answer(message, self.strings["network_error"])
