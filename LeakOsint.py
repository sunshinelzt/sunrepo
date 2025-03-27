# meta developer: @sunshinelzt
# писядвапися

import asyncio
import logging
from typing import Dict, List

import aiohttp
from .. import loader, utils


class LeakOsintMod(loader.Module):
    """Расширенный OSINT модуль для поиска любых утечек"""

    strings = {
        "name": "LeakOsint",
        "working": "🔍 Выполняется поиск по запросу: <b>{query}</b>",
        "no_results": "❌ Ничего не найдено по запросу: <b>{query}</b>",
        "error": "⚠️ Ошибка: {error}",
        "invalid_token": "🔒 Некорректный API-токен",
        "rate_limit": "⏳ Превышен лимит запросов",
    }

    IMPORTANT_FIELDS = [
        "email", "phone", "password", "login", "ip", "address",
        "username", "card", "hash", "birthdate", "token", "domain"
    ]

    def __init__(self):
        self.config = loader.ModuleConfig(
            "bot_name", "@YouLeakOsint_bot", "Имя бота для API",
            "api_token", "", "API-токен для доступа к LeakOsint",
            "api_url", "https://leakosintapi.com/", "URL API для запросов",
            "limit", 500, "Максимальное количество результатов (100-10000)",
            "lang", "ru", "Язык ответа от API",
            "timeout", 40, "Таймаут запроса (в секундах)"
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _api_request(self, payload: Dict) -> Dict:
        """Выполнение безопасного асинхронного запроса к API"""
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
        """Выполнить OSINT-поиск по любому запросу"""
        query = utils.get_args_raw(message)

        if not query:
            return await message.edit("❓ Укажите запрос для поиска")

        if not self.config["api_token"]:
            return await message.edit(self.strings["invalid_token"])

        await message.edit(self.strings["working"].format(query=query))

        payload = {
            "bot_name": self.config["bot_name"],
            "token": self.config["api_token"],
            "request": query,
            "limit": max(100, min(self.config["limit"], 10000)),
            "lang": self.config["lang"],
        }

        response = await self._api_request(payload)

        if "error" in response:
            return await message.edit(self.strings["error"].format(error=response["error"]))

        if not response.get("List") or "No results found" in response["List"]:
            return await message.edit(self.strings["no_results"].format(query=query))

        formatted_report = self._format_reports(response)

        if not formatted_report:
            return await message.edit(self.strings["no_results"].format(query=query))

        await self._send_report(message, formatted_report)

    async def _send_report(self, message, report):
        """Отправка отчета с разбиением на части"""
        report_chunks = self._split_long_message(report)

        for chunk in report_chunks:
            await message.respond(chunk, parse_mode="html")

    def _format_reports(self, response: Dict) -> str:
        """Форматирование отчета с важной информацией"""
        report_parts = []

        for db_name, db_data in response.get("List", {}).items():
            if db_name == "No results found":
                continue

            header = f"📊 <b>{db_name}</b>\n"
            leak_info = f"🗂️ <i>{db_data.get('InfoLeak', 'Информация отсутствует')}</i>\n\n"

            details = []
            for record in db_data.get("Data", []):
                # Фильтруем только важные данные
                important_data = {
                    key: value for key, value in record.items()
                    if key.lower() in self.IMPORTANT_FIELDS and value
                }

                if important_data:
                    record_info = "\n".join(f"🔹 <b>{key.capitalize()}</b>: {value}"
                                            for key, value in important_data.items())
                    details.append(record_info)

            if details:
                report_parts.append(f"{header}{leak_info}\n" + "\n\n".join(details) + "\n")

        if not report_parts:
            return ""

        # Соединяем отчет и ограничиваем длину
        full_report = "\n".join(report_parts)
        return full_report[:15000]

    def _split_long_message(self, text: str, max_length: int = 4096) -> List[str]:
        """Разбиение длинных сообщений на части"""
        return [text[i:i + max_length] for i in range(0, len(text), max_length)]
