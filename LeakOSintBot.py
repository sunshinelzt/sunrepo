# meta developer @sunshinelzt

from hikka import loader, utils
import requests
import asyncio
from random import randint

class LeakOSintBot(loader.Module):
    """Мощный бот для работы с LeakOSint API с высокой функциональностью и улучшенной обработкой данных."""

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
            "REPORT_TYPE", "json", "Тип отчёта (json, short, html)",
            "BOT_NAME", "", "Имя бота в формате @name (если необходимо)"
        )
        self.cash_reports = {}
        self.session = requests.Session()

    async def leakcmd(self, message):
        """Запуск поиска через API LeakOsint. Использование: .leak запрос"""
        await self._process_leak(message)

    async def _process_leak(self, message):
        args = utils.get_args_raw(message)
        if not args:
            await message.edit(self.strings["no_query"])
            return

        query_id = randint(0, 9999999)
        report = await self._generate_report(args, query_id)

        if not report:
            await message.edit(self.strings["api_error"])
            return

        await message.edit(self.strings["report_started"])

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
        report_type = self.config["REPORT_TYPE"]
        bot_name = self.config["BOT_NAME"]

        if not api_token:
            await message.edit(self.strings["invalid_token"])
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
                await message.edit(self.strings["api_error"])
                return None

            report = self._parse_report(response)
            if not report:
                await message.edit(self.strings["empty_results"])
                return None

            # Проверка на превышение лимита
            if len(report) > limit:
                await message.edit(self.strings["limit_exceeded"])
                return None

            return report
        except Exception as e:
            await message.edit(self.strings["report_error"])
            print(f"Error: {e}")
            return None

    async def _fetch_data(self, url, data):
        """Асинхронная функция для отправки запросов и получения данных."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.session.post(url, json=data).json())
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def _parse_report(self, response):
        """Парсинг данных отчёта из API."""
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

    async def stopleakcmd(self, message):
        """Останавливает все активные задачи поиска"""
        await self._stop_spam(message)

    async def _stop_spam(self, message):
        self.cash_reports.clear()
        await message.edit(self.strings["stopped"])

client = loader.Client()
client.run()
