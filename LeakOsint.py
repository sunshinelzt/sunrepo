# meta developer: @sunshinelzt

import asyncio
import logging
import random
import re
from typing import Dict, List, Optional

import aiohttp
from telethon import events, Button
from .. import loader, utils

class LeakOsintMod(loader.Module):
    """Продвинутый OSINT модуль с расширенной безопасностью и функциональностью"""
    
    strings = {
        "name": "LeakOsint",
        "no_access": "🚫 Доступ запрещен",
        "working": "🔍 Поиск по запросу: <b>{query}</b>",
        "no_results": "❌ Ничего не найдено по запросу: <b>{query}</b>",
        "error": "⚠️ Ошибка: {error}",
        "invalid_token": "🔒 Некорректный API-токен",
        "rate_limit": "⏳ Превышен лимит запросов"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "bot_name", "@YouLeakOsint_bot", "Имя бота для API",
            "api_token", "", "API-токен",
            "api_url", "https://leakosintapi.com/", "URL API",
            "limit", 100, "Лимит результатов (100-10000)",
            "lang", "ru", "Язык результатов",
            "timeout", 30, "Время ожидания запроса (сек)"
        )
        self.reports_cache = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _validate_query(self, query: str) -> bool:
        """Валидация поискового запроса"""
        if not query or len(query) < 2 or len(query) > 100:
            return False
        
        # Безопасный шаблон для поиска
        safe_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z0-9\s\-\.]+$')
        return bool(safe_pattern.match(query))

    async def _safe_api_request(self, payload: Dict) -> Dict:
        """Безопасный асинхронный запрос к API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config["api_url"], 
                    json=payload, 
                    timeout=aiohttp.ClientTimeout(total=self.config["timeout"])
                ) as response:
                    if response.status != 200:
                        self.logger.error(f"API Error: {response.status}")
                        return {"error": f"HTTP {response.status}"}
                    
                    return await response.json()
        
        except asyncio.TimeoutError:
            self.logger.warning("API Request Timeout")
            return {"error": self.strings["rate_limit"]}
        
        except Exception as e:
            self.logger.error(f"API Request Error: {e}")
            return {"error": str(e)}

    @loader.command()
    async def osint(self, message):
        """Выполнить OSINT-поиск"""
        query = utils.get_args_raw(message)
        
        if not query:
            return await message.edit("❓ Укажите запрос для поиска")
        
        if not await self._validate_query(query):
            return await message.edit("⚠️ Некорректный формат запроса")

        if not self.config["api_token"]:
            return await message.edit(self.strings["invalid_token"])

        await message.edit(self.strings["working"].format(query=query))
        
        payload = {
            "bot_name": self.config["bot_name"],
            "token": self.config["api_token"],
            "request": query,
            "limit": max(100, min(self.config["limit"], 10000)),
            "lang": self.config["lang"]
        }
        
        response = await self._safe_api_request(payload)
        
        if "error" in response:
            return await message.edit(self.strings["error"].format(error=response["error"]))

        if not response.get("List") or "No results found" in response["List"]:
            return await message.edit(self.strings["no_results"].format(query=query))

        query_id = str(random.randint(1000, 9999))
        self.reports_cache[query_id] = self._format_reports(response)

        await self._send_report(message, query_id, 0)

    async def _send_report(self, message, query_id, page):
        """Отправка страницы отчета с навигацией"""
        report_pages = self.reports_cache.get(query_id, [])
        if not report_pages:
            return await message.edit(self.strings["error"].format(error="Кэш отчётов пуст"))

        page = max(0, min(page, len(report_pages) - 1))
        
        keyboard = [
            [
                Button.inline("⬅️ Назад", f"osint_prev:{query_id}:{page-1}") if page > 0 else None,
                Button.inline("➡️ Вперёд", f"osint_next:{query_id}:{page+1}") if page < len(report_pages) - 1 else None
            ],
            [Button.inline("🗑️ Удалить", f"osint_delete:{query_id}")]
        ]
        
        # Фильтрация None из кнопок
        keyboard = [btn for btn in keyboard if any(btn)]
        
        await message.edit(report_pages[page], buttons=keyboard, parse_mode="html")

    @loader.callback("osint_prev", "osint_next")
    async def _paginate(self, call):
        """Постраничная навигация по результатам"""
        _, query_id, page = call.data.decode().split(":")
        page = int(page)
        await self._send_report(call, query_id, page)

    @loader.callback("osint_delete")
    async def _delete_report(self, call):
        """Удаление кэша отчета"""
        query_id = call.data.decode().split(":")[1]
        if query_id in self.reports_cache:
            del self.reports_cache[query_id]
        await call.delete()

    def _format_reports(self, response: Dict) -> List[str]:
        """Форматирование результатов поиска"""
        formatted_reports = []

        for db_name, db_data in response.get("List", {}).items():
            if db_name == "No results found":
                continue

            header = f"<b>📊 База данных: {db_name}</b>\n\n"
            leak_info = f"🗂️ <u>{db_data.get('InfoLeak', 'Информация о leaked данных')}</u>\n\n"

            details = []
            for record in db_data.get("Data", []):
                record_info = "\n".join(f"🔹 <b>{key}</b>: {value}" for key, value in record.items())
                details.append(record_info)

            full_report = header + leak_info + "\n\n".join(details)
            
            # Разбиение длинных отчетов на части
            for chunk in self._split_long_message(full_report):
                formatted_reports.append(chunk)

        return formatted_reports

    def _split_long_message(self, text: str, max_length: int = 4000) -> List[str]:
        """Разделение длинных сообщений на части"""
        return [text[i:i+max_length] for i in range(0, len(text), max_length)]
