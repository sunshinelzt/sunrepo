# meta developer: @sunshinelzt

from .. import loader, utils
import requests
import asyncio
import logging


@loader.tds
class LztPayMod(loader.Module):
    """Перевод денег через LZT Market API по нику, ID или Telegram username"""
    
    strings = {
        "name": "LztPay",
        
        # Ошибки и предупреждения
        "no_token": (
            "❌ <b>Токен не установлен</b>\n\n"
            "💡 <i>Установите токен в конфигурации модуля</i>"
        ),
        "no_args": (
            "❌ <b>Неверные аргументы</b>\n\n"
            "💡 <i>Пример:</i> <code>.pay Ceyser 100 [коммент]</code>"
        ),
        "invalid_amount": (
            "❌ <b>Неверная сумма</b>\n\n"
            "💡 <i>Сумма должна быть положительным числом</i>"
        ),
        "not_found": (
            "❌ <b>Пользователь не найден</b>\n\n"
            "🔍 Проверьте правильность ника/ID"
        ),
        "fail": (
            "❌ <b>Ошибка перевода</b>\n\n"
            "📋 <b>Детали:</b>\n<code>{}</code>"
        ),
        "api_error": (
            "❌ <b>Ошибка API запроса</b>\n\n"
            "🔗 <b>URL:</b> <code>{url}</code>\n"
            "📊 <b>Статус:</b> <code>{status}</code>\n"
            "📋 <b>Ошибка:</b> <code>{error}</code>"
        ),
        
        # Успешные операции
        "success": (
            "✅ <b>Перевод выполнен успешно!</b>\n\n"
            "💰 <b>Сумма:</b> <code>{amount} {currency}</code>\n"
            "👤 <b>Получатель:</b> {username}\n"
            "💬 <b>Комментарий:</b> <i>{comment}</i>\n\n"
            "🎉 <i>Средства успешно переведены!</i>"
        ),
        
        # Статусы процесса
        "processing": (
            "⏳ <b>Обработка данных...</b>\n\n"
            "🔍 Поиск пользователя и проверка данных"
        ),
        "executing_transfer": (
            "⏳ <b>Выполнение перевода...</b>\n\n"
            "💳 <i>Обработка платежа</i>"
        ),
        
        # Подтверждение
        "confirm": (
            "💸 <b>Подтверждение перевода</b>\n\n"
            "💰 <b>Сумма:</b> <code>{amount} {currency}</code>\n"
            "👤 <b>Получатель:</b> {username}\n"
            "💬 <b>Комментарий:</b> <i>{comment}</i>\n\n"
            "❓ <b>Подтвердить перевод?</b>"
        ),
        "cancelled": (
            "❌ <b>Перевод отменен</b>\n\n"
            "💭 <i>Операция отменена пользователем</i>"
        ),
        "timeout": (
            "⏰ <b>Время ожидания истекло</b>\n\n"
            "💭 <i>Перевод автоматически отменен</i>"
        ),
        
        # Информация о балансе
        "balance_info": (
            "💰 <b>Информация о балансе</b>\n\n"
            "💵 <b>Баланс:</b> <code>{balance} {currency}</code>\n"
            "👤 <b>Пользователь:</b> {username}\n"
            "🆔 <b>ID:</b> <code>{user_id}</code>"
        ),
        "balance_error": (
            "❌ <b>Не удалось получить информацию о балансе</b>\n\n"
            "🔍 Проверьте токен и подключение к интернету"
        ),
        
        # Конфигурация
        "cfg_doc_token": "API токен от LZT Market",
        "cfg_doc_currency": "Валюта для переводов (RUB, USD, EUR)",
        "cfg_doc_confirm": "Требовать подтверждение перед переводом",
        "cfg_doc_timeout": "Время ожидания подтверждения (секунды)",
        "cfg_doc_default_comment": "Комментарий по умолчанию для переводов",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token",
                "",
                lambda: self.strings("cfg_doc_token"),
                validator=loader.validators.Hidden()
            ),
            loader.ConfigValue(
                "currency",
                "RUB",
                lambda: self.strings("cfg_doc_currency"),
                validator=loader.validators.Choice(["RUB", "USD", "EUR"])
            ),
            loader.ConfigValue(
                "require_confirmation",
                True,
                lambda: self.strings("cfg_doc_confirm"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "confirmation_timeout",
                300,
                lambda: self.strings("cfg_doc_timeout"),
                validator=loader.validators.Integer(minimum=30, maximum=600)
            ),
            loader.ConfigValue(
                "default_comment",
                "Перевод через LztPay",
                lambda: self.strings("cfg_doc_default_comment"),
                validator=loader.validators.String()
            ),
        )
        
        # Константы API
        self.api_url = "https://prod-api.lzt.market/balance/transfer"
        self.lookup_url = "https://prod-api.lolz.live/users/find"
        self.balance_url = "https://prod-api.lzt.market/balance"
        self.profile_url = "https://lolz.live/members/{}"
        
        # Состояние модуля
        self.pending_transfers = {}
        self.logger = logging.getLogger(__name__)

    async def client_ready(self, client, db):
        """Инициализация после готовности клиента"""
        self.client = client
        self.db = db

    async def paycmd(self, message):
        """Перевести деньги: .pay <ник/ID/@telegram> <amount> [комментарий]"""
        # Проверка токена
        if not self.config["api_token"]:
            await utils.answer(message, self.strings("no_token"))
            return
        
        # Проверка аргументов
        args = utils.get_args(message)
        if len(args) < 2:
            await utils.answer(message, self.strings("no_args"))
            return
        
        # Парсинг аргументов
        user = args[0]
        amount = self._parse_amount(args[1])
        if amount is None:
            await utils.answer(message, self.strings("invalid_amount"))
            return
            
        comment = " ".join(args[2:]) if len(args) > 2 else self.config["default_comment"]
        
        # Показываем статус обработки
        await utils.answer(message, self.strings("processing"))
        
        # Подготовка данных для API
        headers = self._get_headers()
        payload = self._create_base_payload(amount, comment)
        
        # Получение информации о пользователе
        user_info = await self._resolve_user(user, headers, payload)
        if user_info is None:
            await utils.answer(message, self.strings("not_found"))
            return
        
        # Форматирование имени пользователя
        formatted_username = self._format_username(user_info['username'], user_info.get('user_id'))
        
        # Проверка необходимости подтверждения
        if self.config["require_confirmation"]:
            # Создание данных для подтверждения
            transfer_id = self._generate_transfer_id(message)
            
            self.pending_transfers[transfer_id] = {
                'payload': payload,
                'headers': headers,
                'amount': amount,
                'username': formatted_username,
                'comment': comment,
                'user_id': user_info.get('user_id'),
                'message': message
            }
            
            # Показываем форму подтверждения
            await self._show_confirmation_form(message, transfer_id, amount, formatted_username, comment)
            
            # Автоматическая очистка через таймаут
            asyncio.create_task(self._cleanup_transfer(transfer_id, self.config["confirmation_timeout"]))
        else:
            # Выполняем перевод без подтверждения
            await self._execute_transfer(message, payload, headers, amount, formatted_username, comment)

    async def balancecmd(self, message):
        """Показать информацию о балансе: .balance"""
        if not self.config["api_token"]:
            await utils.answer(message, self.strings("no_token"))
            return
        
        headers = self._get_headers()
        
        try:
            response = requests.get(self.balance_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                balance = data.get('balance', 0)
                user_info = data.get('user', {})
                username = user_info.get('username', 'Неизвестно')
                user_id = user_info.get('user_id', 'Неизвестно')
                
                balance_text = self.strings("balance_info").format(
                    balance=balance,
                    currency=self.config["currency"],
                    username=username,
                    user_id=user_id
                )
                await utils.answer(message, balance_text)
            else:
                await utils.answer(message, self.strings("balance_error"))
                
        except Exception as e:
            self.logger.error(f"Ошибка получения баланса: {e}")
            await utils.answer(message, self.strings("balance_error"))

    def _parse_amount(self, amount_str):
        """Парсинг суммы с валидацией"""
        try:
            amount = float(amount_str)
            return amount if amount > 0 else None
        except ValueError:
            return None

    def _get_headers(self):
        """Создание заголовков для API запросов"""
        return {
            "Authorization": f"Bearer {self.config['api_token']}",
            "Content-Type": "application/json",
            "User-Agent": "LztPay-Hikka/1.0"
        }

    def _create_base_payload(self, amount, comment):
        """Создание базового payload для API"""
        return {
            "amount": amount,
            "comment": comment,
            "currency": self.config["currency"]
        }

    async def _resolve_user(self, user, headers, payload):
        """Определение типа пользователя и получение информации"""
        user_id = None
        username = user
        
        try:
            if user.isdigit():
                # Пользователь передан как ID
                user_id = int(user)
                payload['user_id'] = user_id
                username = f"ID: {user}"
                
            elif user.startswith("@"):
                # Пользователь передан как Telegram username
                telegram_username = user.replace('@', '')
                response = requests.get(
                    f"{self.lookup_url}?custom_fields[telegram]={telegram_username}", 
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if len(data.get('users', [])) > 0:
                        user_info = data['users'][0]
                        user_id = user_info['user_id']
                        username = user_info.get('username', user)
                        payload['user_id'] = user_id
                    else:
                        return None
                else:
                    return None
                    
            else:
                # Пользователь передан как username
                payload['username'] = user
                
                # Попытка получить ID для красивой ссылки
                try:
                    response = requests.get(
                        f"{self.lookup_url}?username={user}", 
                        headers=headers,
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if len(data.get('users', [])) > 0:
                            user_info = data['users'][0]
                            user_id = user_info['user_id']
                            username = user_info.get('username', user)
                except Exception:
                    pass
            
            return {
                'user_id': user_id,
                'username': username
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска пользователя: {e}")
            return None

    def _format_username(self, username, user_id):
        """Форматирование имени пользователя с ссылкой"""
        if user_id:
            return f"<a href='{self.profile_url.format(user_id)}'>{username}</a>"
        else:
            return f"<b>{username}</b>"

    def _generate_transfer_id(self, message):
        """Генерация уникального ID для перевода"""
        return f"{message.chat.id}_{message.id}_{message.date.timestamp()}"

    async def _show_confirmation_form(self, message, transfer_id, amount, username, comment):
        """Показ формы подтверждения перевода"""
        confirm_text = self.strings("confirm").format(
            amount=amount,
            currency=self.config["currency"],
            username=username,
            comment=comment
        )
        
        await self.inline.form(
            text=confirm_text,
            message=message,
            reply_markup=[
                [
                    {
                        "text": "✅ Подтвердить",
                        "callback": self.confirm_transfer,
                        "args": (transfer_id,)
                    },
                    {
                        "text": "❌ Отменить",
                        "callback": self.cancel_transfer,
                        "args": (transfer_id,)
                    }
                ]
            ]
        )

    async def _execute_transfer(self, message, payload, headers, amount, username, comment):
        """Выполнение перевода"""
        await utils.answer(message, self.strings("executing_transfer"))
        
        try:
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                success_message = self.strings("success").format(
                    amount=amount,
                    currency=self.config["currency"],
                    username=username,
                    comment=comment
                )
                await utils.answer(message, success_message)
            else:
                data = response.json()
                error_text = data.get("errors", data.get("message", str(data)))
                await utils.answer(message, self.strings("fail").format(error_text))
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка HTTP запроса: {e}")
            await utils.answer(message, self.strings("fail").format(str(e)))
        except Exception as e:
            self.logger.error(f"Системная ошибка: {e}")
            await utils.answer(message, self.strings("fail").format(str(e)))

    async def _cleanup_transfer(self, transfer_id, timeout):
        """Автоматическая очистка данных о переводе через таймаут"""
        await asyncio.sleep(timeout)
        if transfer_id in self.pending_transfers:
            del self.pending_transfers[transfer_id]

    async def confirm_transfer(self, call, transfer_id):
        """Подтверждение и выполнение перевода"""
        if transfer_id not in self.pending_transfers:
            await call.edit(self.strings("timeout"))
            return
        
        transfer_data = self.pending_transfers[transfer_id]
        
        # Показываем статус выполнения
        await call.edit(self.strings("executing_transfer"))
        
        try:
            response = requests.post(
                self.api_url, 
                json=transfer_data['payload'], 
                headers=transfer_data['headers'],
                timeout=30
            )
            
            if response.status_code == 200:
                success_message = self.strings("success").format(
                    amount=transfer_data['amount'],
                    currency=self.config["currency"],
                    username=transfer_data['username'],
                    comment=transfer_data['comment']
                )
                await call.edit(success_message)
            else:
                data = response.json()
                error_text = data.get("errors", data.get("message", str(data)))
                await call.edit(self.strings("fail").format(error_text))
                
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении перевода: {e}")
            await call.edit(self.strings("fail").format(str(e)))
        
        # Очистка данных
        self._remove_pending_transfer(transfer_id)

    async def cancel_transfer(self, call, transfer_id):
        """Отмена перевода"""
        if transfer_id not in self.pending_transfers:
            await call.edit(self.strings("timeout"))
            return
        
        await call.edit(self.strings("cancelled"))
        self._remove_pending_transfer(transfer_id)

    def _remove_pending_transfer(self, transfer_id):
        """Удаление данных о переводе из памяти"""
        if transfer_id in self.pending_transfers:
            del self.pending_transfers[transfer_id]
