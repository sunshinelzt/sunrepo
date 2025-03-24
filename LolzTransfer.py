# meta developer: @sunshinelzt

from telethon.tl.types import Message
from telethon import events
from .. import loader, utils
import logging
import hashlib
import urllib.parse
import requests
from typing import Dict, Optional, Tuple

class LolzTransfer(loader.Module):
    """Продвинутый модуль финансовых операций для Lolz.market"""

    strings = {
        "name": "LolzTransfer",
        "config_help": "🔧 Настройка API: .lzconfig API_KEY SECRET_PHRASE",
        "transfer_usage": "💸 Перевод: .lztransfer username amount [currency] [comment]",
        "api_error": "🚫 Ошибка API: Проверьте настройки",
        "user_not_found": "❌ Пользователь {username} не найден",
        "transfer_success": "✅ Переведено {amount} {currency} пользователю {username}",
        "transfer_error": "❌ Ошибка перевода: {error}",
        "balance_info": "💳 Баланс: {balance} {currency}\n🔓 Доступно: {available} {currency}",
        "history_title": "📜 История транзакций",
        "help_menu": (
            "🌟 <b>LolzTransfer - Меню помощи</b>\n\n"
            "🔹 Основные команды:\n"
            "• <code>.lzconfig</code> - Настройка API\n"
            "• <code>.lzbalance</code> - Проверка баланса\n"
            "• <code>.lztransfer</code> - Перевод средств\n"
            "• <code>.lzhistory</code> - История операций"
        )
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_KEY", "", "API ключ Lolz.Market",
            "SECRET_PHRASE", "", "Секретная фраза",
            "DEFAULT_CURRENCY", "rub", "Валюта по умолчанию",
            "TRANSFER_TIMEOUT", 30, "Таймаут операций (сек)",
            "MAX_TRANSFER_AMOUNT", 50000, "Максимальная сумма перевода"
        )
        self._cache = {}
        self._transfer_locks = {}

    def _generate_secure_id(self, data: str) -> str:
        """Генерация безопасного уникального идентификатора"""
        return hashlib.sha256(
            f"{data}_{hashlib.md5(str(self.config['API_KEY']).encode()).hexdigest()}"
            .encode()
        ).hexdigest()[:16]

    def _validate_transfer_params(self, amount: float, username: str) -> Tuple[bool, Optional[str]]:
        """Расширенная валидация параметров перевода"""
        if not username or len(username) < 2:
            return False, "Некорректное имя пользователя"
        
        try:
            amount = float(amount)
            if amount <= 0:
                return False, "Сумма должна быть положительной"
            
            if amount > self.config["MAX_TRANSFER_AMOUNT"]:
                return False, f"Превышен лимит перевода {self.config['MAX_TRANSFER_AMOUNT']}"
        except ValueError:
            return False, "Неверный формат суммы"
        
        return True, None

    def _api_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Универсальный метод API-запросов с расширенной обработкой"""
        base_url = "https://api.lzt.market"
        url = f"{base_url}/{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.config['API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": "LolzTransfer/1.0"
        }
        
        try:
            if method.lower() == 'get':
                response = requests.get(url, headers=headers, params=data, timeout=self.config["TRANSFER_TIMEOUT"])
            else:
                response = requests.post(url, headers=headers, json=data, timeout=self.config["TRANSFER_TIMEOUT"])
            
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            logging.error(f"API Error: {e}")
            return {"error": str(e)}

    def _find_user(self, username: str) -> Optional[Dict]:
        """Улучшенный поиск пользователя с кэшированием"""
        cache_key = self._generate_secure_id(username)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        encoded_username = urllib.parse.quote(username)
        
        # Основной и резервный методы поиска
        search_methods = [
            f"users/find?username={encoded_username}",
            "users/search"
        ]
        
        for method in search_methods:
            result = self._api_request('get', method, {"username": username})
            
            if result and (result.get("user_id") or len(result) > 0):
                user_data = result[0] if isinstance(result, list) else result
                user_info = {
                    "user_id": user_data.get("user_id"),
                    "username": user_data.get("username"),
                    "profile_url": f"https://lolz.live/members/{user_data.get('user_id')}"
                }
                
                # Кэширование результата
                self._cache[cache_key] = user_info
                return user_info
        
        return None

    def _create_transfer_payload(self, user_id: int, amount: float, currency: str, comment: str) -> Dict:
        """Подготовка payload для перевода"""
        return {
            "amount": float(amount),
            "currency": currency,
            "user_id": int(user_id),
            "comment": comment,
            "secret_answer": self.config["SECRET_PHRASE"]
        }

    @loader.owner
    async def lztransfercmd(self, message: Message):
        """Продвинутый перевод средств"""
        args = utils.get_args_raw(message).split(maxsplit=3)
        
        if len(args) < 2:
            await utils.answer(message, self.strings["transfer_usage"])
            return
        
        username, amount = args[:2]
        currency = args[2] if len(args) > 2 else self.config["DEFAULT_CURRENCY"]
        comment = args[3] if len(args) > 3 else f"Перевод для {username}"
        
        # Валидация параметров
        valid, error = self._validate_transfer_params(amount, username)
        if not valid:
            await utils.answer(message, f"❌ {error}")
            return
        
        # Поиск пользователя
        user_info = self._find_user(username)
        if not user_info:
            await utils.answer(message, self.strings["user_not_found"].format(username=username))
            return
        
        # Подготовка и выполнение перевода
        payload = self._create_transfer_payload(
            user_info["user_id"], amount, currency, comment
        )
        
        transfer_result = self._api_request('post', 'balance/transfer', payload)
        
        if transfer_result.get("error"):
            await utils.answer(message, self.strings["transfer_error"].format(error=transfer_result["error"]))
            return
        
        await utils.answer(message, self.strings["transfer_success"].format(
            amount=amount, currency=currency.upper(), username=username
        ))

    @loader.owner
    async def lzbalancecmd(self, message: Message):
        """Получение баланса с дополнительной информацией"""
        balance_info = self._api_request('get', 'balance')
        
        if balance_info.get("error"):
            await utils.answer(message, self.strings["api_error"])
            return
        
        await utils.answer(message, self.strings["balance_info"].format(
            balance=balance_info.get('balance', 0),
            currency=balance_info.get('currency', 'RUB'),
            available=balance_info.get('available', 0)
        ))

    @loader.owner
    async def lzconfigcmd(self, message: Message):
        """Настройка и проверка API"""
        args = utils.get_args_raw(message).split(maxsplit=1)
        
        if len(args) < 2:
            await utils.answer(message, self.strings["config_help"])
            return
        
        self.config["API_KEY"], self.config["SECRET_PHRASE"] = args
        
        # Проверка корректности API
        balance_check = self._api_request('get', 'balance')
        
        if balance_check.get("error"):
            await utils.answer(message, self.strings["api_error"])
            return
        
        await utils.answer(message, "✅ API успешно настроен!")

    async def helplolzcmd(self, message: Message):
        """Справка по модулю"""
        await utils.answer(message, self.strings["help_menu"])
