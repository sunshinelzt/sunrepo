# meta developer: @sunshinelzt

from .. import loader, utils
import requests
import asyncio


@loader.tds
class LztPayMod(loader.Module):
    """Перевод денег через LZT Market API по нику, ID или Telegram username"""
    
    strings = {
        "name": "LztPay",
        
        # Ошибки и предупреждения
        "no_token": (
            "❌ <b>Токен не установлен</b>\n\n"
            "💡 <i>Используй:</i> <code>.settoken &lt;токен&gt;</code>"
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
        
        # Успешные операции
        "token_set": (
            "✅ <b>Токен успешно установлен</b>\n\n"
            "🔐 Теперь вы можете совершать переводы"
        ),
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
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token",
                "",
                "LZT Market API токен для переводов",
                validator=loader.validators.Hidden()
            ),
            loader.ConfigValue(
                "api_url",
                "https://prod-api.lzt.market/balance/transfer",
                "URL API для переводов"
            ),
            loader.ConfigValue(
                "lookup_url",
                "https://prod-api.lolz.live/users/find",
                "URL API для поиска пользователей"
            ),
            loader.ConfigValue(
                "profile_url",
                "https://lolz.live/members/{}",
                "URL профиля пользователя (с плейсхолдером {})"
            ),
            loader.ConfigValue(
                "default_comment",
                "Перевод через LztPay",
                "Комментарий по умолчанию для переводов"
            ),
            loader.ConfigValue(
                "transfer_timeout",
                300,
                "Таймаут подтверждения перевода в секундах",
                validator=loader.validators.Integer(minimum=10)
            ),
            loader.ConfigValue(
                "currency",
                "RUB",
                "Валюта для переводов"
            ),
        )
        
        self.pending_transfers = {}

    @property
    def api_url(self):
        return self.config["api_url"]
    
    @property
    def lookup_url(self):
        return self.config["lookup_url"]
    
    @property
    def profile_url(self):
        return self.config["profile_url"]
    
    @property
    def token(self):
        return self.config["api_token"]
    
    @property
    def default_comment(self):
        return self.config["default_comment"]
    
    @property
    def transfer_timeout(self):
        return self.config["transfer_timeout"]
    
    @property
    def currency(self):
        return self.config["currency"]

    async def settokencmd(self, message):
        """Установить API токен: .settoken <токен>"""
        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings("no_token"))
            return
        
        self.config["api_token"] = args[0]
        await utils.answer(message, self.strings("token_set"))

    async def paycmd(self, message):
        """Перевести деньги: .pay <ник/ID/@telegram> <amount> [комментарий]"""
        # Проверка токена
        if not self.token:
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
            
        comment = " ".join(args[2:]) if len(args) > 2 else self.default_comment
        
        # Базовая проверка пользователя
        if user is None:
            await utils.answer(message, self.strings("not_found"))
            return
        
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
        
        # Создание данных для подтверждения
        transfer_id = self._generate_transfer_id(message)
        formatted_username = self._format_username(user_info['username'], user_info['user_id'])
        
        self.pending_transfers[transfer_id] = {
            'payload': payload,
            'headers': headers,
            'amount': amount,
            'username': formatted_username,
            'comment': comment,
            'user_id': user_info['user_id'],
            'message': message
        }
        
        # Показываем форму подтверждения
        await self._show_confirmation_form(message, transfer_id, amount, formatted_username, comment)
        
        # Автоматическая очистка через таймаут
        asyncio.create_task(self._cleanup_transfer(transfer_id, self.transfer_timeout))

    def _parse_amount(self, amount_str):
        """Парсинг суммы с валидацией"""
        try:
            amount = int(amount_str)
            return amount if amount > 0 else None
        except ValueError:
            return None

    def _get_headers(self):
        """Создание заголовков для API запросов"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _create_base_payload(self, amount, comment):
        """Создание базового payload для API"""
        return {
            "amount": amount,
            "comment": comment,
            "currency": self.currency
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
                    headers=headers
                )
                data = response.json()
                
                if response.status_code == 200 and len(data.get('users', [])) > 0:
                    user_info = data['users'][0]
                    user_id = user_info['user_id']
                    username = user_info.get('username', user)
                    payload['user_id'] = user_id
                else:
                    return None
                    
            else:
                # Пользователь передан как username
                payload['username'] = user
                
                # Попытка получить ID для красивой ссылки
                try:
                    response = requests.get(f"{self.lookup_url}?username={user}", headers=headers)
                    data = response.json()
                    if response.status_code == 200 and len(data.get('users', [])) > 0:
                        user_info = data['users'][0]
                        user_id = user_info['user_id']
                        username = user_info.get('username', user)
                except:
                    pass
            
            return {
                'user_id': user_id,
                'username': username
            }
            
        except Exception as e:
            return None

    def _format_username(self, username, user_id):
        """Форматирование имени пользователя с ссылкой"""
        if user_id:
            return f"<a href='{self.profile_url.format(user_id)}'>{username}</a>"
        else:
            return f"<b>{username}</b>"

    def _generate_transfer_id(self, message):
        """Генерация уникального ID для перевода"""
        return f"{message.chat.id}_{message.id}"

    async def _show_confirmation_form(self, message, transfer_id, amount, username, comment):
        """Показ формы подтверждения перевода"""
        confirm_text = self.strings("confirm").format(
            amount=amount,
            currency=self.currency,
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
            # Выполнение API запроса
            response = requests.post(
                self.api_url, 
                json=transfer_data['payload'], 
                headers=transfer_data['headers']
            )
            data = response.json()
            
            if response.status_code == 200:
                # Успешный перевод
                success_message = self.strings("success").format(
                    amount=transfer_data['amount'],
                    currency=self.currency,
                    username=transfer_data['username'],
                    comment=transfer_data['comment']
                )
                await call.edit(success_message)
            else:
                # Ошибка API
                error_text = data.get("errors", data.get("message", str(data)))
                await call.edit(self.strings("fail").format(error_text))
                
        except Exception as e:
            # Системная ошибка
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
