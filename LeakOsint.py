# meta developer: @sunshinelzt
# писядвапися

import aiohttp
import json
from telethon import Button
from hikka import loader
import os

class LeakOsintMod(loader.Module):
    """Модуль для обработки и вывода данных с дополнительной информацией и улучшенным оформлением"""

    strings = {
        "name": "LeakOsint",
        "working": "🔍 <b>Поиск по запросу:</b> <i>{query}</i>",
        "no_results": "❌ <b>Ничего не найдено по запросу:</b> <i>{query}</i>",
        "error": "⚠️ <b>Ошибка:</b> {error}",
        "rate_limit": "⏳ <b>Превышен лимит запросов, попробуйте позже.</b>",
        "invalid_token": "🔒 <b>Некорректный API-токен, проверьте настройки.</b>",
        "no_query": "❌ Пожалуйста, укажите запрос для поиска.",
        "data_found": "✅ <b>Данные найдены:</b> <i>{count}</i> результатов.",
        "choose_format": "🎨 💬 <b>Выберите формат вывода данных:</b>",
        "format_changed": "✅ <b>Формат вывода успешно изменён на:</b> <b>{format}</b>",
        "user_info": "👤 <b>Искомый пользователь:</b> {user}",
        "query_info": "🔍 <b>Запрос:</b> {query}",
        "data_info": "📊 <b>Количество найденных данных:</b> <i>{count}</i>",
        "file_info": "📁 <b>Файл с результатами готов:</b> {file_name}",
    }

    def __init__(self):
        # Настройки
        self.config = {
            "api_url": "https://your.api/endpoint",  # Замените на ваш API-URL
            "api_key": "your_api_key_here",  # Ваш API ключ
            "output_format": "html",  # Формат вывода по умолчанию: html
        }

    async def _safe_api_request(self, payload: dict) -> dict:
        """Безопасный асинхронный запрос к API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(self.config["api_url"], json=payload, headers=headers) as response:
                    if response.status != 200:
                        return {"error": f"HTTP {response.status}"}
                    return await response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _format_as_html(self, data: dict, query: str, user: str, result_count: int) -> str:
        """Форматирует данные в HTML с добавлением информации о запросе и улучшенным оформлением"""
        html_content = f"<html><body style='font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;'>"
        html_content += f"<h1 style='color: #4CAF50; text-align: center;'>🔍 <u>Результаты поиска</u></h1>"
        html_content += f"<p style='font-size: 16px;'>🎯 <b>Запрос:</b> {query}</p>"
        html_content += f"<p style='font-size: 16px;'>👤 <b>Искомый пользователь:</b> {user}</p>"
        html_content += f"<p style='font-size: 16px;'>📊 <b>Количество найденных данных:</b> {result_count}</p>"
        html_content += "<ul style='list-style: none; padding: 0; font-size: 14px;'>"
        
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 5:  # Выводим строки
                html_content += f"<li style='padding: 8px; margin-bottom: 6px; background: #e7f9e7; border-radius: 5px;'>"
                html_content += f"<b>{key.capitalize()}:</b> <i>{value}</i></li>"
        
        html_content += "</ul><br><hr>"
        html_content += "<footer style='text-align: center; font-size: 14px; color: #888;'>"
        html_content += "© 2025 LeakOsint. Все права защищены.</footer></body></html>"
        return html_content

    async def _format_as_json(self, data: dict, query: str, user: str, result_count: int) -> str:
        """Форматирует данные в JSON с добавлением информации о запросе"""
        result = {
            "query": query,
            "user": user,
            "result_count": result_count,
            "data": data
        }
        return json.dumps(result, indent=4, ensure_ascii=False)

    async def _format_as_txt(self, data: dict, query: str, user: str, result_count: int) -> str:
        """Форматирует данные в TXT с добавлением информации о запросе"""
        txt_content = f"🔍 Запрос: {query}\n"
        txt_content += f"👤 Искомый пользователь: {user}\n"
        txt_content += f"📊 Количество найденных данных: {result_count}\n\n"
        
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 5:  # Выводим строки
                txt_content += f"{key.capitalize()}: {value}\n"
        
        return txt_content

    async def _generate_buttons(self, data: dict) -> list:
        """Генерирует кнопки для каждого типа данных с красивым оформлением"""
        buttons = []
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 5:  # Для данных типа строки
                buttons.append([Button.inline(f"📋 {key.capitalize()}: {value[:20]}...", data=key)])
        buttons.append([Button.inline("🔎 Получить все данные", data="all_data")])
        return buttons

    @loader.command()
    async def leak(self, message):
        """Команда для поиска информации по запросу"""
        query = message.text.split(" ", 1)[1]

        if not query:
            await message.reply(self.strings["no_query"])
            return

        # Получаем данные о пользователе
        user = message.sender.username if message.sender.username else message.sender.id
        
        # Формат по умолчанию
        output_format = self.config["output_format"]
        
        # Делаем запрос
        payload = {"query": query}
        data = await self._safe_api_request(payload)

        if "error" in data:
            await message.reply(self.strings["error"].format(error=data["error"]))
            return

        # Получаем количество данных
        result_count = len(data)

        # Форматируем данные в нужном формате
        if output_format == "html":
            formatted_data = await self._format_as_html(data, query, user, result_count)
        elif output_format == "json":
            formatted_data = await self._format_as_json(data, query, user, result_count)
        elif output_format == "txt":
            formatted_data = await self._format_as_txt(data, query, user, result_count)

        # Отправляем информацию в чат о том, кого искали, сколько данных найдено
        await message.reply(self.strings["query_info"].format(query=query))
        await message.reply(self.strings["user_info"].format(user=user))
        await message.reply(self.strings["data_info"].format(count=result_count))

        # Генерация кнопок
        buttons = await self._generate_buttons(data)
        await message.reply(self.strings["choose_format"], buttons=buttons)

        # Сохраняем данные в файл
        file_name = f"output.{output_format}"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(formatted_data)

        # Отправляем файл
        await message.reply(self.strings["file_info"].format(file_name=file_name), file=f"output.{output_format}", caption="🔍 Результаты поиска")

    @loader.command()
    async def setformat(self, message):
        """Команда для настройки формата вывода данных"""
        format_choice = message.text.split(" ", 1)[1].lower()

        if format_choice not in ["html", "json", "txt"]:
            await message.reply("❌ Неверный формат. Доступные форматы: html, json, txt.")
            return

        # Сохраняем выбранный формат
        self.config["output_format"] = format_choice
        await message.reply(self.strings["format_changed"].format(format=format_choice.upper()))
