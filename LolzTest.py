# meta developer: @sunshinelzt

from telethon.tl.types import Message
from telethon import events
from .. import loader, utils
import logging
import requests
import json
import hashlib
import urllib.parse
import asyncio
import base64
from typing import Union, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

@loader.tds
class EnhancedLolzTransferMod(loader.Module):
    """🔐 Улучшенный модуль для перевода денег на lolz.live/zelenka.guru с защитой API-ключа"""
    
    strings = {
        "name": "EnhancedLolzTransfer",
        "no_api": "⚠️ <b>API ключ не установлен. Используйте </b><code>.lzconfig</code>",
        "no_secret": "⚠️ <b>Секретная фраза не установлена. Используйте </b><code>.lzconfig</code>",
        "config_saved": "✅ <b>Конфигурация успешно сохранена!</b>",
        "invalid_amount": "⚠️ <b>Неверная сумма. Пожалуйста, введите корректное число.</b>",
        "user_not_found": "⚠️ <b>Пользователь не найден на форуме.</b>",
        "transfer_success": "✅ <b>Успешно переведено <code>{amount} {currency}</code> пользователю </b><a href='{profile_url}'>{username}</a>",
        "transfer_error": "❌ <b>Ошибка при переводе средств:</b> <code>{error}</code>",
        "transfer_confirm": "💸 <b>Перевод средств</b>\n\n<b>Получатель:</b> <a href='{profile_url}'>{username}</a>\n<b>Сумма:</b> <code>{amount} {currency}</code>\n<b>Комментарий:</b> <i>{comment}</i>",
        "confirm": "✅ Подтвердить",
        "cancel": "❌ Отменить",
        "operation_cancelled": "❌ <b>Операция отменена.</b>",
        "checking_user": "🔍 <b>Поиск пользователя</b> <code>{username}</code><b>...</b>",
        "api_error": "❌ <b>Ошибка API:</b> <code>{error}</code>",
        "balance_info": "💰 <b>Ваш баланс:</b>\n\n{balance_info}",
        "decryption_failed": "⚠️ <b>Ошибка расшифровки API ключа. Проверьте корректность данных.</b>",
        "processing_transfer": "⏳ <b>Выполняется перевод</b> <code>{amount} {currency}</code> <b>пользователю</b> <code>{username}</code><b>...</b>",
        "help_text": (
            "<b>🔹 EnhancedLolzTransfer 🔹</b>\n\n"
            "<b>📌 Команды:</b>\n"
            "  • <code>.lzconfig [ENCODED_API_KEY] [SECRET_PHRASE]</code>\n"
            "     <i>Настройка API ключа (в base64) и секретной фразы</i>\n\n"
            "  • <code>.lztransfer [username] [сумма] [валюта] [комментарий]</code>\n"
            "     <i>Перевод средств на указанный аккаунт</i>\n\n"
            "  • <code>.lzbalance</code>\n"
            "     <i>Проверка баланса</i>\n\n"
            "  • <code>.lzhistory [число_записей]</code>\n"
            "     <i>История операций (макс. 50)</i>\n\n"
            "<b>💡 Примечание:</b> API ключ должен быть зашифрован в формате base64"
        ),
        "history_title": "📜 <b>История операций:</b>",
        "history_empty": "📭 <b>История операций пуста</b>",
        "getting_history": "🔄 <b>Получение истории операций...</b>",
        "getting_balance": "🔄 <b>Получение информации о балансе...</b>",
        "history_item": "{icon} <b>{amount} {currency}</b> • <i>{description}</i>",
        "balance_empty": "• <i>На балансе нет средств</i>",
        "auth_success": "✅ <b>Авторизация успешна! Аккаунт:</b> <code>{username}</code>",
        "config_guide": (
            "<b>🔧 Настройка EnhancedLolzTransfer</b>\n\n"
            "<code>.lzconfig [ENCODED_API_KEY] [SECRET_PHRASE]</code>\n\n"
            "<b>Где:</b>\n"
            "• <code>ENCODED_API_KEY</code> — API ключ в формате base64\n"
            "• <code>SECRET_PHRASE</code> — Секретная фраза\n\n"
            "<i>API ключ можно получить в настройках профиля на lolz.live/zelenka.guru</i>"
        )
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY_ENCODED", "", "API Ключ Lolz Market/Zelenka.Guru в формате base64",
            "SECRET_PHRASE", "", "Секретная фраза для подтверждения переводов",
            "DEFAULT_CURRENCY", "rub", "Валюта по умолчанию (rub, usd и т.д.)",
            "DEFAULT_HOLD", 0, "Срок холда по умолчанию (0 для отсутствия холда)",
            "DEFAULT_HOLD_OPTION", "day", "Опция холда по умолчанию (day, month)",
            "API_URL_FORUM", "https://api.lolz.live", "URL API форума",
            "API_URL_MARKET", "https://api.lzt.market", "URL API маркета",
            "UI_THEME", "modern", "Тема интерфейса (modern, classic, dark)"
        )
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        """Инициализация при готовности клиента"""
        self.client = client
        self.db = db
        self._cache = {}
        self._semaphore = asyncio.Semaphore(3)  # Ограничение параллельных запросов
    
    def _decode_api_key(self) -> Optional[str]:
        """
        Расшифровка API ключа из base64
        
        Returns:
            Optional[str]: Расшифрованный API ключ или None в случае ошибки
        """
        if not self.config["API_KEY_ENCODED"]:
            return None
            
        try:
            # Декодируем base64
            return base64.b64decode(self.config["API_KEY_ENCODED"]).decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка расшифровки API ключа: {e}")
            return None
        
    async def _make_request(self, method: str, url: str, headers: Dict[str, str] = None, 
                            params: Optional[Dict[str, Any]] = None, 
                            json_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        Универсальный метод для выполнения HTTP запросов с обработкой ошибок
        
        Args:
            method: HTTP метод (GET, POST и т.д.)
            url: URL для запроса
            headers: Заголовки запроса
            params: Параметры запроса (для GET)
            json_data: JSON данные (для POST)
            
        Returns:
            Tuple[bool, Union[Dict[str, Any], str]]: (успех, данные/сообщение об ошибке)
        """
        # Получаем расшифрованный API ключ, если в заголовках есть Authorization
        if headers and "Authorization" in headers and "Bearer" in headers["Authorization"]:
            api_key = self._decode_api_key()
            if not api_key:
                return False, self.strings["decryption_failed"]
            headers["Authorization"] = f"Bearer {api_key}"
        
        async with self._semaphore:
            try:
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=json_data)
                else:
                    return False, f"Неподдерживаемый метод: {method}"
                
                # Обработка ответа
                if response.status_code == 200:
                    try:
                        return True, response.json()
                    except json.JSONDecodeError:
                        return True, response.text
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"Код ошибки: {response.status_code}")
                    except json.JSONDecodeError:
                        error_msg = f"Код ошибки: {response.status_code}, текст: {response.text[:100]}"
                    
                    return False, error_msg
                    
            except Exception as e:
                logger.error(f"Ошибка запроса {url}: {e}")
                return False, str(e)
    
    async def get_user_by_username(self, username: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Усовершенствованный поиск пользователя по имени пользователя
        
        Args:
            username: Имя пользователя для поиска
            
        Returns:
            Tuple[Optional[int], Optional[str], Optional[str]]: (ID пользователя, URL профиля, имя пользователя)
        """
        if not self.config["API_KEY_ENCODED"]:
            return None, None, None
            
        # Кэширование результатов для оптимизации
        cache_key = f"user_{username.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        headers = {"Authorization": "Bearer PLACEHOLDER"}  # Реальный ключ будет подставлен в _make_request
        
        # Метод 1: Прямой поиск по API find
        encoded_username = urllib.parse.quote(username)
        success, data = await self._make_request(
            "GET", 
            f"{self.config['API_URL_FORUM']}/users/find?username={encoded_username}",
            headers
        )
        
        if success and data.get("user_id"):
            result = (
                data["user_id"], 
                f"https://lolz.live/members/{data['user_id']}", 
                data.get("username", username)
            )
            self._cache[cache_key] = result
            return result
            
        # Метод 2: Поиск через API search с точным совпадением
        success, data = await self._make_request(
            "GET",
            f"{self.config['API_URL_FORUM']}/users/search",
            headers,
            params={"username": username}
        )
        
        if success and isinstance(data, list):
            for user in data:
                if user.get("username", "").lower() == username.lower():
                    result = (
                        user["user_id"],
                        f"https://lolz.live/members/{user['user_id']}",
                        user["username"]
                    )
                    self._cache[cache_key] = result
                    return result
                    
        # Метод 3: Поиск по email, если передан email
        if "@" in username and "." in username:
            success, data = await self._make_request(
                "GET",
                f"{self.config['API_URL_FORUM']}/users/find-by-email",
                headers,
                params={"email": username}
            )
            
            if success and data.get("user_id"):
                result = (
                    data["user_id"],
                    f"https://lolz.live/members/{data['user_id']}",
                    data.get("username", username)
                )
                self._cache[cache_key] = result
                return result
                
        # Пользователь не найден
        return None, None, None
        
    async def get_balance(self) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """Получение баланса пользователя"""
        if not self.config["API_KEY_ENCODED"]:
            return False, self.strings["no_api"]
            
        headers = {"Authorization": "Bearer PLACEHOLDER"}  # Реальный ключ будет подставлен в _make_request
        return await self._make_request(
            "GET",
            f"{self.config['API_URL_MARKET']}/balance",
            headers
        )
        
    async def get_user_info(self) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """Получение информации о текущем пользователе"""
        if not self.config["API_KEY_ENCODED"]:
            return False, self.strings["no_api"]
            
        headers = {"Authorization": "Bearer PLACEHOLDER"}  # Реальный ключ будет подставлен в _make_request
        return await self._make_request(
            "GET",
            f"{self.config['API_URL_FORUM']}/users/me",
            headers
        )
        
    async def get_history(self, limit: int = 10) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """Получение истории операций"""
        if not self.config["API_KEY_ENCODED"]:
            return False, self.strings["no_api"]
            
        headers = {"Authorization": "Bearer PLACEHOLDER"}  # Реальный ключ будет подставлен в _make_request
        return await self._make_request(
            "GET",
            f"{self.config['API_URL_MARKET']}/balance/history",
            headers,
            params={"limit": min(limit, 50)}  # Ограничение максимального количества
        )
        
    async def transfer_money(self, user_id: int, amount: float, currency: str, 
                           comment: str, secret_answer: str) -> Tuple[bool, Optional[str]]:
        """
        Перевод денег через API маркета
        
        Args:
            user_id: ID пользователя
            amount: Сумма перевода
            currency: Валюта перевода
            comment: Комментарий к переводу
            secret_answer: Секретная фраза
            
        Returns:
            Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
        """
        if not self.config["API_KEY_ENCODED"]:
            return False, self.strings["no_api"]
            
        headers = {"Authorization": "Bearer PLACEHOLDER"}  # Реальный ключ будет подставлен в _make_request
        payload = {
            "amount": float(amount),
            "currency": currency.lower(),
            "secret_answer": secret_answer,
            "user_id": int(user_id),
            "comment": comment,
            "hold": self.config["DEFAULT_HOLD"],
            "hold_option": self.config["DEFAULT_HOLD_OPTION"]
        }
        
        success, data = await self._make_request(
            "POST",
            f"{self.config['API_URL_MARKET']}/balance/transfer",
            headers,
            json_data=payload
        )
        
        if success:
            return True, None
        else:
            return False, data
    
    def generate_operation_id(self, user_id: int, amount: float, currency: str, 
                           username: str, comment: str) -> str:
        """
        Генерация уникального идентификатора операции
        
        Args:
            user_id: ID пользователя
            amount: Сумма перевода
            currency: Валюта перевода
            username: Имя пользователя
            comment: Комментарий к переводу
            
        Returns:
            str: Уникальный идентификатор операции
        """
        # Создаем уникальный идентификатор для операции
        raw_data = f"{user_id}_{amount}_{currency}_{username}_{comment}_{utils.rand(16)}"
        operation_id = hashlib.md5(raw_data.encode()).hexdigest()[:12]
        
        # Сохраняем данные в базу
        self.db.set(self.name, f"op_{operation_id}", {
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "username": username,
            "comment": comment,
            "timestamp": utils.time.time()  # Добавляем временную метку для отслеживания устаревших операций
        })
        
        return operation_id
    
    @loader.owner
    async def lzconfigcmd(self, message: Message):
        """Настроить API ключ и секретную фразу"""
        args = utils.get_args_raw(message).split(maxsplit=1)
        
        if len(args) < 2:
            await utils.answer(message, self.strings["config_guide"])
            return
        
        api_key_encoded, secret_phrase = args
        
        # Проверяем валидность API ключа (пробуем расшифровать)
        try:
            base64.b64decode(api_key_encoded).decode('utf-8')
        except Exception:
            await utils.answer(message, self.strings["decryption_failed"])
            return
        
        # Сохраняем данные в конфиг
        self.config["API_KEY_ENCODED"] = api_key_encoded.strip()
        self.config["SECRET_PHRASE"] = secret_phrase.strip()
        
        # Проверяем авторизацию
        success, data = await self.get_user_info()
        
        if success and data.get("username"):
            # Очищаем кэш при изменении API ключа
            self._cache = {}
            await utils.answer(
                message, 
                self.strings["auth_success"].format(username=data.get("username")) + "\n\n" + self.strings["config_saved"]
            )
        else:
            self.config["API_KEY_ENCODED"] = ""
            self.config["SECRET_PHRASE"] = ""
            error_message = data if isinstance(data, str) else "Неизвестная ошибка"
            await utils.answer(message, f"❌ <b>Ошибка авторизации:</b> {error_message}")
    
    @loader.owner
    async def lzbalancecmd(self, message: Message):
        """Проверить баланс"""
        if not self.config["API_KEY_ENCODED"]:
            await utils.answer(message, self.strings["no_api"])
            return
            
        status_msg = await utils.answer(message, self.strings["getting_balance"])
        
        success, data = await self.get_balance()
        
        if success:
            balance_text = ""
            for currency, amount in data.items():
                if isinstance(amount, (int, float)) and amount > 0:
                    balance_text += f"• <b>{currency.upper()}</b>: <code>{amount}</code>\n"
            
            if not balance_text:
                balance_text = self.strings["balance_empty"]
                
            await utils.answer(status_msg, self.strings["balance_info"].format(balance_info=balance_text))
        else:
            await utils.answer(status_msg, self.strings["api_error"].format(error=data))
    
    @loader.owner
    async def lzhistorycmd(self, message: Message):
        """История операций"""
        if not self.config["API_KEY_ENCODED"]:
            await utils.answer(message, self.strings["no_api"])
            return
            
        args = utils.get_args_raw(message)
        try:
            limit = int(args) if args else 10
        except ValueError:
            limit = 10
            
        status_msg = await utils.answer(message, self.strings["getting_history"])
        
        success, data = await self.get_history(limit)
        
        if success:
            if not data:
                await utils.answer(status_msg, self.strings["history_empty"])
                return
                
            history_text = f"{self.strings['history_title']}\n\n"
            
            for item in data:
                operation_type = item.get("type", "unknown")
                amount = item.get("amount", 0)
                currency = item.get("currency", "").upper()
                description = item.get("description", "Нет описания")
                timestamp = item.get("date", 0)
                
                if operation_type == "income":
                    icon = "📥"
                elif operation_type == "outcome":
                    icon = "📤"
                else:
                    icon = "🔄"
                    
                history_text += self.strings["history_item"].format(
                    icon=icon,
                    amount=amount,
                    currency=currency,
                    description=description
                ) + "\n"
                
            await utils.answer(status_msg, history_text)
        else:
            await utils.answer(status_msg, self.strings["api_error"].format(error=data))
    
    @loader.owner
    async def lztransfercmd(self, message: Message):
        """Перевести деньги пользователю"""
        if not self.config["API_KEY_ENCODED"]:
            await utils.answer(message, self.strings["no_api"])
            return
        
        if not self.config["SECRET_PHRASE"]:
            await utils.answer(message, self.strings["no_secret"])
            return
        
        args = utils.get_args_raw(message)
        
        # Парсинг аргументов с поддержкой кавычек
        parsed_args = []
        current_arg = ""
        in_quotes = False
        
        for char in args + " ":  # Добавляем пробел для обработки последнего аргумента
            if char == '"' and (not current_arg or current_arg[-1] != '\\'):
                in_quotes = not in_quotes
                if not in_quotes and current_arg:
                    parsed_args.append(current_arg)
                    current_arg = ""
            elif char == ' ' and not in_quotes:
                if current_arg:
                    parsed_args.append(current_arg)
                    current_arg = ""
            else:
                current_arg += char
        
        if len(parsed_args) < 2:
            await utils.answer(message, self.strings["help_text"])
            return
        
        # Парсинг аргументов
        username = parsed_args[0]
        
        try:
            amount = float(parsed_args[1])
        except ValueError:
            await utils.answer(message, self.strings["invalid_amount"])
            return
        
        currency = parsed_args[2] if len(parsed_args) > 2 else self.config["DEFAULT_CURRENCY"]
        comment = parsed_args[3] if len(parsed_args) > 3 else f"Перевод для {username}"
        
        # Отправка сообщения о процессе проверки
        status_msg = await utils.answer(
            message, 
            self.strings["checking_user"].format(username=username)
        )
        
        # Получение ID пользователя
        user_id, profile_url, actual_username = await self.get_user_by_username(username)
        
        if not user_id:
            await utils.answer(status_msg, self.strings["user_not_found"])
            return
        
        # Используем фактическое имя пользователя из API
        display_username = actual_username or username
        
        # Генерация идентификатора операции
        operation_id = self.generate_operation_id(
            user_id, amount, currency, display_username, comment
        )
        
        # Создание инлайн-клавиатуры для подтверждения
        await self.inline.form(
            self.strings["transfer_confirm"].format(
                amount=amount,
                currency=currency.upper(),
                username=display_username,
                profile_url=profile_url,
                comment=comment
            ),
            message=message,
            reply_markup=[
                [
                    {
                        "text": self.strings["confirm"],
                        "callback": self.confirm_transfer,
                        "args": (operation_id,)
                    },
                    {
                        "text": self.strings["cancel"],
                        "callback": self.cancel_transfer,
                        "args": (operation_id,)
                    }
                ]
            ],
            ttl=300,  # Время жизни формы - 5 минут
            disable_security=False
        )
    
    async def confirm_transfer(self, call, operation_id):
        """Обработчик подтверждения перевода"""
        # Получение данных операции
        operation_data = self.db.get(self.name, f"op_{operation_id}")
        
        if not operation_data:
            await call.edit(
                "❌ <b>Данные операции устарели или были удалены.</b>",
                reply_markup=[]
            )
            return
        
        # Проверка на истечение срока действия операции (10 минут)
        current_time = utils.time.time()
        if current_time - operation_data.get("timestamp", 0) > 600:
            await call.edit(
                "❌ <b>Время действия операции истекло.</b>",
                reply_markup=[]
            )
            self.db.set(self.name, f"op_{operation_id}", None)
            return
        
        user_id = operation_data["user_id"]
        amount = operation_data["amount"]
        currency = operation_data["currency"]
        username = operation_data["username"]
        comment = operation_data["comment"]
        
        # Обновление сообщения
        await call.edit(
            self.strings["processing_transfer"].format(
                amount=amount,
                currency=currency.upper(),
                username=username
            ),
            reply_markup=[]
        )
        
        # Получаем URL профиля
        profile_url = f"https://lolz.live/members/{user_id}"
        
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
            await call.edit(
                self.strings["transfer_success"].format(
                    amount=amount,
                    currency=currency.upper(),
                    username=username,
                    profile_url=profile_url
                )
            )
        else:
            await call.edit(
                self.strings["transfer_error"].format(error=error)
            )
    
    async def cancel_transfer(self, call, operation_id):
        """Обработчик отмены перевода"""
        # Удаляем данные операции
        self.db.set(self.name, f"op_{operation_id}", None)
        
        await call.edit(
            self.strings["operation_cancelled"],
            reply_markup=[]
        )
    
    @loader.command
    async def lzhelp(self, message: Message):
        """Помощь по модулю"""
        await utils.answer(message, self.strings["help_text"])
    
    # Инлайн-обработчик для Hikka
    async def lztransfer_inline_handler(self, query):
        """Инлайн обработчик для перевода средств"""
        query_text = query.args
        
        if not query_text:
            return
        
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
        
        if len(args) < 2:
            return
        
        username, amount_str = args[:2]
        
        try:
            amount = float(amount_str)
        except ValueError:
            return
        
        currency = args[2] if len(args) > 2 else self.config["DEFAULT_CURRENCY"]
        comment = " ".join(args[3:]) if len(args) > 3 else f"Перевод для {username}"
        
        # Проверяем наличие API ключа
        if not self.config["API_KEY_ENCODED"] or not self.config["SECRET_PHRASE"]:
            return [
                {
                    "title": "⚠️ Не настроен API ключ или секретная фраза",
                    "description": "Используйте .lzconfig для настройки",
                    "message": "⚠️ <b>Для использования модуля необходимо настроить API ключ и секретную фразу</b>\n\nИспользуйте команду <code>.lzconfig API_KEY SECRET_PHRASE</code>",
                    "thumb": "https://img.icons8.com/color/48/000000/error--v1.png"
                }
            ]
        
        # Получение ID пользователя
        user_id, profile_url, actual_username = await self.get_user_by_username(username)
        
        if not user_id:
            return [
                {
                    "title": "⚠️ Пользователь не найден",
                    "description": f"Пользователь {username} не найден на форуме",
                    "message": self.strings["user_not_found"],
                    "thumb": "https://img.icons8.com/color/48/000000/error--v1.png"
                }
            ]
        
        # Используем фактическое имя пользователя из API
        display_username = actual_username or username
        
        # Генерация данных для callback
        operation_id = self.generate_operation_id(
            user_id, amount, currency, display_username, comment
        )
        
        # Используем формат инлайн-форм для Hikka
        return [
            {
                "title": f"💸 Перевести {amount} {currency.upper()} пользователю {display_username}",
                "description": f"Комментарий: {comment}",
                "message": self.strings["transfer_confirm"].format(
                    amount=amount,
                    currency=currency.upper(),
                    username=display_username,
                    profile_url=profile_url,
                    comment=comment
                ),
                "thumb": "https://img.icons8.com/fluency/48/000000/money-transfer.png",
                "reply_markup": [
                    [
                        {
                            "text": self.strings["confirm"],
                            "callback": self.confirm_transfer,
                            "args": (operation_id,)
                        },
                        {
                            "text": self.strings["cancel"],
                            "callback": self.cancel_transfer,
                            "args": (operation_id,)
                        }
                    ]
                ]
            }
        ]
