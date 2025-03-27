# meta developer: @sunshinelzt
# scope: hikka_min 1.6.0

import asyncio
import logging
import re
from typing import List, Dict, Any

import requests
from telethon import types
from telethon.tl.types import MessageEntityTextUrl

from .. import loader, utils
from ..inline.types import InlineQuery, InlineResult

logger = logging.getLogger(__name__)

@loader.tds
class LeakOsintMod(loader.Module):
    """🕵️ Продвинутый модуль для глубокого поиска информации с LeakOsint"""

    strings = {
        "name": "🔍 LeakOsint",
        "no_args": "❌ Вы не указали запрос для поиска",
        "processing": "🌪️ Начинаю глубокий анализ...",
        "error": "❗ Критическая ошибка при выполнении запроса: {}",
        "no_results": "🚫 Информация не найдена. Возможно, стоит уточнить запрос.",
        "token_not_set": "🔒 API токен не установлен. Настройте через .osintconfig",
        "config_updated": "✅ Конфигурация успешно обновлена",
        "search_history": "📜 История поиска очищена",
        "rate_limit": "⏳ Превышен лимит запросов. Подождите немного."
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token", 
                None, 
                lambda: "🔑 API токен LeakOsint",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "default_limit", 
                300, 
                lambda: "🔢 Максимальный лимит поиска",
                validator=loader.validators.Integer(minimum=100, maximum=10000)
            ),
            loader.ConfigValue(
                "default_lang", 
                "ru", 
                lambda: "🌐 Язык результатов",
                validator=loader.validators.Choice(["ru", "en"])
            ),
            loader.ConfigValue(
                "max_depth", 
                3, 
                lambda: "🕳️ Глубина поиска (количество перекрестных источников)",
                validator=loader.validators.Integer(minimum=1, maximum=5)
            )
        )
        
        self._search_history = []
        self._rate_limit_counter = 0
        self._error_log = []

    async def client_ready(self, client, db):
        self._client = client
        self.inline_handler = self.create_inline_handler()

    def create_inline_handler(self):
        """Создание инлайн-хендлера для расширенного поиска"""
        @loader.inline_handler(func=lambda self, query: query.startswith('osint_'))
        async def handler(self, query: InlineQuery):
            try:
                search_type = query.split('_')[1]
                if search_type == 'advanced':
                    return await self._advanced_search_inline(query)
            except Exception as e:
                return [InlineResult(
                    id=query,
                    title="Ошибка инлайн-поиска",
                    description=str(e),
                    thumb="https://img.icons8.com/fluency/48/error.png"
                )]

        return handler

    async def _advanced_search_inline(self, query: str) -> List[InlineResult]:
        """Расширенный инлайн-поиск с предварительным анализом"""
        query_text = query.split('advanced ', 1)[1].strip()
        
        # Предварительный анализ запроса
        query_analysis = self._analyze_query(query_text)
        
        return [
            InlineResult(
                id=query,
                title=f"🔎 Поиск: {query_text}",
                description=f"Тип: {query_analysis['type']}, Сложность: {query_analysis['complexity']}",
                thumb="https://img.icons8.com/fluency/48/search.png"
            )
        ]

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Предварительный анализ запроса"""
        # Определение типа запроса
        query_type = 'unknown'
        if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', query):
            query_type = 'email'
        elif re.match(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$', query):
            query_type = 'phone'
        elif re.match(r'^[A-Za-zА-Яа-я]+ [A-Za-zА-Яа-я]+', query):
            query_type = 'name'
        
        # Оценка сложности
        words = query.split()
        complexity = min(max(len(words) * 5, 1), 40)
        
        return {
            'type': query_type,
            'complexity': complexity,
            'words_count': len(words)
        }

    @loader.command(ru_doc="🔐 Настройка конфигурации LeakOsint")
    async def osintconfig(self, message):
        """Расширенная настройка модуля"""
        args = utils.get_args_raw(message)
        
        if not args:
            # Показ текущей конфигурации
            config_text = (
                "🛠️ <b>Текущая конфигурация LeakOsint:</b>\n\n"
                f"🔑 API Токен: {'✅ Установлен' if self.config['api_token'] else '❌ Не установлен'}\n"
                f"🔢 Лимит поиска: {self.config['default_limit']}\n"
                f"🌐 Язык: {self.config['default_lang']}\n"
                f"🕳️ Глубина поиска: {self.config['max_depth']}"
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
                return await utils.answer(message, "❌ Неверный параметр конфигурации")
            
            await utils.answer(message, self.strings["config_updated"])
        except Exception as e:
            await utils.answer(message, f"❌ Ошибка настройки: {str(e)}")

    @loader.command(ru_doc="🔍 Расширенный поиск информации")
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
        
        async with self._client.request('POST', url, json=data) as resp:
            return await resp.json()

    async def _format_and_send_results(self, message, response):
        """Красивое форматирование и отправка результатов"""
        if "Error code" in response:
            return await utils.answer(message, f"❌ Ошибка API: {response.get('Error code', 'Неизвестная ошибка')}")

        results = response.get("List", {})
        
        if not results or list(results.keys()) == ["No results found"]:
            return await utils.answer(message, self.strings["no_results"])

        formatted_results = []
        for db_name, db_info in results.items():
            if db_name == "No results found":
                continue

            db_section = f"🌐 <b>{db_name}</b>\n"
            db_section += f"📋 {db_info.get('InfoLeak', 'Без дополнительной информации')}\n\n"

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
            return '✉️'
        elif 'phone' in key_lower or 'tel' in key_lower:
            return '📱'
        elif 'name' in key_lower:
            return '👤'
        elif 'address' in key_lower:
            return '🏠'
        elif 'date' in key_lower:
            return '📅'
        else:
            return '🔹'

    async def _send_long_message(self, chat_id, text, max_length=4096):
        """Отправляет длинные сообщения частями"""
        while text:
            chunk = text[:max_length]
            await self._client.send_message(chat_id, chunk, parse_mode='html')
            text = text[max_length:]

    @loader.command(ru_doc="📜 История поиска")
    async def osinthistory(self, message):
        """Показать историю поисковых запросов"""
        if not self._search_history:
            return await utils.answer(message, "🕳️ История поиска пуста")
        
        history_text = "🔍 <b>История поиска:</b>\n\n"
        for entry in self._search_history[-10:]:  # Последние 10 записей
            history_text += (
                f"🕰️ {utils.format_time(entry['timestamp'])}\n"
                f"🔎 Запрос: {entry['query']}\n"
                f"📊 Результатов: {entry['results_count']}\n\n"
            )
        
        await utils.answer(message, history_text)

    @loader.command(ru_doc="🧹 Очистить историю")
    async def osintclear(self, message):
        """Очистить историю поиска и логи ошибок"""
        self._search_history.clear()
        self._error_log.clear()
        await utils.answer(message, self.strings["search_history"])

def generate_invite_link(bot_username="@LeakOsintBot"):
    """Генерирует пригласительную ссылку на бота"""
    return f"https://t.me/{bot_username.replace('@', '')}"
