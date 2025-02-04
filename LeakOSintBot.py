# meta developer @sunshinelzt

from hikka import loader, utils
import asyncio
import requests
import json
from random import randint
import logging

class LeakOSintBot(loader.Module):
    """Интерактивный и мощный бот для работы с LeakOsint API."""

    strings = {
        "name": "LeakOSintBot",
        "no_query": "❌ Пожалуйста, укажите запрос для поиска.",
        "api_error": "❌ Произошла ошибка при запросе к API. Попробуйте позже.",
        "report_started": "✅ Начинаю обработку запроса. Пожалуйста, подождите...",
        "report_success": "✅ Отчёт успешно сгенерирован и отправлен.",
        "report_error": "❌ Ошибка при обработке данных. Проверьте запрос и попробуйте снова.",
        "stopped": "🛑 Все запросы остановлены.",
        "invalid_token": "❌ Токен API недействителен или не был указан в конфигурации.",
        "empty_results": "❌ Нет результатов для вашего запроса.",
        "limit_exceeded": "❌ Превышен лимит результатов. Попробуйте уточнить запрос.",
        "invalid_query": "❌ Некорректный запрос. Пожалуйста, попробуйте снова.",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_TOKEN", "", "Токен API для LeakOsint",
            "LANG", "ru", "Язык запросов по умолчанию",
            "LIMIT", 300, "Лимит на количество данных",
            "TYPE", "json", "Тип отчёта (json, short, html)",
            "BOT_NAME", "", "Имя бота (необходимо, если бот не в основной группе зеркал)",
            "LOG_LEVEL", "ERROR", "Уровень логирования (DEBUG, INFO, WARNING, ERROR)"
        )
        self.cash_reports = {}
        self.session = requests.Session()
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Настроить логирование для минимизации засорения."""
        logger = logging.getLogger("LeakOSintBot")
        log_level = getattr(logging, self.config["LOG_LEVEL"].upper(), logging.ERROR)
        logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    async def leakcmd(self, message):
        """Запуск поиска через API LeakOsint. Использование: .leak запрос"""
        await self._process_leak(message)

    async def _process_leak(self, message):
        args = utils.get_args_raw(message)
        if not args:
            await message.edit(self.strings["no_query"])
            return

        query_id = randint(0, 9999999)
        await message.edit(self.strings["report_started"])

        report = await self._generate_report(args, query_id)

        if not report:
            await message.edit(self.strings["api_error"])
            return

        if not report:
            await message.edit(self.strings["empty_results"])
            return

        # Отправка отчётов по частям (если нужно)
        for page_id, report_text in enumerate(report):
            await message.respond(report_text, parse_mode="html")

        self.cash_reports[str(query_id)] = report
        await message.edit(self.strings["report_success"])

    async def _generate_report(self, query, query_id):
        """Асинхронная функция для генерации отчётов с использованием API."""
        url = "https://leakosintapi.com/"
        api_token = self.config["API_TOKEN"]
        lang = self.config["LANG"]
        limit = self.config["LIMIT"]
        report_type = self.config["TYPE"]
        bot_name = self.config["BOT_NAME"]

        if not api_token:
            self.logger.warning("API Token is missing or invalid.")
            await self._send_error_message(query_id, self.strings["invalid_token"])
            return None

        data = {
            "token": api_token,
            "request": query,
            "limit": limit,
            "lang": lang,
            "type": report_type,
            "bot_name": bot_name
        }

        try:
            response = await self._fetch_data(url, data)
            if not response:
                await self._send_error_message(query_id, self.strings["api_error"])
                return None

            report = await self._process_api_response(response)

            if len(report) > limit:
                await self._send_error_message(query_id, self.strings["limit_exceeded"])
                return None

            return report
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            await self._send_error_message(query_id, self.strings["api_error"])
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            await self._send_error_message(query_id, self.strings["report_error"])
            return None

    async def _process_api_response(self, response):
        """Обработка данных, полученных от API."""
        report = []
        for database_name, data in response.get("List", {}).items():
            text = [f"<b>{database_name}</b>", ""]
            text.append(data.get("InfoLeak", "") + "\n")

            if database_name != "No results found":
                for report_data in data.get("Data", []):
                    for column_name, value in report_data.items():
                        text.append(f"<b>{column_name}</b>: {value}")
                    text.append("")
            text = "\n".join(text)

            # Обработка слишком длинных сообщений
            if len(text) > 3500:
                text = text[:3500] + text[3500:].split("\n")[0] + "\n\nНекоторые данные не поместились в это сообщение"
            report.append(text)

        return report

    async def _send_error_message(self, query_id, message_text):
        """Отправка сообщения об ошибке пользователю."""
        self.logger.warning(f"Sending error message: {message_text}")
        await self._send_message(query_id, message_text)
        return None

    async def _send_message(self, query_id, message_text):
        """Отправка сообщения пользователю."""
        if query_id in self.cash_reports:
            for text in self.cash_reports[str(query_id)]:
                await utils.answer(text)
        await utils.answer(message_text)

    async def _fetch_data(self, url, data):
        """Асинхронная функция для отправки запросов и получения данных."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.session.post(url, json=data).json())
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None

    async def stopleakcmd(self, message):
        """Останавливает все активные задачи поиска"""
        await self._stop_spam(message)

    async def _stop_spam(self, message):
        self.cash_reports.clear()
        await message.edit(self.strings["stopped"])

client = loader.Client()
client.run()
