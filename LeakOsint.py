# meta developer: @sunshinelzt
# scope: hikka_min 1.6.0
# requires: requests

import asyncio
import logging
import re
import typing
import json
from typing import List, Dict, Any

import requests
from telethon import types
from telethon.tl.types import MessageEntityTextUrl

from .. import loader, utils
from ..inline.types import InlineQuery, InlineResult

logger = logging.getLogger(__name__)

def safe_json_loads(data: str) -> Dict:
    """Безопасная загрузка JSON"""
    try:
        return json.loads(data)
    except (TypeError, json.JSONDecodeError):
        return {}

@loader.tds
class AdvancedLeakOsintMod(loader.Module):
    """<emoji document_id=5453862417215803155>💻</emoji> Продвинутый модуль для глубокого поиска информации"""

    strings = {
        "name": "<emoji document_id=5454249518323222262>📊</emoji> LeakOsint Pro",
        "no_args": "<emoji document_id=5453972364083614390>❗️</emoji> Вы не указали запрос для поиска",
        "processing": "<emoji document_id=5454071693792267761>🔥</emoji> Начинаю глубокий анализ...",
        "error": "<emoji document_id=5453972364083614390>❗️</emoji> Критическая ошибка при выполнении запроса: {}",
        "no_results": "<emoji document_id=5453914472219431554>📄</emoji> Информация не найдена. Возможно, стоит уточнить запрос.",
        "token_not_set": "<emoji document_id=5451611974611781917>📝</emoji> API токен не установлен. Настройте через .osintconfig",
        "config_updated": "<emoji document_id=5454137273647912913>🎁</emoji> Конфигурация успешно обновлена",
        "search_history": "<emoji document_id=5453886782565272984>🔙</emoji> История поиска очищена",
        "rate_limit": "<emoji document_id=5454261548526622388>⚙️</emoji> Превышен лимит запросов. Подождите немного."
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token", 
                None, 
                lambda: "<emoji document_id=5454221227373645916>🔖</emoji> API токен LeakOsint",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "default_limit", 
                300, 
                lambda: "<emoji document_id=5452088170520791411>🖲</emoji> Максимальный лимит поиска",
                validator=loader.validators.Integer(minimum=100, maximum=10000)
            ),
            loader.ConfigValue(
                "default_lang", 
                "ru", 
                lambda: "<emoji document_id=5453982431486955842>📅</emoji> Язык результатов",
                validator=loader.validators.Choice(["ru", "en"])
            ),
            loader.ConfigValue(
                "max_depth", 
                3, 
                lambda: "<emoji document_id=5454091673980132816>🧬</emoji> Глубина поиска",
                validator=loader.validators.Integer(minimum=1, maximum=5)
            )
        )
        
        self._search_history = []
        self._rate_limit_counter = 0
        self._error_log = []

    @loader.command(ru_doc="<emoji document_id=5454160256017912961>📮</emoji> Настройка конфигурации LeakOsint")
    async def osintconfig(self, message):
        """Расширенная настройка модуля"""
        args = utils.get_args_raw(message)
        
        if not args:
            # Показ текущей конфигурации
            config_text = (
                "<emoji document_id=5451958870530346105>❤️</emoji> <b>Текущая конфигурация LeakOsint:</b>\n\n"
                f"<emoji document_id=5454221227373645916>🔖</emoji> API Токен: {'✅ Установлен' if self.config['api_token'] else '❌ Не установлен'}\n"
                f"<emoji document_id=5452088170520791411>🖲</emoji> Лимит поиска: {self.config['default_limit']}\n"
                f"<emoji document_id=5453982431486955842>📅</emoji> Язык: {self.config['default_lang']}\n"
                f"<emoji document_id=5454091673980132816>🧬</emoji> Глубина поиска: {self.config['max_depth']}"
            )
            return await utils.answer(message, config_text)

        # Парсинг аргументов
        try:
            key, value = args.split(maxsplit=1)
            if key == 'token':
                self.config['api_token'] = value
            elif key == 'limit':
                self.config['default_limit'] = int(value)
            elif key == 'lang':
                self.config['default_lang'] = value
            elif key == 'depth':
                self.config['max_depth'] = int(value)
            else:
                return await utils.answer(message, "<emoji document_id=5453972364083614390>❗️</emoji> Неверный параметр конфигурации")
            
            await utils.answer(message, self.strings["config_updated"])
        except Exception as e:
            await utils.answer(message, f"<emoji document_id=5453972364083614390>❗️</emoji> Ошибка настройки: {str(e)}")

    @loader.command(ru_doc="<emoji document_id=5454249518323222262>📊</emoji> Расширенный поиск информации")
    async def osint(self, message):
        """Продвинутый поиск через LeakOsint"""
        args = utils.get_args_raw(message)
        
        if not args:
            return await utils.answer(message, self.strings["no_args"])
        
        if not self.config['api_token']:
            return await utils.answer(message, self.strings["token_not_set"])

        # Проверка лимита запросов
        if self._rate_limit_counter > 5:
            return await utils.answer(message, self.strings["rate_limit"])

        await utils.answer(message, self.strings["processing"])

        try:
            response = await self._search_osint(args)
            await self._format_and_send_results(message, response)
            
            # Обновление истории поиска
            self._search_history.append({
                'query': args,
                'timestamp': utils.get_time(),
                'results_count': len(response.get('List', {}))
            })
        except Exception as e:
            self._error_log.append(str(e))
            logger.exception(e)
            await utils.answer(message, self.strings["error"].format(str(e)))
        
        self._rate_limit_counter += 1
        await asyncio.sleep(10)  # Сброс счетчика через 10 секунд
        self._rate_limit_counter -= 1

    async def _search_osint(self, query):
        """Выполнение запроса к LeakOsint API"""
        url = "https://leakosintapi.com/"
        data = {
            "token": self.config['api_token'],
            "request": query,
            "limit": self.config['default_limit'],
            "lang": self.config['default_lang']
        }
        
        try:
            async with self._client.request('POST', url, json=data) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"API Request Error: {e}")
            raise

    async def _format_and_send_results(self, message, response):
        """Красивое форматирование и отправка результатов"""
        if "Error code" in response:
            return await utils.answer(message, f"<emoji document_id=5453972364083614390>❗️</emoji> Ошибка API: {response.get('Error code', 'Неизвестная ошибка')}")

        results = response.get("List", {})
        
        if not results or list(results.keys()) == ["No results found"]:
            return await utils.answer(message, self.strings["no_results"])

        formatted_results = []
        for db_name, db_info in results.items():
            if db_name == "No results found":
                continue

            db_section = f"<emoji document_id=5454172810207318529>🗂</emoji> <b>{db_name}</b>\n"
            db_section += f"<emoji document_id=5453914472219431554>📄</emoji> {db_info.get('InfoLeak', 'Без дополнительной информации')}\n\n"

            for entry in db_info.get("Data", []):
                entry_details = []
                for key, value in entry.items():
                    emoji = self._get_emoji_for_key(key)
                    entry_details.append(f"{emoji} <b>{key}</b>: {value}")
                
                db_section += "\n".join(entry_details) + "\n\n"
            
            formatted_results.append(db_section)

        # Разбиваем длинные результаты на части
        for result in formatted_results:
            await self._send_long_message(message.chat_id, result)

    def _get_emoji_for_key(self, key):
        """Подбор эмодзи в зависимости от типа данных"""
        key_lower = key.lower()
        if 'email' in key_lower:
            return '<emoji document_id=5453935118127222895>📩</emoji>'
        elif 'phone' in key_lower or 'tel' in key_lower:
            return '<emoji document_id=5454113616968045758>👫</emoji>'
        elif 'name' in key_lower:
            return '<emoji document_id=5454295616207213193>👨‍👩‍👧‍👦</emoji>'
        elif 'address' in key_lower:
            return '<emoji document_id=5454407706263701910>🛒</emoji>'
        elif 'date' in key_lower:
            return '<emoji document_id=5453982431486955842>📅</emoji>'
        else:
            return '<emoji document_id=5454221227373645916>🔖</emoji>'

    async def _send_long_message(self, chat_id, text, max_length=4096):
        """Отправляет длинные сообщения частями"""
        while text:
            chunk = text[:max_length]
            await self._client.send_message(chat_id, chunk, parse_mode='html')
            text = text[max_length:]

    @loader.command(ru_doc="<emoji document_id=5453914472219431554>📄</emoji> История поиска")
    async def osinthistory(self, message):
        """Показать историю поисковых запросов"""
        if not self._search_history:
            return await utils.answer(message, "<emoji document_id=5454172810207318529>🗂</emoji> История поиска пуста")
        
        history_text = "<emoji document_id=5454249518323222262>📊</emoji> <b>История поиска:</b>\n\n"
        for entry in self._search_history[-10:]:  # Последние 10 записей
            history_text += (
                f"<emoji document_id=5453982431486955842>📅</emoji> {utils.format_time(entry['timestamp'])}\n"
                f"<emoji document_id=5454221227373645916>🔖</emoji> Запрос: {entry['query']}\n"
                f"<emoji document_id=5453914472219431554>📄</emoji> Результатов: {entry['results_count']}\n\n"
            )
        
        await utils.answer(message, history_text)

    @loader.command(ru_doc="<emoji document_id=5453886782565272984>🔙</emoji> Очистить историю")
    async def osintclear(self, message):
        """Очистить историю поиска и логи ошибок"""
        self._search_history.clear()
        self._error_log.clear()
        await utils.answer(message, self.strings["search_history"])

def generate_invite_link(bot_username="@LeakOsintBot"):
    """Генерирует пригласительную ссылку на бота"""
    return f"https://t.me/{bot_username.replace('@', '')}"
