# ---------------------------------------------------------------------------------
# | ChatAnalyzer module for Hikka Userbot
# | Author: Claude AI
# | Description: Улучшенный модуль анализа чатов с интеграцией различных AI-моделей
# ---------------------------------------------------------------------------------

__version__ = (1, 0, 0)

# meta developer: @sunshinelzt

import asyncio
import aiohttp
import logging
import re
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

from telethon.tl.types import Message, User, Chat, Channel
from telethon.tl.functions.messages import GetHistoryRequest
from telethon import errors

from .. import loader, utils
from ..inline.types import InlineQuery
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)

# Добавляем константы для работы модуля
DEFAULT_HISTORY_LIMIT = 100
MAX_HISTORY_LIMIT = 500
DEFAULT_WAIT_TIME = 60  # Время ожидания между запросами в секундах
AI_MODELS = ["gemini", "openai", "anthropic"]

@loader.tds
class ChatAnalyzerMod(loader.Module):
    """Расширенный анализ сообщений чата с помощью AI-моделей"""
    
    strings = {
        "name": "ChatAnalyzer",
        "no_api_key": "<b>❌ API ключ не установлен. Используйте </b><code>.config ChatAnalyzer</code>",
        "api_key_set": "<b>✅ API ключ успешно установлен</b>",
        "collecting_history": "<b>📊 Собираю историю сообщений пользователя <code>{}</code>...</b>",
        "collecting_chat": "<b>📊 Собираю историю сообщений всего чата...</b>",
        "processing": "<b>🧠 {}</b>",
        "error": "<b>❌ Произошла ошибка: {}</b>",
        "user_analysis_title": "<b>🔍 Анализ сообщений пользователя {}</b>",
        "chat_analysis_title": "<b>🔍 Анализ чата</b>",
        "mood_analysis_title": "<b>😊 Анализ настроения чата</b>",
        "topic_analysis_title": "<b>📋 Тематический анализ</b>",
        "no_messages": "<b>❌ Сообщения не найдены</b>",
        "rate_limited": "<b>⏳ Слишком много запросов. Пожалуйста, подождите {} секунд</b>",
        "settings_saved": "<b>✅ Настройки успешно сохранены</b>",
        "model_set": "<b>✅ Модель ИИ изменена на: {}</b>",
        "limit_set": "<b>✅ Лимит истории установлен на: {}</b>",
        "invalid_limit": "<b>❌ Некорректный лимит. Должен быть от 10 до 500</b>",
        "help_text": """
<b>📌 Использование модуля ChatAnalyzer:</b>

<code>.cahelp</code> - показать эту справку
<code>.caconfig</code> - настройка модуля через инлайн-меню
<code>.ca [число]</code> - анализ всего чата (опционально укажите количество сообщений)
<code>.ca </code><i>(ответ на сообщение)</i> - анализ сообщений конкретного пользователя
<code>.camood</code> - анализ общего настроения чата
<code>.catopic</code> - анализ основных тем обсуждения
<code>.caset [модель]</code> - быстрая смена AI-модели (gemini/openai/anthropic)
"""
    }
    
    strings_ru = strings
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "gemini_api_key", "", "API ключ для Google Gemini",
            "openai_api_key", "", "API ключ для OpenAI",
            "anthropic_api_key", "", "API ключ для Anthropic Claude",
            "history_limit", DEFAULT_HISTORY_LIMIT, "Сколько сообщений анализировать",
            "active_model", "gemini", f"Модель ИИ для использования ({'/'.join(AI_MODELS)})",
            "include_media", True, "Включать медиа-файлы в анализ",
            "include_links", True, "Включать ссылки в анализ",
            "emojis_enabled", True, "Добавлять эмодзи в результаты",
            "auto_translate", False, "Автоматически переводить иностранные сообщения"
        )
        self.name = self.strings["name"]
        # Добавляем словарь для отслеживания запросов
        self.last_requests = {}
    
    async def client_ready(self, client, db):
        """Вызывается при готовности модуля"""
        self.client = client
        self.db = db
        # Инициализируем хранилище данных для модуля
        self._db = self.db.get(self.name, {
            "user_stats": {},
            "chat_stats": {},
            "request_history": []
        })
        # Регистрируем обработчики для инлайн-меню
        self.inline = self.client.loader.inline
        
    def get_active_api_key(self) -> Optional[str]:
        """Получает активный API-ключ в зависимости от выбранной модели"""
        model = self.config["active_model"]
        if model == "gemini":
            return self.config["gemini_api_key"]
        elif model == "openai":
            return self.config["openai_api_key"]
        elif model == "anthropic":
            return self.config["anthropic_api_key"]
        return None
    
    async def _check_rate_limit(self, chat_id: int) -> Optional[int]:
        """Проверяет, не превышен ли лимит запросов"""
        current_time = time.time()
        if chat_id in self.last_requests:
            time_diff = current_time - self.last_requests[chat_id]
            if time_diff < DEFAULT_WAIT_TIME:
                return int(DEFAULT_WAIT_TIME - time_diff)
        self.last_requests[chat_id] = current_time
        return None
    
    async def _collect_messages(
        self, 
        chat_id: int, 
        limit: int, 
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Собирает сообщения из чата с расширенными данными"""
        all_messages = []
        total_collected = 0
        
        try:
            async for msg in self.client.iter_messages(chat_id, limit=limit * 2):  # Увеличиваем лимит для компенсации фильтров
                if total_collected >= limit:
                    break
                
                if not msg or getattr(msg, "action", None) or not msg.sender:
                    continue
                
                # Пропускаем сообщения от ботов
                if getattr(msg.sender, "bot", False):
                    continue
                    
                # Фильтр по пользователю, если указан
                if user_id and msg.sender.id != user_id:
                    continue
                
                # Получаем имя отправителя
                sender_name = getattr(msg.sender, "first_name", "Unknown")
                if hasattr(msg.sender, "last_name") and msg.sender.last_name:
                    sender_name += f" {msg.sender.last_name}"
                
                # Обрабатываем текст сообщения
                msg_text = msg.text if msg.text else ""
                
                # Обрабатываем разные типы медиа
                media_type = None
                if not msg_text and hasattr(msg, "media"):
                    if hasattr(msg.media, "photo"):
                        media_type = "фото"
                    elif hasattr(msg.media, "document"):
                        if getattr(msg.media.document, "mime_type", "").startswith("video"):
                            media_type = "видео"
                        elif getattr(msg.media.document, "mime_type", "").startswith("audio"):
                            media_type = "аудио"
                        else:
                            media_type = "файл"
                    elif hasattr(msg.media, "webpage"):
                        media_type = "ссылка"
                        if hasattr(msg.media.webpage, "title"):
                            msg_text = f"[{msg.media.webpage.title}]"
                        
                # Добавляем информацию о медиа, если нужно
                if media_type and self.config["include_media"]:
                    if not msg_text:
                        msg_text = f"[{media_type}]"
                    else:
                        msg_text += f" + [{media_type}]"
                
                # Если нет текста, переходим к следующему сообщению
                if not msg_text and not media_type:
                    continue
                
                # Формируем данные о сообщении
                message_data = {
                    "sender_id": msg.sender.id,
                    "sender": sender_name,
                    "username": getattr(msg.sender, "username", None),
                    "date": msg.date,
                    "time": msg.date.strftime("%d.%m %H:%M:%S"),
                    "text": msg_text,
                    "media_type": media_type,
                    "reply_to": None,
                    "forwarded": bool(getattr(msg, "forward", None))
                }
                
                # Добавляем информацию о том, на какое сообщение это ответ
                if msg.reply_to and msg.reply_to.reply_to_msg_id:
                    message_data["reply_to"] = msg.reply_to.reply_to_msg_id
                
                all_messages.append(message_data)
                total_collected += 1
                
            # Сортируем сообщения по времени
            all_messages.sort(key=lambda x: x["date"])
            
            # Собираем статистику в фоне для будущих запросов
            asyncio.create_task(self._update_stats(chat_id, all_messages))
            
            return all_messages
            
        except Exception as e:
            logger.exception(f"Ошибка при сборе сообщений: {e}")
            return []
    
    async def _update_stats(self, chat_id: int, messages: List[Dict[str, Any]]):
        """Обновляет статистику чата для будущих запросов"""
        if not messages:
            return
            
        chat_stats = self._db.get("chat_stats", {})
        if chat_id not in chat_stats:
            chat_stats[chat_id] = {
                "total_messages": 0,
                "active_users": {},
                "message_times": {},
                "topics": {}
            }
            
        # Обновляем общую статистику
        for msg in messages:
            sender_id = msg["sender_id"]
            
            # Увеличиваем счетчик сообщений
            chat_stats[chat_id]["total_messages"] += 1
            
            # Обновляем активных пользователей
            if sender_id not in chat_stats[chat_id]["active_users"]:
                chat_stats[chat_id]["active_users"][sender_id] = {
                    "name": msg["sender"],
                    "count": 0,
                    "username": msg["username"]
                }
            chat_stats[chat_id]["active_users"][sender_id]["count"] += 1
            
            # Обновляем время сообщений (по часам)
            hour = msg["date"].hour
            if hour not in chat_stats[chat_id]["message_times"]:
                chat_stats[chat_id]["message_times"][hour] = 0
            chat_stats[chat_id]["message_times"][hour] += 1
                
        # Сохраняем обновленную статистику
        self._db["chat_stats"] = chat_stats
        self.db.set(self.name, self._db)
        
    async def _process_ai_query(self, prompt: str) -> str:
        """Обрабатывает запрос к выбранной AI-модели"""
        api_key = self.get_active_api_key()
        if not api_key:
            return "Ошибка: API ключ не установлен"
            
        model = self.config["active_model"]
        
        try:
            if model == "gemini":
                return await self._process_gemini_query(prompt)
            elif model == "openai":
                return await self._process_openai_query(prompt)
            elif model == "anthropic":
                return await self._process_anthropic_query(prompt)
            else:
                return f"Ошибка: неизвестная модель {model}"
        except Exception as e:
            logger.exception(f"Ошибка при обработке запроса к AI: {e}")
            return f"Ошибка при обработке запроса: {str(e)}"
    
    async def _process_gemini_query(self, prompt: str) -> str:
        """Обрабатывает запрос к модели Google Gemini"""
        api_key = self.config["gemini_api_key"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048
                    }
                }
            ) as response:
                if response.status != 200:
                    error_msg = await response.text()
                    return f"Ошибка API Gemini ({response.status}): {error_msg}"
                
                result = await response.json()
                
                try:
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as e:
                    logger.exception(f"Ошибка при обработке ответа Gemini: {e}")
                    return "Ошибка при обработке ответа от API"
    
    async def _process_openai_query(self, prompt: str) -> str:
        """Обрабатывает запрос к модели OpenAI"""
        api_key = self.config["openai_api_key"]
        url = "https://api.openai.com/v1/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Ты аналитик сообщений из телеграм-чата. Твоя задача - анализировать сообщения и предоставлять содержательные выводы."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
            ) as response:
                if response.status != 200:
                    error_msg = await response.text()
                    return f"Ошибка API OpenAI ({response.status}): {error_msg}"
                
                result = await response.json()
                
                try:
                    return result["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as e:
                    logger.exception(f"Ошибка при обработке ответа OpenAI: {e}")
                    return "Ошибка при обработке ответа от API"
    
    async def _process_anthropic_query(self, prompt: str) -> str:
        """Обрабатывает запрос к модели Anthropic Claude"""
        api_key = self.config["anthropic_api_key"]
        url = "https://api.anthropic.com/v1/messages"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-instant-1.2",
                    "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                    "max_tokens_to_sample": 2048,
                    "temperature": 0.7
                }
            ) as response:
                if response.status != 200:
                    error_msg = await response.text()
                    return f"Ошибка API Anthropic ({response.status}): {error_msg}"
                
                result = await response.json()
                
                try:
                    return result["completion"]
                except KeyError as e:
                    logger.exception(f"Ошибка при обработке ответа Anthropic: {e}")
                    return "Ошибка при обработке ответа от API"
    
    async def _get_random_emoji(self) -> str:
        """Возвращает случайный эмодзи в зависимости от темы"""
        if not self.config["emojis_enabled"]:
            return ""
            
        analysis_emojis = ["🧠", "📊", "📈", "🔍", "💡", "🤔", "🧐", "📝", "📑", "📰"]
        mood_emojis = ["😊", "😄", "🥳", "😎", "😍", "🤩", "😌", "🤗", "👍", "✨"]
        topic_emojis = ["📋", "📌", "📚", "🗂️", "📁", "🧩", "🔖", "📎", "📔", "📘"]
        
        # Выбираем случайные эмодзи из всех категорий
        emojis = random.sample(analysis_emojis, 2) + random.sample(mood_emojis, 2) + random.sample(topic_emojis, 2)
        return " ".join(random.sample(emojis, 3))
    
    async def _generate_prompt(
        self,
        messages: List[Dict[str, Any]],
        analysis_type: str = "general",
        user_name: Optional[str] = None
    ) -> str:
        """Генерирует продвинутый промпт для AI на основе типа анализа"""
        if analysis_type == "user" and user_name:
            context = f"""Ты - продвинутый аналитик данных и психолог. Проанализируй сообщения пользователя {user_name} в телеграм-чате.

Задачи:
1. Составь психологический портрет пользователя на основе его сообщений
2. Выдели основные темы и интересы пользователя
3. Оцени общий тон и настроение сообщений
4. Определи, какие вопросы больше всего интересовали пользователя
5. Опиши стиль общения пользователя
6. В конце добавь остроумную шутку, связанную с интересами пользователя

Результат должен быть структурированным, содержательным и полезным."""

        elif analysis_type == "mood":
            context = """Ты - эксперт по анализу настроений и эмоций. Проанализируй настроение чата в Telegram.

Задачи:
1. Определи преобладающее настроение в чате
2. Найди пользователей с самыми позитивными и негативными сообщениями
3. Оцени изменение настроения на протяжении беседы
4. Выдели эмоциональные пики и спады
5. Определи, какие темы вызывают наибольший эмоциональный отклик
6. В конце предложи шутку или мем, подходящий к общему настроению чата

Стремись к точному эмоциональному анализу."""

        elif analysis_type == "topic":
            context = """Ты - эксперт по тематическому анализу и извлечению информации. Проанализируй темы обсуждения в телеграм-чате.

Задачи:
1. Выдели 3-5 основных тем обсуждения
2. Для каждой темы укажи ключевые слова и идеи
3. Определи, кто из пользователей больше всего заинтересован в каждой теме
4. Выяви связи между разными темами
5. Оцени глубину обсуждения каждой темы
6. В конце предложи интересную шутку на основе самой популярной темы

Стремись к точному и информативному анализу."""

        else:  # general analysis
            context = """Ты - продвинутый аналитик данных и психолог. Проанализируй сообщения телеграм-чата.

Задачи:
1. Выдели основные темы обсуждения в чате
2. Определи наиболее активных участников и их роли
3. Оцени общий тон и настроение беседы
4. Выяви интересные и необычные моменты в диалоге
5. Проанализируй динамику и структуру беседы
6. В конце предложи остроумную шутку на основе обсуждаемых тем

Результат должен быть структурированным, содержательным и полезным."""

        history_text = "\n".join([f"[{msg['time']}] {msg['sender']}: {msg['text']}" for msg in messages])
        
        # Добавляем статистическую информацию для улучшения анализа
        if messages:
            unique_users = len(set(msg["sender_id"] for msg in messages))
            date_range = f"с {messages[0]['time']} по {messages[-1]['time']}"
            stats = f"\nВсего сообщений: {len(messages)}\nУникальных пользователей: {unique_users}\nПериод: {date_range}"
        else:
            stats = "\nВ выборке нет сообщений для анализа."
            
        return f"{context}\n\nСтатистика:{stats}\n\nИстория сообщений:\n{history_text}"
    
    async def _create_inline_config(self, call: Optional[InlineCall] = None):
        """Создает инлайн-меню для конфигурации модуля"""
        buttons = [
            [
                {
                    "text": "🤖 Модель: " + self.config["active_model"].capitalize(),
                    "callback": self._inline_set_model
                }
            ],
            [
                {
                    "text": f"📊 Лимит: {self.config['history_limit']}",
                    "callback": self._inline_set_limit
                }
            ],
            [
                {
                    "text": "🖼 Медиа: " + ("✅" if self.config["include_media"] else "❌"),
                    "callback": self._inline_toggle_media
                },
                {
                    "text": "🔗 Ссылки: " + ("✅" if self.config["include_links"] else "❌"),
                    "callback": self._inline_toggle_links
                }
            ],
            [
                {
                    "text": "😊 Эмодзи: " + ("✅" if self.config["emojis_enabled"] else "❌"),
                    "callback": self._inline_toggle_emoji
                },
                {
                    "text": "🌐 Авто-перевод: " + ("✅" if self.config["auto_translate"] else "❌"),
                    "callback": self._inline_toggle_translate
                }
            ],
            [
                {
                    "text": "💾 Сохранить",
                    "callback": self._inline_save_config
                },
                {
                    "text": "❌ Закрыть",
                    "callback": self._inline_close
                }
            ]
        ]
        
        return self.inline.form(
            text=f"⚙️ <b>Настройки модуля {self.strings['name']}</b>",
            message=call.message if call else None,
            reply_markup=buttons
        )
    
    async def _inline_set_model(self, call: InlineCall):
        """Инлайн-обработчик для смены модели"""
        current_index = AI_MODELS.index(self.config["active_model"])
        next_index = (current_index + 1) % len(AI_MODELS)
        self.config["active_model"] = AI_MODELS[next_index]
        await self._create_inline_config(call)
    
    async def _inline_set_limit(self, call: InlineCall):
        """Инлайн-обработчик для установки лимита истории"""
        current = self.config["history_limit"]
        presets = [50, 100, 200, 300, 500]
        
        # Находим следующее значение
        for i, preset in enumerate(presets):
            if current < preset:
                self.config["history_limit"] = preset
                break
        else:
            # Если текущее значение >= последнего пресета, вернемся к первому
            self.config["history_limit"] = presets[0]
            
        await self._create_inline_config(call)
    
    async def _inline_toggle_media(self, call: InlineCall):
        """Инлайн-обработчик для переключения включения медиа"""
        self.config["include_media"] = not self.config["include_media"]
        await self._create_inline_config(call)
    
    async def _inline_toggle_links(self, call: InlineCall):
        """Инлайн-обработчик для переключения включения ссылок"""
        self.config["include_links"] = not self.config["include_links"]
        await self._create_inline_config(call)
    
    async def _inline_toggle_emoji(self, call: InlineCall):
        """Инлайн-обработчик для переключения использования эмодзи"""
        self.config["emojis_enabled"] = not self.config["emojis_enabled"]
        await self._create_inline_config(call)
    
    async def _inline_toggle_translate(self, call: InlineCall):
        """Инлайн-обработчик для переключения автоматического перевода"""
        self.config["auto_translate"] = not self.config["auto_translate"]
        await self._create_inline_config(call)
    
    async def _inline_save_config(self, call: InlineCall):
        """Инлайн-обработчик для сохранения конфигурации"""
        await call.edit(self.strings["settings_saved"])
    
    async def _inline_close(self, call: InlineCall):
        """Инлайн-обработчик для закрытия меню"""
        await call.delete()
    
    @loader.command(ru_doc="– помощь по модулю")
    async def cahelp(self, message: Message):
        """– show module help"""
        await utils.answer(message, self.strings["help_text"])
    
    @loader.command(ru_doc="– настройка модуля через инлайн-меню")
    async def caconfig(self, message: Message):
        """– configure module via inline menu"""
        await self._create_inline_config()
        await message.delete()
    
    @loader.command(ru_doc="– анализ сообщений чата [лимит сообщений или ответ на пользователя]")
    async def ca(self, message: Message):
        """– analyze chat messages [limit or reply to user]"""
        if not self.get_active_api_key():
            await utils.answer(message, self.strings["no_api_key"])
            return
        
        # Проверяем ограничение запросов
        wait_time = await self._check_rate_limit(message.chat_id)
        if wait_time:
            await utils.answer(message, self.strings["rate_limited"].format(wait_time))
            return
        
        # Парсим аргументы
        args = utils.get_args(message)
        limit = self.config["history_limit"]
        
        if args and args[0].isdigit():
            limit = int(args[0])
            if limit < 10:
                limit = 10
            elif limit > MAX_HISTORY_LIMIT:
                limit = MAX_HISTORY_LIMIT
        
        user = None
        user_id = None
        user_name = ""
        analysis_type = "general"
        
        if message.is_reply:
            reply = await message.get_reply_message()
            if reply and reply.sender:
                user = reply.sender.username
                user_id = reply.sender.id
                user_name = reply.sender.first_name
                if hasattr(reply.sender, "last_name") and reply.sender.last_name:
                    user_name += f" {reply.sender.last_name}"
                analysis_type = "user"
                
                await utils.answer(message, self.strings["collecting_history"].format(user_name))
            else:
                await utils.answer(message, self.strings["collecting_chat"])
        else:
            await utils.answer(message, self.strings["collecting_chat"])
        
        # Собираем сообщения
        chat_messages = await self._collect_messages(message.chat_id, limit, user_id)
        
        if not chat_messages:
            await utils.answer(message, self.strings["no_messages"])
            return
        
        # Генерируем промпт для AI
        prompt = await self._generate_prompt(chat_messages, analysis_type, user_name)
        
        # Отображаем статус обработки
        emoji = await self._get_random_emoji()
        await utils.answer(message, self.strings["processing"].format(f"{emoji} Анализирую сообщения..."))
        
        # Обрабатываем запрос к AI
        result = await self._process_ai_query(prompt)
        
        # Формируем заголовок в зависимости от типа анализа
        if analysis_type == "user":
            title = self.strings["user_analysis_title"].format(user_name)
        else:
            title = self.strings["chat_analysis_title"]
        
        # Отправляем результат анализа
        await utils.answer(message, f"{title}\n\n{result}")
    
    @loader.command(ru_doc="– анализ настроения чата")
    async def camood(self, message: Message):
        """– analyze chat mood"""
        if not self.get_active_api_key():
            await utils.answer(message, self.strings["no_api_key"])
            return
        
        # Проверяем ограничение запросов
        wait_time = await self._check_rate_limit(message.chat_id)
        if wait_time:
            await utils.answer(message, self.strings["rate_limited"].format(wait_time))
            return
        
        # Определяем лимит
        limit = self.config["history_limit"]
        args = utils.get_args(message)
        if args and args[0].isdigit():
            limit = int(args[0])
            if limit < 10:
                limit = 10
            elif limit > MAX_HISTORY_LIMIT:
                limit = MAX_HISTORY_LIMIT
        
        # Собираем сообщения
        await utils.answer(message, self.strings["collecting_chat"])
        chat_messages = await self._collect_messages(message.chat_id, limit)
        
        if not chat_messages:
            await utils.answer(message, self.strings["no_messages"])
            return
        
        # Генерируем промпт для AI с фокусом на анализ настроения
        prompt = await self._generate_prompt(chat_messages, "mood")
        
        # Отображаем статус обработки
        emoji = await self._get_random_emoji()
        await utils.answer(message, self.strings["processing"].format(f"{emoji} Анализирую настроение чата..."))
        
        # Обрабатываем запрос к AI
        result = await self._process_ai_query(prompt)
        
        # Отправляем результат анализа
        await utils.answer(message, f"{self.strings['mood_analysis_title']}\n\n{result}")
    
    @loader.command(ru_doc="– анализ основных тем обсуждения в чате")
    async def catopic(self, message: Message):
        """– analyze chat topics"""
        if not self.get_active_api_key():
            await utils.answer(message, self.strings["no_api_key"])
            return
        
        # Проверяем ограничение запросов
        wait_time = await self._check_rate_limit(message.chat_id)
        if wait_time:
            await utils.answer(message, self.strings["rate_limited"].format(wait_time))
            return
        
        # Определяем лимит
        limit = self.config["history_limit"]
        args = utils.get_args(message)
        if args and args[0].isdigit():
            limit = int(args[0])
            if limit < 10:
                limit = 10
            elif limit > MAX_HISTORY_LIMIT:
                limit = MAX_HISTORY_LIMIT
        
        # Собираем сообщения
        await utils.answer(message, self.strings["collecting_chat"])
        chat_messages = await self._collect_messages(message.chat_id, limit)
        
        if not chat_messages:
            await utils.answer(message, self.strings["no_messages"])
            return
        
        # Генерируем промпт для AI с фокусом на тематический анализ
        prompt = await self._generate_prompt(chat_messages, "topic")
        
        # Отображаем статус обработки
        emoji = await self._get_random_emoji()
        await utils.answer(message, self.strings["processing"].format(f"{emoji} Анализирую темы обсуждения..."))
        
        # Обрабатываем запрос к AI
        result = await self._process_ai_query(prompt)
        
        # Отправляем результат анализа
        await utils.answer(message, f"{self.strings['topic_analysis_title']}\n\n{result}")
    
    @loader.command(ru_doc="[модель] – быстрая смена AI-модели (gemini/openai/anthropic)")
    async def caset(self, message: Message):
        """[model] – quickly change AI model (gemini/openai/anthropic)"""
        args = utils.get_args_raw(message)
        
        if not args:
            available_models = ", ".join(AI_MODELS)
            current_model = self.config["active_model"]
            await utils.answer(message, f"<b>Текущая модель:</b> {current_model}\n<b>Доступные модели:</b> {available_models}")
            return
        
        model = args.lower()
        
        if model not in AI_MODELS:
            available_models = ", ".join(AI_MODELS)
            await utils.answer(message, f"<b>❌ Некорректная модель.</b>\n<b>Доступные модели:</b> {available_models}")
            return
        
        self.config["active_model"] = model
        await utils.answer(message, self.strings["model_set"].format(model))
