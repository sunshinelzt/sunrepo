__version__ = (1, 3, 0)

# пися
# meta developer: @sunshinelzt

import os
import json
import random
import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class ChatGPTMod(loader.Module):
    """Модуль для общения с ChatGPT и анализа истории чата"""

    strings = {
        "name": "ChatGPT",
        "no_api_key": "<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Получите его на platform.openai.com</b>",
        "no_prompt": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Введите запрос или ответьте на сообщение</b>",
        "request_sent": "<emoji document_id=5325547803936572038>✨</emoji> <b>Запрос отправлен, ожидайте ответ...</b>",
        "error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка:</b> {}",
        "empty_response": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ответ пустой.</b>",
        "collecting_history": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю сообщений для {}...</b>",
        "collecting_chat": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю чата...</b>",
        "user_analysis_title": "<emoji document_id=5873121512445187130>❓</emoji> <b>Что обсуждал {} сегодня?</b>",
        "chat_analysis_title": "<emoji document_id=5873121512445187130>❓</emoji> <b>Анализ чата:</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key", "", "API ключ OpenAI", validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "model_name", "gpt-4o", "Модель ChatGPT", validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "proxy", "", "Прокси для API (если требуется)", validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "max_retries", 3, "Количество попыток запроса", validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "timeout", 60, "Таймаут запроса (сек)", validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "history_limit", 50, "Максимальное число сообщений для анализа", validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "max_tokens", 1000, "Максимальное число токенов в ответе", validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "temperature", 0.7, "Температура генерации (0-1)", validator=loader.validators.String()
            ),
        )
        self.conversations = {}  # Хранение истории диалога по chat_id

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        if self.config["proxy"]:
            os.environ["HTTP_PROXY"] = self.config["proxy"]
            os.environ["HTTPS_PROXY"] = self.config["proxy"]
            logger.info(f"Proxy set to {self.config['proxy']}")

    async def _call_chatgpt(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Отправляет запрос в OpenAI и возвращает ответ."""
        api_key = self.config["api_key"]
        if not api_key:
            raise ValueError("API ключ не указан")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.config["model_name"],
            "messages": messages,
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
        }

        timeout = aiohttp.ClientTimeout(total=self.config["timeout"])
        proxy = self.config["proxy"] or None

        for attempt in range(self.config["max_retries"]):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data,
                        proxy=proxy
                    ) as response:
                        response_text = await response.text()
                        try:
                            response_json = json.loads(response_text)
                        except json.JSONDecodeError:
                            logger.error(f"Ошибка декодирования JSON: {response_text}")
                            raise Exception("Некорректный ответ API")

                        if response.status == 200 and "choices" in response_json:
                            return response_json["choices"][0]["message"]["content"].strip()
                        elif response.status == 429:
                            wait_time = 2 ** attempt
                            logger.warning(f"Лимит запросов, повтор через {wait_time} сек (попытка {attempt+1})")
                            await asyncio.sleep(wait_time)
                        else:
                            error_msg = response_json.get("error", {}).get("message", f"HTTP {response.status}")
                            logger.error(f"Ошибка API: {error_msg}")
                            raise Exception(f"Ошибка API: {error_msg}")

            except asyncio.TimeoutError:
                logger.error(f"Таймаут запроса (попытка {attempt+1})")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.exception(f"Ошибка запроса: {e}")
                await asyncio.sleep(2 ** attempt)

        raise Exception("Превышено число попыток запроса к API")

    async def _process_media(self, message) -> Optional[str]:
        """Обрабатывает медиа в сообщении и возвращает краткое описание."""
        if not message:
            return None

        try:
            if getattr(message, "photo", None):
                return "[Изображение]"
            elif getattr(message, "video", None) or getattr(message, "video_note", None):
                return "[Видео]"
            elif getattr(message, "animation", None):
                return "[GIF]"
            elif getattr(message, "voice", None):
                return "[Голосовое сообщение]"
            elif getattr(message, "audio", None):
                return "[Аудио]"
            elif getattr(message, "sticker", None):
                return "[Стикер]"
            elif getattr(message, "document", None):
                return "[Документ]"
        except Exception as e:
            logger.error(f"Ошибка обработки медиа: {e}")
            return None

        return None

    async def _update_conversation(self, chat_id: str, role: str, content: str):
        """Обновляет историю диалога, сохраняя последние сообщения."""
        if chat_id not in self.conversations:
            # Добавляем системное сообщение по умолчанию
            self.conversations[chat_id] = [{"role": "system", "content": "Ты – полезный и грамотный помощник."}]
        self.conversations[chat_id].append({"role": role, "content": content})
        max_items = self.config["history_limit"]
        # Сохраняем системное сообщение и последние max_items пар сообщений (user+assistant)
        if len(self.conversations[chat_id]) > max_items * 2 + 1:
            system_msg = self.conversations[chat_id][0]
            self.conversations[chat_id] = [system_msg] + self.conversations[chat_id][-max_items * 2:]

    @loader.command(ru_doc="- отправить запрос к ChatGPT")
    async def gpts(self, message):
        """Отправляет запрос к ChatGPT с учетом истории диалога"""
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        prompt = utils.get_args_raw(message)
        chat_id = str(message.chat_id)

        if message.is_reply:
            reply = await message.get_reply_message()
            prompt = prompt or (reply.text or (await self._process_media(reply)) or "")

        if not prompt:
            await utils.answer(message, self.strings["no_prompt"])
            return

        await utils.answer(message, self.strings["request_sent"])
        conv = self.conversations.get(chat_id, [])
        conv.append({"role": "user", "content": prompt})

        try:
            response = await self._call_chatgpt(conv)
            if not response:
                await utils.answer(message, self.strings["empty_response"])
                return

            await self._update_conversation(chat_id, "assistant", response)
            await utils.answer(message, f"<b>🤖 ChatGPT:</b> {response}")

        except Exception as e:
            logger.exception(f"Ошибка в команде gpt: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(ru_doc="- очистить историю диалога в текущем чате")
    async def gptclear(self, message):
        """Очищает историю диалога для текущего чата"""
        chat_id = str(message.chat_id)
        if chat_id in self.conversations:
            # Если есть системное сообщение – оставляем его
            system_msg = self.conversations[chat_id][0] if self.conversations[chat_id] and self.conversations[chat_id][0]["role"] == "system" else None
            self.conversations[chat_id] = [system_msg] if system_msg else []
            await utils.answer(message, "<b>История диалога очищена!</b>")
        else:
            await utils.answer(message, "<b>История диалога уже пуста.</b>")

    @loader.command(ru_doc="- анализ последних сообщений чата")
    async def gptanal(self, message):
        """
        Анализирует историю сообщений чата и выдает сводку обсуждения.
        Если команда вызвана в ответ на сообщение, анализируются только сообщения указанного пользователя.
        """
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        history_limit = self.config["history_limit"]
        chat_id = message.chat_id
        target_user = None
        target_name = ""
        prompt_header = ""

        if message.is_reply:
            reply = await message.get_reply_message()
            if reply.sender:
                target_user = reply.sender.username
                target_name = reply.sender.first_name or "Пользователь"
                prompt_header = self.strings["user_analysis_title"].format(target_name)
                await utils.answer(message, self.strings["collecting_history"].format(target_name))
            else:
                await utils.answer(message, self.strings["collecting_chat"])
        else:
            await utils.answer(message, self.strings["collecting_chat"])

        collected_msgs = []
        try:
            async for msg in self.client.iter_messages(chat_id, limit=history_limit):
                # Пропускаем системные, сообщения от ботов и служебные сообщения
                if not msg or not msg.sender or getattr(msg.sender, "bot", False) or msg.action:
                    continue

                # Если задан фильтр по пользователю
                if target_user:
                    sender_username = getattr(msg.sender, "username", None)
                    if sender_username != target_user:
                        continue

                text = msg.text or (await self._process_media(msg))
                if not text:
                    continue

                # Форматируем время и имя отправителя
                time_str = msg.date.strftime("%H:%M")
                sender_name = msg.sender.first_name if hasattr(msg.sender, "first_name") else "Unknown"
                collected_msgs.append(f"[{time_str}] {sender_name}: {text}")

            if not collected_msgs:
                await utils.answer(message, self.strings["error"].format("Не найдено подходящих сообщений для анализа"))
                return

            collected_msgs.reverse()  # Сообщения в хронологическом порядке
            history_text = "\n".join(collected_msgs)

            # Формируем задание для анализа
            if not prompt_header:
                prompt_header = self.strings["chat_analysis_title"]
            analysis_prompt = (
                f"{prompt_header}\n\n"
                "Ниже представлена история сообщений из чата:\n"
                f"{history_text}\n\n"
                "Проанализируй обсуждение: выдели основные темы, активных участников, общее настроение. "
                "В конце добавь шутку, подписанную как 'Шутка от ИИ'."
            )

            # Отправляем запрос к API без сохранения в историю диалога
            messages = [
                {"role": "system", "content": "Ты – аналитик чатов. Твоя задача – анализировать и обобщать информацию."},
                {"role": "user", "content": analysis_prompt}
            ]

            analysis = await self._call_chatgpt(messages)
            if not analysis:
                await utils.answer(message, self.strings["empty_response"])
                return

            # Выбираем случайный эмодзи для украшения ответа
            emoji = random.choice(["<emoji document_id=6046253808810464426>💃</emoji>"])
            result = f"{emoji} {analysis}"
            await utils.answer(message, result)

        except Exception as e:
            logger.exception(f"Ошибка в gptanal: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))
