__version__ = (1, 4, 8, 8)

# meta developer: @sunshinelzt

# ███████╗██╗   ██╗███╗   ██╗███████╗██╗  ██╗██╗███╗   ██╗███████╗
# ██╔════╝██║   ██║████╗  ██║██╔════╝██║  ██║██║████╗  ██║██╔════╝
# ███████╗██║   ██║██╔██╗ ██║███████╗███████║██║██╔██╗ ██║█████╗  
# ╚════██║██║   ██║██║╚██╗██║╚════██║██╔══██║██║██║╚██╗██║██╔══╝  
# ███████║╚██████╔╝██║ ╚████║███████║██║  ██║██║██║ ╚████║███████╗
# ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝


import google.generativeai as genai
import os
import time
import io
import json
import asyncio
import random
import hashlib
from typing import Tuple, Optional, Dict, Any, List, Union, Callable
import logging
from contextlib import suppress
from functools import wraps, lru_cache
from PIL import Image
from .. import loader, utils
import aiohttp
from telethon import events


logger = logging.getLogger(__name__)


def retry_decorator(max_retries=3, delay_base=2):
    """Декоратор для повторных попыток выполнения функции при ошибках"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in {func.__name__} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    wait_time = delay_base ** attempt
                    await asyncio.sleep(wait_time)
        return wrapper
    return decorator


@loader.tds
class SunshineGPT(loader.Module):
    """Продвинутый модуль для работы с Google Gemini AI и генерации изображений"""

    strings = {
        "name": "SunshineGPT",
        # Общие сообщения
        "no_api_key": "<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Получите его на aistudio.google.com/apikey</b>",
        "no_prompt": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Введите запрос или ответьте на сообщение (изображение, видео, GIF, стикер, голосовое)</b>",
        "processing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>{}</b>",
        "request_sent": "<emoji document_id=5325547803936572038>✨</emoji> <b>Запрос отправлен, ожидайте ответ...</b>",
        "generating_image": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Сервер генерирует картинку, пожалуйста, подождите...</b>",
        "describe_this": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Опиши это...</b>",
        "error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка:</b> {}",
        "server_error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка сервера:</b> {}",
        "empty_response": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ответ пустой. Попробуйте переформулировать запрос.</b>",
        "no_image_prompt": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Пожалуйста, укажите описание для генерации изображения.</b>",
        "image_caption": "<blockquote><emoji document_id=5465143921912846619>💭</emoji> <b>Промт:</b> <code>{prompt}</code></blockquote>\n"
                         "<blockquote><emoji document_id=5877260593903177342>⚙️</emoji> <b>Модель:</b> <code>{model}</code></blockquote>\n"
                         "<blockquote><emoji document_id=5199457120428249992>🕘</emoji> <b>Время генерации:</b> {time} сек.</blockquote>",
        "collecting_history": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю сообщений для {}...</b>",
        "collecting_chat": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю чата...</b>",
        "user_analysis_title": "<emoji document_id=5873121512445187130>❓</emoji> <b>Что сегодня обсуждал {}?</b>",
        "chat_analysis_title": "<emoji document_id=5873121512445187130>❓</emoji> <b>Что сегодня обсуждали участники чата?</b>",
        "empty_media": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Не удалось открыть медиа:</b> {}",
        "empty_content": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка: Запрос должен содержать текст или медиа.</b>",
        "gemini_response": "<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini:</b> {} {}",
        "question": "<emoji document_id=5443038326535759644>💬</emoji> <b>Вопрос:</b> {}",
        "gemini_models": "<emoji document_id=5325547803936572038>✨</emoji> <b>Доступные модели Gemini:</b>\n\n{}\n\n<b>Текущая модель:</b> <code>{}</code>\n\n<b>Для изменения модели используйте:</b>\n<code>.config SunshineGPT model_name новая_модель</code>",
        "help_text": "<emoji document_id=5325547803936572038>✨</emoji> <b>SunshineGPT</b>\n\n<b>Основные команды:</b>\n• <code>.gpt запрос</code> - отправить запрос к Gemini\n• <code>.gimg промпт</code> - сгенерировать изображение\n• <code>.ghist</code> - анализ истории чата (можно с ответом на сообщение)\n• <code>.gmodels</code> - показать доступные модели Gemini\n• <code>.ghelp</code> - показать эту справку\n\n<b>Работа с медиа:</b>\nОтветьте на изображение/видео/стикер с командой <code>.gpt</code>\n\n<b>Автообработка сообщений:</b>\nМодуль может автоматически обрабатывать сообщения при упоминании бота",
        "auto_processing_enabled": "<emoji document_id=5325547803936572038>✨</emoji> <b>Автоматическая обработка сообщений включена</b>",
        "auto_processing_disabled": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Автоматическая обработка сообщений отключена</b>",
        "processing_media": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Обрабатываю медиа...</b>",
        "audio_transcribing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Транскрибирую аудио...</b>",
        "video_analyzing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Анализирую видео...</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            # Настройки Gemini
            loader.ConfigValue(
                "api_key", 
                "", 
                "API ключ для Gemini AI (aistudio.google.com/apikey)", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "model_name", 
                "gemini-1.5-flash", 
                "Модель для Gemini AI. Примеры: gemini-1.5-flash, gemini-1.5-pro, gemini-pro-vision, gemini-1.5-flash-preview, gemini-1.5-pro-preview, gemini-pro", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "system_instruction", 
                "", 
                "Инструкция для Gemini AI", 
                validator=loader.validators.String()
            ),
            
            # Настройки для генерации изображений
            loader.ConfigValue(
                "api_key_image", 
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", 
                "Ключ для API генерации изображений (не изменяйте)", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "default_image_model", 
                "flux", 
                "Модель для генерации изображений. Примеры: flux, flux-pro, flux-dev, dall-e-3, midjourney", 
                validator=loader.validators.String()
            ),
            
            # Общие настройки
            loader.ConfigValue(
                "proxy", 
                "", 
                "Прокси в формате http://<user>:<pass>@<proxy>:<port>, или http://<proxy>:<port>", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "max_retries", 
                3, 
                "Максимальное количество попыток отправки запроса", 
                validator=loader.validators.Integer(minimum=1, maximum=5)
            ),
            loader.ConfigValue(
                "timeout", 
                60, 
                "Таймаут в секундах для запросов к API", 
                validator=loader.validators.Integer(minimum=10, maximum=300)
            ),
            loader.ConfigValue(
                "history_limit", 
                400, 
                "Количество сообщений для анализа истории", 
                validator=loader.validators.Integer(minimum=50, maximum=1000)
            ),
            loader.ConfigValue(
                "gemini_stream", 
                False, 
                "Использовать потоковую передачу ответов от Gemini (экспериментально)", 
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "temperature", 
                0.7, 
                "Температура для генерации (0.0 - точные ответы, 1.0 - творческие)", 
                validator=loader.validators.Float(minimum=0.0, maximum=1.0)
            ),
            # Новые настройки для автоматической обработки
            loader.ConfigValue(
                "auto_processing", 
                True, 
                "Автоматически обрабатывать сообщения при упоминании бота", 
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "default_prompt", 
                "Опиши это", 
                "Стандартный запрос для обработки медиа без текста", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "media_auto_process", 
                True, 
                "Автоматически обрабатывать медиа файлы", 
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "voice_transcription", 
                True, 
                "Транскрибировать голосовые сообщения", 
                validator=loader.validators.Boolean()
            ),
        )
        
        # Список эмодзи для разнообразия ответов
        self.emojis = [
            "<emoji document_id=5440588507254896965>🤨</emoji>",
            "<emoji document_id=5443135817998416433>😕</emoji>",
            "<emoji document_id=5442828624757536533>😂</emoji>",
            "<emoji document_id=5443072677684197457>😘</emoji>",
            "<emoji document_id=5440854425860061667>👹</emoji>",
            "<emoji document_id=5443073472253148107>🤓</emoji>",
            "<emoji document_id=5440693467665677594>🚬</emoji>",
            "<emoji document_id=5440883077586893345>☕️</emoji>",
            "<emoji document_id=5442843472459481786>🥳</emoji>",
            "<emoji document_id=5442927761192665683>🤲</emoji>",
            "<emoji document_id=5440814207786303456>😎</emoji>",
            "<emoji document_id=5442924243614447997>😡</emoji>",
            "<emoji document_id=5440804385196096498>👋</emoji>",
            "<emoji document_id=5442795081062956585>✋</emoji>",
            "<emoji document_id=5442874134231008257>👍</emoji>",
            "<emoji document_id=5442639916779454280>🖐</emoji>",
            "<emoji document_id=5442634539480400651>😶</emoji>",
            "<emoji document_id=5443010220269782390>😌</emoji>",
            "<emoji document_id=5440581390494090067>😲</emoji>",
            "<emoji document_id=5442674890698145284>😧</emoji>",
            "<emoji document_id=5443037587801389289>📲</emoji>",
            "<emoji document_id=5442864698187856287>👜</emoji>",
            "<emoji document_id=5442936205098369573>😐</emoji>",
            "<emoji document_id=5443129680490152331>👋</emoji>",
            "<emoji document_id=5442868116981824547>🔔</emoji>",
            "<emoji document_id=5440388529282629473>🫥</emoji>",
            "<emoji document_id=5442876913074847850>🧮</emoji>",
            "<emoji document_id=5442644336300802689>🚬</emoji>",
            "<emoji document_id=5442714550426157926>🦴</emoji>",
            "<emoji document_id=5442869822083841917>😴</emoji>",
            "<emoji document_id=5442895299829843652>😳</emoji>",
            "<emoji document_id=5443106182724076636>🍫</emoji>",
            "<emoji document_id=5443135796523579899>💃</emoji>",
            "<emoji document_id=5442741651669795615>😱</emoji>",
            "<emoji document_id=5442613657349405621>🖖</emoji>",
            "<emoji document_id=5442672781869204635>🎉</emoji>",
            "<emoji document_id=5440474033491560675>☺️</emoji>",
            "<emoji document_id=5442979910685573674>👍</emoji>",
            "<emoji document_id=5442873906597741574>🗣</emoji>",
            "<emoji document_id=5440412353466222950>😶‍🌫️</emoji>",
            "<emoji document_id=5442938782078746258>😃</emoji>",
            "<emoji document_id=5443087564040847705>😠</emoji>",
            "<emoji document_id=5440702594471182364>🐽</emoji>",
            "<emoji document_id=5442641505917352670>💢</emoji>",
            "<emoji document_id=5444907646626838669>🥰</emoji>",
            "<emoji document_id=5445374977723349942>😒</emoji>",
            "<emoji document_id=5442881062013254513>😊</emoji>",
            "<emoji document_id=5445375935501055831>😐</emoji>",
            "<emoji document_id=5445360628237614380>🌅</emoji>",
            "<emoji document_id=5445079806095933151>😦</emoji>",
            "<emoji document_id=5444946571915444568>🤷‍♂️</emoji>",
            "<emoji document_id=5445017237012363750>🥳</emoji>",
            "<emoji document_id=5442859243579393479>🤦‍♀️</emoji>",
            "<emoji document_id=5444950785278362209>😎</emoji>",
            "<emoji document_id=5445398230676291110>🤣</emoji>",
            "<emoji document_id=5445333290770775391>👀</emoji>",
            "<emoji document_id=5445255122365988661>😕</emoji>",
            "<emoji document_id=5445159739732279716>🫥</emoji>",
            "<emoji document_id=5447594277519505787>😌</emoji>",
            "<emoji document_id=5444909231469771073>👍</emoji>",
            "<emoji document_id=5445144823310859690>☠️</emoji>",
            "<emoji document_id=5445178796502171599>💀</emoji>",
            "<emoji document_id=5445021368770905143>🎧</emoji>",
            "<emoji document_id=5444963197733846783>😭</emoji>",
            "<emoji document_id=5444953903424616983>🙂</emoji>",
            "<emoji document_id=5445281673853813075>🤔</emoji>",
            "<emoji document_id=5444879089389289261>👌</emoji>",
            "<emoji document_id=5444884879005204566>😨</emoji>",
            "<emoji document_id=5445069897606381495>😋</emoji>",
            "<emoji document_id=5445141215538329626>😅</emoji>",
            "<emoji document_id=5444875919703424395>▶️</emoji>",
            "<emoji document_id=5445324125310567405>⏰</emoji>",
            "<emoji document_id=5447657447898496804>😕</emoji>",
            "<emoji document_id=5447437455378627555>🤬</emoji>",
            "<emoji document_id=5449419466821618942>😱</emoji>",
            "<emoji document_id=5447455666039963228>💦</emoji>",
            "<emoji document_id=5449777078683582032>🥕</emoji>",
            "<emoji document_id=5447417329161879977>🤦‍♀️</emoji>",
            "<emoji document_id=5447214563755836578>🙈</emoji>",
            "<emoji document_id=5447152020442070774>🔫</emoji>",
            "<emoji document_id=5447123909881117332>🖕</emoji>",
            "<emoji document_id=5449728399524249126>🐻</emoji>",
            "<emoji document_id=5447440066718743386>🍺</emoji>",
            "<emoji document_id=5447153218737949833>🤦</emoji>",
            "<emoji document_id=5447223407093497907>☺️</emoji>"
        ]
        
        # Временный кэш для обработанных запросов
        self._request_cache = {}
        self._gemini_model = None
        self._me = None
        self._is_bot_mentioned = False

    async def client_ready(self, client, db):
        """Инициализация клиента"""
        self.client = client
        self.db = db
        
        if self.config["proxy"]:
            os.environ["HTTP_PROXY"] = self.config["proxy"]
            os.environ["HTTPS_PROXY"] = self.config["proxy"]
            logger.info(f"Proxy set to {self.config['proxy']}")
            
        # Получаем информацию о нашем пользователе/боте
        self._me = await client.get_me()
        
        # Регистрируем обработчик для всех входящих сообщений
        client.add_event_handler(
            self._message_handler, 
            events.NewMessage(incoming=True)
        )
        
        logger.info("SunshineGPT автоматическая обработка сообщений инициализирована")

    async def _message_handler(self, event):
        """Обработчик всех входящих сообщений"""
        
        # Пропускаем, если автоматическая обработка отключена
        if not self.config["auto_processing"]:
            return
            
        # Проверяем, что API ключ указан
        if not self.config["api_key"]:
            return
            
        # Получаем объект сообщения
        message = event.message
        
        # Проверяем упоминание бота
        if self._me:
            # Проверка текстового упоминания
            if message.text:
                # Проверяем упоминание по имени пользователя или имени бота
                bot_username = self._me.username if self._me.username else ""
                bot_firstname = self._me.first_name if self._me.first_name else ""
                
                mentioned = False
                
                # Проверка прямого упоминания через @username
                if bot_username and f"@{bot_username}" in message.text.lower():
                    mentioned = True
                    
                # Проверка упоминания по имени
                if bot_firstname and bot_firstname.lower() in message.text.lower():
                    mentioned = True
                    
                if not mentioned:
                    # Проверяем, есть ли медиа контент, который мы должны обработать автоматически
                    if not self.config["media_auto_process"]:
                        return
                        
                    # Проверка наличия медиа в сообщении
                    if not (message.media or getattr(message, "voice", None) or 
                            getattr(message, "video", None) or getattr(message, "audio", None) or
                            getattr(message, "photo", None) or getattr(message, "document", None) or
                            getattr(message, "sticker", None) or getattr(message, "video_note", None)):
                        return
            else:
                # Если нет текста, но есть медиа и настройка включена
                if not self.config["media_auto_process"]:
                    return
                    
                # Проверяем наличие медиа для автоматической обработки
                if not (message.media or getattr(message, "voice", None) or 
                        getattr(message, "video", None) or getattr(message, "audio", None) or
                        getattr(message, "photo", None) or getattr(message, "document", None) or
                        getattr(message, "sticker", None) or getattr(message, "video_note", None)):
                    return
                        
        # Обрабатываем сообщение
        await self._process_message(message)

    async def _process_message(self, message):
        """Обрабатывает сообщение и отправляет ответ от AI"""
        try:
            # Определяем тип медиа
            mime_type = self._get_mime_type(message)
            media_path = None
            prompt = message.text if message.text else self.config["default_prompt"]
            
            # Специальное сообщение в зависимости от типа медиа
            if mime_type:
                if mime_type.startswith("audio"):
                    status_msg = await message.reply(self.strings["audio_transcribing"])
                elif mime_type.startswith("video"):
                    status_msg = await message.reply(self.strings["video_analyzing"])
                else:
                    status_msg = await message.reply(self.strings["processing_media"])
                    
                # Скачиваем медиа
                media_path = await message.download_media()
                
                # Если это изображение, попробуем открыть его
                if mime_type.startswith("image"):
                    try:
                        img = Image.open(media_path)
                    except Exception as e:
                        await status_msg.edit(self.strings["empty_media"].format(e))
                        if media_path and os.path.exists(media_path):
                            with suppress(Exception):
                                os.remove(media_path)
                        return
            else:
                # Если нет медиа, просто отправляем запрос
                status_msg = await message.reply(self.strings["request_sent"])
                
            # Формируем запрос к Gemini
            content_parts = []
            if prompt:
                content_parts.append(genai.protos.Part(text=prompt))
                
            if media_path:
                with open(media_path, "rb") as f:
                    content_parts.append(genai.protos.Part(
                        inline_data=genai.protos.Blob(
                            mime_type=mime_type,
                            data=f.read()
                        )
                    ))
                    
            if not content_parts:
                await status_msg.edit(self.strings["empty_content"])
                return
                
            # Кэширование запроса
            cache_key = self._get_request_cache_key(prompt, media_path)
            if cache_key in self._request_cache:
                reply_text = self._request_cache[cache_key]
                logger.info("Using cached response")
            else:
                # Отправляем запрос с учетом настройки потоковой передачи
                reply_text = await self._process_gemini_query(content_parts, stream=self.config["gemini_stream"])
                
                # Кэшируем ответ (ограничиваем размер кэша)
                if len(self._request_cache) > 50:
                    # Удаляем старый элемент
                    try:
                        oldest_key = next(iter(self._request_cache))
                        del self._request_cache[oldest_key]
                    except (StopIteration, KeyError):
                        pass
                        
                self._request_cache[cache_key] = reply_text
                
            random_emoji = await self._get_random_emoji()
            
            # Формируем ответ, включая исходный запрос при необходимости
            if prompt != self.config["default_prompt"]:
                response = f"{self.strings['question'].format(prompt)}\n\n{self.strings['gemini_response'].format(reply_text, random_emoji)}"
            else:
                response = f"\n{self.strings['gemini_response'].format(reply_text, random_emoji)}"
                
            # Отправляем ответ
            await status_msg.edit(response)
            
        except Exception as e:
            logger.exception(f"Error in _process_message: {e}")
            try:
                await message.reply(self.strings["error"].format(e))
            except Exception:
                pass
        finally:
            # Очистка временных файлов
            if media_path and os.path.exists(media_path):
                with suppress(Exception):
                    os.remove(media_path)

    def _get_mime_type(self, message) -> Optional[str]:
        """Определяет MIME-тип медиа в сообщении"""
        if not message:
            return None

        try:
            if getattr(message, "video", None) or getattr(message, "video_note", None):
                return "video/mp4"
            elif getattr(message, "animation", None) or (getattr(message, "sticker", None) and getattr(message.sticker, "is_video", False)):
                return "video/mp4"
            elif getattr(message, "voice", None) or getattr(message, "audio", None):
                return "audio/wav"
            elif getattr(message, "photo", None):
                return "image/png"
            elif getattr(message, "sticker", None):
                return "image/webp"
            elif getattr(message, "document", None):
                # Попытка определить тип по имени файла
                file_name = getattr(message.document, "file_name", "").lower()
                if file_name.endswith((".jpg", ".jpeg")):
                    return "image/jpeg"
                elif file_name.endswith(".png"):
                    return "image/png"
                elif file_name.endswith(".gif"):
                    return "image/gif"
                elif file_name.endswith((".mp4", ".avi", ".mov")):
                    return "video/mp4"
                elif file_name.endswith((".mp3", ".wav", ".ogg")):
                    return "audio/mpeg"
                # Дополнительные типы документов
                elif file_name.endswith((".pdf")):
                    return "application/pdf"
                elif file_name.endswith((".doc", ".docx")):
                    return "application/msword"
                elif file_name.endswith((".xls", ".xlsx")):
                    return "application/vnd.ms-excel"
                elif file_name.endswith((".ppt", ".pptx")):
                    return "application/vnd.ms-powerpoint"
                # Если не смогли определить по расширению, пробуем по MIME типу
                mime_type = getattr(message.document, "mime_type", None)
                if mime_type:
                    return mime_type
                
        except AttributeError as e:
            logger.error(f"Error getting mime type: {e}")
            return None

        return None

    async def _get_random_emoji(self) -> str:
        """Возвращает случайный эмодзи из списка"""
        return random.choice(self.emojis)

    async def _setup_gemini(self) -> genai.GenerativeModel:
        """Настраивает Gemini API с заданным ключом и возвращает модель"""
        if not self.config["api_key"]:
            raise ValueError("API ключ не указан")
        
        # Настраиваем API с ключом
        genai.configure(api_key=self.config["api_key"])
        
        # Создаем модель с инструкцией и температурой
        return genai.GenerativeModel(
            model_name=self.config["model_name"],
            system_instruction=self.config["system_instruction"] or None,
            generation_config={"temperature": self.config["temperature"]}
        )

    def _get_request_cache_key(self, prompt: str, media_path: Optional[str] = None) -> str:
        """Создает уникальный ключ для кэширования запроса"""
        key_components = [prompt]
        
        if media_path and os.path.exists(media_path):
            # Добавляем хеш содержимого файла для медиа
            try:
                with open(media_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                key_components.append(file_hash)
            except Exception as e:
                logger.error(f"Error hashing media file: {e}")
                # Если не удалось получить хеш, добавляем путь
                key_components.append(media_path)
        
        return hashlib.md5(":".join(key_components).encode()).hexdigest()

    @retry_decorator()
    async def _process_gemini_query(self, content_parts, stream=False):
        """Обрабатывает запрос к Gemini API"""
        model = await self._setup_gemini()
        
        if stream and self.config["gemini_stream"]:
            # Потоковая генерация
            response_stream = model.generate_content(content_parts, stream=True)
            full_response = ""
            
            async for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    
            return full_response.strip() or self.strings["empty_response"]
        else:
            # Обычная генерация
            response = model.generate_content(content_parts)
            return response.text.strip() if response.text else self.strings["empty_response"]

    @retry_decorator(max_retries=3)
    async def generate_image(self, prompt: str) -> Tuple[Optional[str], Union[float, str]]:
        """Генерация изображения с API"""
        start_time = time.time()

        payload = {
            "model": self.config["default_image_model"],
            "prompt": prompt,
            "response_format": "url"
        }

        http_proxy = self.config["proxy"] if self.config["proxy"] else None
        conn = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.config["timeout"])
        
        headers = {
            "Authorization": f"Bearer {self.config['api_key_image']}", 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            async with session.post(
                "https://api.kshteam.top/v1/images/generate", 
                headers=headers, 
                json=payload, 
                proxy=http_proxy
            ) as response:
                generation_time = round(time.time() - start_time, 2)
                
                if response.status == 200:
                    data = await response.json()
                    image_url = data.get("data", [{}])[0].get("url", None)

                    if image_url:
                        logger.info(f"Image generated successfully in {generation_time}s")
                        return image_url, generation_time
                    else:
                        error_msg = "Ошибка получения URL изображения"
                        logger.error(error_msg)
                        return None, error_msg
                else:
                    error_msg = f"Ошибка сервера: {response.status}"
                    logger.error(f"Server error: {response.status} - {await response.text()}")
                    return None, error_msg

    @loader.command(alias="gpt")
    async def gpt(self, message):
        """— отправить запрос к Gemini AI"""
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        prompt = utils.get_args_raw(message)
        media_path = None
        img = None
        show_question = True

        try:
            if message.is_reply:
                reply = await message.get_reply_message()
                mime_type = self._get_mime_type(reply)

                if mime_type:
                    media_path = await reply.download_media()
                    if not prompt:
                        prompt = "Опиши это"
                        await utils.answer(message, self.strings["describe_this"])
                        show_question = False
                else:
                    prompt = prompt or reply.text

            if media_path and mime_type and mime_type.startswith("image"):
                try:
                    img = Image.open(media_path)
                except Exception as e:
                    await utils.answer(message, self.strings["empty_media"].format(e))
                    if media_path and os.path.exists(media_path):
                        with suppress(Exception):
                            os.remove(media_path)
                    return

            if not prompt and not img and not media_path:
                await utils.answer(message, self.strings["no_prompt"])
                return

            await utils.answer(message, self.strings["request_sent"])

            # Проверяем кэш для одинаковых запросов
            cache_key = self._get_request_cache_key(prompt, media_path)
            if cache_key in self._request_cache:
                reply_text = self._request_cache[cache_key]
                logger.info("Using cached response")
            else:
                # Формируем части запроса для Gemini
                content_parts = []
                if prompt:
                    content_parts.append(genai.protos.Part(text=prompt))

                if media_path:
                    with open(media_path, "rb") as f:
                        content_parts.append(genai.protos.Part(
                            inline_data=genai.protos.Blob(
                                mime_type=mime_type,
                                data=f.read()
                            )
                        ))

                if not content_parts:
                    await utils.answer(message, self.strings["empty_content"])
                    return

                # Отправляем запрос с учетом настройки потоковой передачи
                reply_text = await self._process_gemini_query(content_parts, stream=self.config["gemini_stream"])
                
                # Кэшируем ответ (ограничиваем размер кэша)
                if len(self._request_cache) > 50:  # Ограничиваем кэш до 50 запросов
                    # Удаляем старый элемент
                    try:
                        oldest_key = next(iter(self._request_cache))
                        del self._request_cache[oldest_key]
                    except (StopIteration, KeyError):
                        pass
                        
                self._request_cache[cache_key] = reply_text

            random_emoji = await self._get_random_emoji()

            if show_question and prompt != "Опиши это":
                response = f"{self.strings['question'].format(prompt)}\n\n{self.strings['gemini_response'].format(reply_text, random_emoji)}"
            else:
                response = f"\n{self.strings['gemini_response'].format(reply_text, random_emoji)}"
            
            await utils.answer(message, response)
            
        except Exception as e:
            logger.exception(f"Error in gemini command: {e}")
            await utils.answer(message, self.strings["error"].format(e))
        finally:
            if media_path and os.path.exists(media_path):
                with suppress(Exception):
                    os.remove(media_path)

    @loader.command()
    async def gimg(self, message):
        """— генерация изображения"""
        prompt = utils.get_args_raw(message)
        if not prompt:
            await utils.answer(message, self.strings["no_image_prompt"])
            return

        await utils.answer(message, self.strings["generating_image"])

        image_url, generation_time = await self.generate_image(prompt)

        if image_url:
            timeout = aiohttp.ClientTimeout(total=30)
            conn = aiohttp.TCPConnector(ssl=False)
            
            try:
                async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
                    async with session.get(image_url) as img_response:
                        if img_response.status != 200:
                            await utils.answer(message, self.strings["error"].format(f"Не удалось загрузить изображение (код: {img_response.status})"))
                            return
                            
                        img_content = io.BytesIO(await img_response.read())
                        img_content.name = f"generated_image_{int(time.time())}.png"

                        caption = self.strings["image_caption"].format(
                            prompt=prompt,
                            model=self.config['default_image_model'],
                            time=generation_time
                        )

                        await utils.answer_file(message, img_content, caption=caption)

            except Exception as e:
                logger.exception(f"Error downloading generated image: {e}")
                await utils.answer(message, self.strings["error"].format(f"Ошибка при загрузке изображения: {e}"))
        else:
            await utils.answer(message, self.strings["error"].format(generation_time))

    @loader.command()
    async def ghist(self, message):
        """- анализ сообщений чата или пользователя (можно с ответом на сообщение)"""
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        user = None
        user_name = ""
        history_limit = self.config["history_limit"]
        
        if message.is_reply:
            reply = await message.get_reply_message()
            user = reply.sender_id if reply.sender else None
            user_name = reply.sender.first_name if reply.sender else "Пользователь"
            if user:
                await utils.answer(message, self.strings["collecting_history"].format(user_name))
            else:
                await utils.answer(message, self.strings["collecting_chat"])
        else:
            await utils.answer(message, self.strings["collecting_chat"])

        try:
            chat_id = message.chat_id
            all_messages = []
            
            total_collected = 0
            async for msg in self.client.iter_messages(chat_id, limit=history_limit * 2):  # Увеличиваем лимит для лучшего сбора
                if msg and msg.sender and not getattr(msg.sender, "bot", False) and not msg.action:
                    sender_id = msg.sender_id if hasattr(msg, "sender_id") else 0
                    sender_name = msg.sender.first_name if hasattr(msg.sender, "first_name") else "Unknown"
                    
                    if user and sender_id != user:
                        continue
                        
                    msg_text = msg.text if msg.text else ""
                    if not msg_text and msg.media:
                        msg_text = "[медиа]"
                    
                    # Пропускаем пустые сообщения
                    if not msg_text:
                        continue
                    
                    message_data = {
                        "sender": sender_name,
                        "time": msg.date.strftime("%H:%M:%S"),
                        "text": msg_text
                    }
                    
                    all_messages.append(message_data)
                    total_collected += 1
                    
                if total_collected >= history_limit:
                    break
            
            if not all_messages:
                await utils.answer(message, self.strings["error"].format("Не найдено подходящих сообщений"))
                return
                
            # Сортируем сообщения по времени
            all_messages.sort(key=lambda x: x["time"])
            
            # Готовим контекст для анализа
            context = "Ниже представлена история сообщений из чата Telegram. "
            if user:
                context += f"Проанализируй все сообщения пользователя {user_name} и составь краткую сводку о чем он писал сегодня, "
                context += "его интересах, вопросах, общем настроении. Выдели основные темы обсуждения. "
                context += "В конце напиши шутку про то что ты прочитал и запиши как 'Шутка от ИИ:'"
                title = self.strings["user_analysis_title"].format(user_name)
            else:
                context += "Проанализируй все сообщения и составь краткую сводку о том, что обсуждалось в чате сегодня. "
                context += "Выдели основные темы обсуждения, активных участников, общее настроение беседы. "
                context += "В конце напиши шутку про то что ты прочитал и запиши как 'Шутка от ИИ:'"
                title = self.strings["chat_analysis_title"]
                
            # Формируем текст истории для анализа
            history_text = "\n".join([f"[{msg['time']}] {msg['sender']}: {msg['text']}" for msg in all_messages])
            
            prompt = f"{context}\n\nИстория сообщений:\n{history_text}"
            
            processing_msg = await utils.answer(
                message, 
                self.strings["processing"].format("Анализирую сообщения...")
            )
            
            # Отправляем запрос к Gemini
            content_parts = [genai.protos.Part(text=prompt)]
            analysis = await self._process_gemini_query(content_parts)
            
            random_emoji = await self._get_random_emoji()
            result = f"{title}\n\n{analysis} {random_emoji}"
            
            await utils.answer(processing_msg, result)
            
        except Exception as e:
            logger.exception(f"Error in ghist: {e}")
            await utils.answer(message, self.strings["error"].format(e))

    @loader.command()
    async def gmodels(self, message):
        """— список доступных моделей Gemini"""
        models = [
            "gemini-1.5-flash", 
            "gemini-1.5-pro", 
            "gemini-1.5-flash-preview", 
            "gemini-1.5-pro-preview",
            "gemini-pro",
            "gemini-pro-vision"
        ]
        
        models_text = "\n".join([f"• <code>{model}</code>" for model in models])
        await utils.answer(message, self.strings["gemini_models"].format(models_text, self.config["model_name"]))

    @loader.command()
    async def ghelp(self, message):
        """— показать справку по модулю"""
        await utils.answer(message, self.strings["help_text"])

    @loader.command()
    async def gauto(self, message):
        """— включить/выключить автоматическую обработку сообщений"""
        self.config["auto_processing"] = not self.config["auto_processing"]
        
        if self.config["auto_processing"]:
            await utils.answer(message, self.strings["auto_processing_enabled"])
        else:
            await utils.answer(message, self.strings["auto_processing_disabled"])
