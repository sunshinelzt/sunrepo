# meta developer: @sunshinelzt

from .. import loader, utils
import requests
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@loader.tds
class LztPayMod(loader.Module):
    """Перевод денег через LZT Market API по нику, ID или Telegram username"""
    
    strings = {
        "name": "LztPay",
        "cfg_doc": "Конфигурация модуля LztPay",
        "cfg_token": "API токен от LZT Market",
        "cfg_currency": "Валюта для переводов (по умолчанию RUB)",
        "cfg_confirm": "Требовать подтверждение перевода",
        "cfg_timeout": "Время ожидания подтверждения (секунды)",
      
        "no_token": (
            "🔐 <b>API токен не установлен</b>\n\n"
            "💡 <i>Установите токен в конфигурации модуля</i>\n"
            "⚙️ <code>.cfg LztPay</code>"
        ),
        "no_args": (
            "❌ <b>Неверные аргументы</b>\n\n"
            "💡 <i>Использование:</i> <code>{prefix}pay &lt;получатель&gt; &lt;сумма&gt; [комментарий]</code>\n\n"
            "📋 <b>Форматы получателя:</b>\n"
            "• <code>nickname</code> - по никнейму\n"
            "• <code>123456</code> - по ID пользователя\n"
            "• <code>@username</code> - по Telegram username"
        ),
        "invalid_amount": (
            "❌ <b>Неверная сумма</b>\n\n"
            "💡 <i>Сумма должна быть положительным числом</i>"
        ),
        "user_not_found": (
            "❌ <b>Пользователь не найден</b>\n\n"
            "🔍 <i>Проверьте правильность данных получателя</i>"
        ),
        "api_error": (
            "❌ <b>Ошибка API LZT Market</b>\n\n"
            "📋 <b>Детали:</b> <code>{error}</code>\n"
            "🔄 <i>Попробуйте позже или проверьте токен</i>"
        ),
        "network_error": (
            "🌐 <b>Ошибка сети</b>\n\n"
            "📡 <i>Проверьте подключение к интернету</i>"
        ),
        "insufficient_balance": (
            "💳 <b>Недостаточно средств</b>\n\n"
            "💰 <i>Пополните баланс на LZT Market</i>"
        ),
        
        "transfer_success": (
            "🎉 <b>Перевод выполнен успешно!</b>\n\n"
            "💰 <b>Сумма:</b> <code>{amount} {currency}</code>\n"
            "👤 <b>Получатель:</b> {username}\n"
            "💬 <b>Комментарий:</b> <i>{comment}</i>\n\n"
            "✨ <i>Средства успешно переведены!</i>"
        ),
        
        "processing": (
            "⏳ <b>Обработка запроса...</b>\n\n"
            "🔍 <i>Поиск пользователя и валидация данных</i>"
        ),
        "executing": (
            "💳 <b>Выполнение перевода...</b>\n\n"
            "⚡ <i>Отправка запроса в LZT Market API</i>"
        ),
        
        "confirm_transfer": (
            "💸 <b>Подтверждение перевода</b>\n\n"
            "💰 <b>Сумма:</b> <code>{amount} {currency}</code>\n"
            "👤 <b>Получатель:</b> {username}\n"
            "💬 <b>Комментарий:</b> <i>{comment}</i>\n\n"
            "❓ <b>Подтвердить операцию?</b>"
        ),
        "transfer_cancelled": (
            "❌ <b>Перевод отменен</b>\n\n"
            "💭 <i>Операция отменена пользователем</i>"
        ),
        "transfer_timeout": (
            "⏰ <b>Время ожидания истекло</b>\n\n"
            "💭 <i>Перевод автоматически отменен</i>"
        ),
        
        #"module_info": (
            #"💸 <b>LztPay</b>\n\n"
            #"📋 <b>Возможности:</b>\n"
            #"• Переводы по никнейму, ID, Telegram\n"
            #"• Подтверждение операций\n"
            #"• Детальная обработка ошибок\n"
            #"• Гибкие настройки\n\n"
            #"⚙️ <i>Настройка:</i> <code>{prefix}cfg LztPay</code>"
        ),
    }
    
    def __init__(self):
        """Инициализация модуля"""
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token",
                "",
                lambda: "API токен от LZT Market для выполнения переводов",
                validator=loader.validators.Hidden()
            ),
            loader.ConfigValue(
                "default_currency",
                "RUB",
                lambda: "Валюта по умолчанию для переводов",
                validator=loader.validators.Choice(["RUB", "USD", "EUR", "UAH"])
            ),
            loader.ConfigValue(
                "require_confirmation",
                True,
                lambda: "Требовать подтверждение перед выполнением перевода"
            ),
            loader.ConfigValue(
                "confirmation_timeout",
                300,
                lambda: "Время ожидания подтверждения в секундах",
                validator=loader.validators.Integer(minimum=30, maximum=1800)
            ),
            loader.ConfigValue(
                "default_comment",
                "Перевод через LztPay",
                lambda: "Комментарий по умолчанию для переводов"
            )
        )
        
        self._api_url = "https://prod-api.lzt.market/balance/transfer"
        self._lookup_url = "https://prod-api.lolz.live/users/find"
        self._profile_url = "https://lolz.live/members/{}"
        
        self._pending_transfers: Dict[str, Dict[str, Any]] = {}

    async def client_ready(self, client, db):
        """Вызывается при готовности клиента"""
        self._client = client
        self._db = db

    # ==================== ОСНОВНЫЕ КОМАНДЫ ====================
    
    async def paycmd(self, message):
        """Перевести деньги: .pay <получатель> <сумма> [комментарий]"""
        if not self.config["api_token"]:
            await utils.answer(message, self.strings("no_token"))
            return
        
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message, 
                self.strings("no_args").format(prefix=self.get_prefix())
            )
            return
        
        parsed_args = args.split()
        if len(parsed_args) < 2:
            await utils.answer(
                message, 
                self.strings("no_args").format(prefix=self.get_prefix())
            )
            return
        
        recipient = parsed_args[0]
        amount = self._validate_amount(parsed_args[1])
        
        if amount is None:
            await utils.answer(message, self.strings("invalid_amount"))
            return
            
        comment = " ".join(parsed_args[2:]) if len(parsed_args) > 2 else self.config["default_comment"]
        
        await utils.answer(message, self.strings("processing"))
        
        try:
            user_data = await self._find_user(recipient)
            if not user_data:
                await utils.answer(message, self.strings("user_not_found"))
                return
                
            transfer_data = self._prepare_transfer_data(user_data, amount, comment)
            
            if self.config["require_confirmation"]:
                await self._show_confirmation(message, transfer_data)
            else:
                await self._execute_transfer(message, transfer_data)
                
        except Exception as e:
            logger.error(f"Ошибка при выполнении перевода: {e}")
            await utils.answer(message, self.strings("api_error").format(error=str(e)))

    #async def lztinfocmd(self, message):
        #"""Информация о модуле LztPay"""
        #await utils.answer(
            #message,
            #self.strings("module_info").format(prefix=self.get_prefix())
         )

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def _validate_amount(self, amount_str: str) -> Optional[int]:
        """Валидация суммы перевода"""
        try:
            amount = int(amount_str)
            return amount if amount > 0 else None
        except ValueError:
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Получение заголовков для API запросов"""
        return {
            "Authorization": f"Bearer {self.config['api_token']}",
            "Content-Type": "application/json",
            "User-Agent": "LztPay-Sunshine/2.0"
        }
    
    async def _find_user(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Поиск пользователя по различным идентификаторам"""
        headers = self._get_headers()
        
        if user_input.isdigit():
            return {
                'user_id': int(user_input),
                'username': f"ID: {user_input}",
                'display_name': f"<b>ID: {user_input}</b>",
                'type': 'id'
            }
        
        if user_input.startswith("@"):
            telegram_username = user_input[1:]
            return await self._find_by_telegram(telegram_username, headers)
        
        return await self._find_by_username(user_input, headers)
    
    async def _find_by_telegram(self, telegram_username: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Поиск пользователя по Telegram username"""
        try:
            url = f"{self._lookup_url}?custom_fields[telegram]={telegram_username}"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            users = data.get('users', [])
            
            if not users:
                return None
                
            user = users[0]
            user_id = user['user_id']
            username = user.get('username', f"@{telegram_username}")
            
            return {
                'user_id': user_id,
                'username': username,
                'display_name': f"<a href='{self._profile_url.format(user_id)}'>{username}</a>",
                'type': 'telegram'
            }
            
        except Exception as e:
            logger.error(f"Ошибка поиска по Telegram: {e}")
            raise
    
    async def _find_by_username(self, username: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Поиск пользователя по никнейму"""
        try:
            url = f"{self._lookup_url}?username={username}"
            response = requests.get(url, headers=headers, timeout=15)
            
            user_data = {
                'username': username,
                'display_name': f"<b>{username}</b>",
                'type': 'username'
            }
            
            if response.status_code == 200:
                data = response.json()
                users = data.get('users', [])
                if users:
                    user_id = users[0]['user_id']
                    user_data.update({
                        'user_id': user_id,
                        'display_name': f"<a href='{self._profile_url.format(user_id)}'>{username}</a>"
                    })
            
            return user_data
            
        except Exception as e:
            logger.error(f"Ошибка поиска по никнейму: {e}")
            raise
    
    def _prepare_transfer_data(self, user_data: Dict[str, Any], amount: int, comment: str) -> Dict[str, Any]:
        """Подготовка данных для перевода"""
        payload = {
            "amount": amount,
            "comment": comment,
            "currency": self.config["default_currency"]
        }
        
        if 'user_id' in user_data:
            payload['user_id'] = user_data['user_id']
        else:
            payload['username'] = user_data['username']
        
        return {
            'payload': payload,
            'headers': self._get_headers(),
            'amount': amount,
            'currency': self.config["default_currency"],
            'username': user_data['display_name'],
            'comment': comment,
            'user_data': user_data
        }
    
    async def _show_confirmation(self, message, transfer_data: Dict[str, Any]):
        """Показ формы подтверждения перевода"""
        transfer_id = f"{message.chat.id}_{message.id}_{asyncio.get_event_loop().time()}"
        self._pending_transfers[transfer_id] = transfer_data
        
        confirm_text = self.strings("confirm_transfer").format(
            amount=transfer_data['amount'],
            currency=transfer_data['currency'],
            username=transfer_data['username'],
            comment=transfer_data['comment']
        )
        
        await self.inline.form(
            text=confirm_text,
            message=message,
            reply_markup=[
                [
                    {
                        "text": "✅ Подтвердить",
                        "callback": self._confirm_transfer,
                        "args": (transfer_id,)
                    },
                    {
                        "text": "❌ Отменить", 
                        "callback": self._cancel_transfer,
                        "args": (transfer_id,)
                    }
                ]
            ]
        )
        
        asyncio.create_task(
            self._cleanup_transfer(transfer_id, self.config["confirmation_timeout"])
        )
    
    async def _execute_transfer(self, message_or_call, transfer_data: Dict[str, Any]):
        """Выполнение перевода"""
        if hasattr(message_or_call, 'edit'):
            await message_or_call.edit(self.strings("executing"))
        else:
            await utils.answer(message_or_call, self.strings("executing"))
        
        try:
            response = requests.post(
                self._api_url,
                json=transfer_data['payload'],
                headers=transfer_data['headers'],
                timeout=30
            )
            
            if response.status_code == 200:
                success_message = self.strings("transfer_success").format(
                    amount=transfer_data['amount'],
                    currency=transfer_data['currency'],
                    username=transfer_data['username'],
                    comment=transfer_data['comment']
                )
                
                if hasattr(message_or_call, 'edit'):
                    await message_or_call.edit(success_message)
                else:
                    await utils.answer(message_or_call, success_message)
                    
                logger.info(f"Успешный перевод: {transfer_data['amount']} {transfer_data['currency']}")
                
            else:
                data = response.json()
                error_text = self._format_api_error(data)
                
                if hasattr(message_or_call, 'edit'):
                    await message_or_call.edit(self.strings("api_error").format(error=error_text))
                else:
                    await utils.answer(message_or_call, self.strings("api_error").format(error=error_text))
                    
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при переводе: {e}")
            error_msg = self.strings("network_error")
            
            if hasattr(message_or_call, 'edit'):
                await message_or_call.edit(error_msg)
            else:
                await utils.answer(message_or_call, error_msg)
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка при переводе: {e}")
            
            if hasattr(message_or_call, 'edit'):
                await message_or_call.edit(self.strings("api_error").format(error=str(e)))
            else:
                await utils.answer(message_or_call, self.strings("api_error").format(error=str(e)))
    
    def _format_api_error(self, data: Dict[str, Any]) -> str:
        """Форматирование ошибки API"""
        if 'errors' in data:
            errors = data['errors']
            if isinstance(errors, dict):
                return "; ".join([f"{k}: {v}" for k, v in errors.items()])
            elif isinstance(errors, list):
                return "; ".join(str(e) for e in errors)
            else:
                return str(errors)
        elif 'message' in data:
            return data['message']
        else:
            return str(data)
    
    async def _cleanup_transfer(self, transfer_id: str, timeout: int):
        """Автоматическая очистка данных о переводе"""
        await asyncio.sleep(timeout)
        if transfer_id in self._pending_transfers:
            del self._pending_transfers[transfer_id]
    
    # ==================== CALLBACK ОБРАБОТЧИКИ ====================
    
    async def _confirm_transfer(self, call, transfer_id: str):
        """Подтверждение перевода"""
        if transfer_id not in self._pending_transfers:
            await call.edit(self.strings("transfer_timeout"))
            return
        
        transfer_data = self._pending_transfers[transfer_id]
        await self._execute_transfer(call, transfer_data)
        
        if transfer_id in self._pending_transfers:
            del self._pending_transfers[transfer_id]
    
    async def _cancel_transfer(self, call, transfer_id: str):
        """Отмена перевода"""
        if transfer_id not in self._pending_transfers:
            await call.edit(self.strings("transfer_timeout"))
            return
        
        await call.edit(self.strings("transfer_cancelled"))
        
        if transfer_id in self._pending_transfers:
            del self._pending_transfers[transfer_id]
