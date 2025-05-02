# meta developer: @sunshinelzt

import asyncio
import logging
import contextlib
import io
import os
import re
import requests
import base64
import mimetypes
from typing import Union, List, Optional, Dict, Any

from telethon import types
from telethon.tl.types import DocumentAttributeFilename, Message

logger = logging.getLogger(__name__)


@loader.tds
class GrokAI(loader.Module):
    """Мощный модуль для взаимодействия с Grok AI с поддержкой мультимедиа"""
    strings = {
        "name": "GrokAI",
        "_cls_doc": "Мощный модуль для взаимодействия с Grok AI с поддержкой мультимедиа",
        "no_args": "<emoji document_id=5854929766146118183>❌</emoji> <b>Нужно </b><code>{}{} {}</code>",
        "no_token": "<emoji document_id=5854929766146118183>❌</emoji> <b>Нету токена! Вставь его в </b><code>{}cfg grokai</code>",
        "asking_grok": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Спрашиваю Grok...</b>",
        "answer": """<emoji document_id=5355148941878900494>🌐</emoji> <b>Ответ от Grok AI:</b> 

{answer}

<emoji document_id=5785419053354979106>❔</emoji> <b>Запрос:</b> {question}""",
        "error": "<emoji document_id=5854929766146118183>❌</emoji> <b>Ошибка при запросе к Grok AI:</b> <code>{error}</code>",
        "processing_media": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Обрабатываю медиафайл...</b>",
        "media_processed": "<emoji document_id=5314250708508220914>✅</emoji> <b>Медиафайл обработан успешно!</b>",
        "no_media": "<emoji document_id=5854929766146118183>❌</emoji> <b>Не удалось обработать медиафайл</b>",
        "media_too_large": "<emoji document_id=5854929766146118183>❌</emoji> <b>Медиафайл слишком большой (>25MB)</b>",
        "generating_image": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Генерирую изображение...</b>",
        "transcribing_audio": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Расшифровываю аудио...</b>",
        "unknown_type": "<emoji document_id=5854929766146118183>❌</emoji> <b>Неизвестный тип файла</b>",
        "uploading_file": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Загружаю файл на сервер...</b>",
        "file_ready": "<emoji document_id=5314250708508220914>✅</emoji> <b>Файл загружен и готов к анализу!</b>",
        "available_models": """<emoji document_id=5314250708508220914>✅</emoji> <b>Доступные модели Grok AI:</b>

• <code>grok-1</code> - Основная модель Grok
• <code>grok-2</code> - Улучшенная версия Grok
• <code>grok-vision</code> - Модель с поддержкой анализа изображений

Текущая модель: <code>{current_model}</code>"""
    }

    strings_ru = {
        "name": "GrokAI",
        "_cls_doc": "Мощный модуль для взаимодействия с Grok AI с поддержкой мультимедиа",
        "no_args": "<emoji document_id=5854929766146118183>❌</emoji> <b>Нужно </b><code>{}{} {}</code>",
        "no_token": "<emoji document_id=5854929766146118183>❌</emoji> <b>Нету токена! Вставь его в </b><code>{}cfg grokai</code>",
        "asking_grok": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Спрашиваю Grok...</b>",
        "answer": """<emoji document_id=5355148941878900494>🌐</emoji> <b>Ответ от Grok AI:</b> 

{answer}

<emoji document_id=5785419053354979106>❔</emoji> <b>Запрос:</b> {question}""",
        "error": "<emoji document_id=5854929766146118183>❌</emoji> <b>Ошибка при запросе к Grok AI:</b> <code>{error}</code>",
        "processing_media": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Обрабатываю медиафайл...</b>",
        "media_processed": "<emoji document_id=5314250708508220914>✅</emoji> <b>Медиафайл обработан успешно!</b>",
        "no_media": "<emoji document_id=5854929766146118183>❌</emoji> <b>Не удалось обработать медиафайл</b>",
        "media_too_large": "<emoji document_id=5854929766146118183>❌</emoji> <b>Медиафайл слишком большой (>25MB)</b>",
        "generating_image": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Генерирую изображение...</b>",
        "transcribing_audio": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Расшифровываю аудио...</b>",
        "unknown_type": "<emoji document_id=5854929766146118183>❌</emoji> <b>Неизвестный тип файла</b>",
        "uploading_file": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Загружаю файл на сервер...</b>",
        "file_ready": "<emoji document_id=5314250708508220914>✅</emoji> <b>Файл загружен и готов к анализу!</b>",
        "available_models": """<emoji document_id=5314250708508220914>✅</emoji> <b>Доступные модели Grok AI:</b>

• <code>grok-1</code> - Основная модель Grok
• <code>grok-2</code> - Улучшенная версия Grok
• <code>grok-vision</code> - Модель с поддержкой анализа изображений

Текущая модель: <code>{current_model}</code>"""
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                lambda: "Токен Grok AI. Получить токен на сайте X.ai",
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "model",
                "grok-1",
                lambda: "Модель Grok AI. Доступны: grok-1, grok-2, grok-vision",
                validator=loader.validators.Choice(["grok-1", "grok-2", "grok-vision"])
            ),
            loader.ConfigValue(
                "max_tokens",
                4096,
                lambda: "Максимальное количество токенов в ответе",
                validator=loader.validators.Integer(minimum=1, maximum=16384)
            ),
            loader.ConfigValue(
                "temperature",
                0.7,
                lambda: "Температура генерации (0.0-1.0). Выше - более креативно, ниже - более точно",
                validator=loader.validators.Float(minimum=0.0, maximum=1.0)
            ),
            loader.ConfigValue(
                "beautify_output",
                True,
                lambda: "Украшать вывод ответов эмодзи и форматированием",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "auto_language",
                True,
                lambda: "Автоматически определять язык запроса и отвечать на том же языке",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "media_support",
                True,
                lambda: "Включить поддержку медиафайлов (фото, видео, аудио)",
                validator=loader.validators.Boolean()
            ),
        )

    async def client_ready(self, client, db):
        self.db = db
        self._client = client
        self._grok_client = None
        try:
            # Проверяем наличие необходимых модулей
            import requests
        except ImportError:
            logger.error("Не установлен модуль requests. Установите его через pip install requests")

    def _create_grok_client(self):
        """Создает клиент для работы с Grok API"""
        if not self.config['api_key']:
            raise ValueError("API ключ не установлен")
        
        # Вместо использования OpenAI клиента, будем использовать напрямую requests
        # для обращения к API Grok
        return {
            "api_key": self.config['api_key'],
            "base_url": "https://api.x.ai/v1"
        }

    def _make_grok_request(self, endpoint, data):
        """Отправляет запрос к API Grok"""
        client = self._create_grok_client()
        headers = {
            "Authorization": f"Bearer {client['api_key']}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{client['base_url']}/{endpoint}",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"Ошибка API Grok: {response.status_code} - {response.text}")
            
        return response.json()

    async def _download_media(self, message: Message) -> Optional[Dict[str, Any]]:
        """Загружает медиафайл из сообщения"""
        if not message.media:
            return None
            
        media_type = None
        file_path = None
        
        try:
            if hasattr(message.media, "photo"):
                media_type = "photo"
            elif hasattr(message.media, "document"):
                document = message.media.document
                if document.mime_type.startswith("image/"):
                    media_type = "image"
                elif document.mime_type.startswith("video/"):
                    media_type = "video"
                elif document.mime_type.startswith("audio/") or document.mime_type == "application/ogg":
                    media_type = "audio"
                elif "sticker" in document.mime_type:
                    media_type = "sticker"
                elif "gif" in document.mime_type:
                    media_type = "gif"
                else:
                    media_type = "document"
                    
                # Проверка размера файла (ограничение 25Mb)
                if document.size > 25 * 1024 * 1024:
                    return {"error": "media_too_large"}
                
            else:
                return {"error": "unknown_type"}
                
            file_path = await self._client.download_media(message.media, "groktemp_")
            
            if not file_path:
                return {"error": "no_media"}
                
            # Получаем MIME тип файла
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"
                
            # Конвертируем стикеры в изображения (если это WebP)
            if media_type == "sticker" and mime_type == "image/webp":
                media_type = "image"
                
            # Создаем словарь с данными о медиафайле    
            with open(file_path, "rb") as f:
                file_data = f.read()
                
            base64_data = base64.b64encode(file_data).decode('utf-8')
            
            return {
                "media_type": media_type,
                "mime_type": mime_type,
                "file_path": file_path,
                "base64_data": base64_data,
                "file_size": len(file_data)
            }
            
        except Exception as e:
            logger.error(f"Error processing media: {e}")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            return {"error": str(e)}

    async def _cleanup_media(self, file_path: Optional[str]) -> None:
        """Очищает временные файлы"""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing temp file: {e}")

    async def _process_media_content(self, message: Message) -> Optional[Dict[str, Any]]:
        """Обрабатывает медиаконтент из сообщения"""
        if not self.config["media_support"]:
            return None
            
        media_status = await utils.answer(message, self.strings["processing_media"])
        if isinstance(media_status, list):
            media_status = media_status[0]
            
        media_data = await self._download_media(message)
        
        if not media_data or "error" in media_data:
            error_msg = media_data.get("error", "no_media") if media_data else "no_media"
            await utils.answer(media_status, self.strings[error_msg])
            return None
            
        file_path = media_data.get("file_path")
        
        try:
            # Формируем правильный контент для запроса к Grok
            content_parts = []
            
            # Адаптируем формат для Grok API
            if media_data["media_type"] in ["photo", "image", "sticker", "gif"]:
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_data["mime_type"],
                        "data": media_data["base64_data"]
                    }
                })
            elif media_data["media_type"] in ["video", "audio", "document"]:
                content_parts.append({
                    "type": "file",
                    "source": {
                        "type": "base64",
                        "media_type": media_data["mime_type"],
                        "data": media_data["base64_data"]
                    }
                })
                
            await utils.answer(media_status, self.strings["file_ready"])
            
            return {
                "content_parts": content_parts,
                "file_path": file_path,
                "media_type": media_data["media_type"]
            }
            
        except Exception as e:
            logger.error(f"Error processing media content: {e}")
            await utils.answer(media_status, self.strings["error"].format(error=str(e)))
            await self._cleanup_media(file_path)
            return None

    @loader.command(ru_doc="Показать доступные модели Grok AI")
    async def grokmodels(self, message):
        """Показать доступные модели Grok AI"""
        await utils.answer(
            message, 
            self.strings["available_models"].format(current_model=self.config["model"])
        )

    @loader.command(ru_doc="Задать вопрос Grok AI")
    async def grok(self, message):
        """Задать вопрос к Grok"""
        # Проверяем наличие ответа
        reply_to = await message.get_reply_message()
        q = utils.get_args_raw(message)
        
        # Проверяем, что есть вопрос либо в аргументах, либо в ответе
        if not q and not reply_to:
            return await utils.answer(
                message, 
                self.strings["no_args"].format(self.get_prefix(), "grok", "[вопрос]")
            )
            
        # Проверяем наличие токена
        if not self.config['api_key']:
            return await utils.answer(message, self.strings["no_token"].format(self.get_prefix()))
            
        # Отправляем статус ожидания
        status_message = await utils.answer(message, self.strings['asking_grok'])
        if isinstance(status_message, list):
            status_message = status_message[0]
            
        try:
            media_data = None
            content = []
            
            # Если есть медиа в ответе на сообщение, обрабатываем его
            if reply_to and reply_to.media:
                media_data = await self._process_media_content(reply_to)
                if media_data:
                    content.extend(media_data["content_parts"])
            
            # Если есть медиа в текущем сообщении, обрабатываем его
            elif message.media:
                media_data = await self._process_media_content(message)
                if media_data:
                    content.extend(media_data["content_parts"])
            
            # Добавляем текстовый вопрос, если он есть
            if q:
                content.append({"type": "text", "text": q})
            elif reply_to and reply_to.text:
                content.append({"type": "text", "text": reply_to.text})
                q = reply_to.text
                
            # Если нет никакого контента, возвращаем ошибку
            if not content:
                await self._cleanup_media(media_data["file_path"] if media_data else None)
                return await utils.answer(
                    status_message, 
                    self.strings["no_args"].format(self.get_prefix(), "grok", "[вопрос]")
                )
                
            # Создаем запрос к Grok API
            data = {
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "model": self.config['model'],
                "max_tokens": self.config["max_tokens"],
                "temperature": self.config["temperature"],
            }
            
            # Отправляем запрос к Grok API
            response = self._make_grok_request("chat/completions", data)
            
            # Получаем ответ
            answer = response["choices"][0]["message"]["content"]
            
            # Форматируем красивый ответ
            if self.config["beautify_output"]:
                formatted_answer = self._beautify_output(answer)
            else:
                formatted_answer = answer
                
            # Отправляем ответ
            await utils.answer(
                status_message,
                self.strings['answer'].format(
                    question=q or "🖼 [Медиафайл]", 
                    answer=formatted_answer
                )
            )
            
        except Exception as e:
            logger.error(f"Error in Grok AI request: {e}")
            await utils.answer(
                status_message, 
                self.strings["error"].format(error=str(e))
            )
        finally:
            # Очищаем временные файлы
            if media_data:
                await self._cleanup_media(media_data.get("file_path"))

    def _beautify_output(self, text: str) -> str:
        """Украшает вывод ответов эмодзи и форматированием"""
        # Заменяем заголовки на более красивые с эмодзи
        text = re.sub(r'(?m)^# (.+)$', r'<emoji document_id=5316559247461712404>🔮</emoji> <b>\1</b>', text)
        text = re.sub(r'(?m)^## (.+)$', r'<emoji document_id=5381691752968294133>🔹</emoji> <b>\1</b>', text)
        text = re.sub(r'(?m)^### (.+)$', r'<emoji document_id=5355547930176588995>📝</emoji> <u>\1</u>', text)
        
        # Выделяем жирным важные элементы
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        
        # Выделяем курсивом элементы важные для контекста
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        
        # Преобразуем блоки кода
        text = re.sub(r'```(.+?)```', r'<code>\1</code>', text, flags=re.DOTALL)
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        
        # Добавляем emoji для улучшения восприятия
        text = re.sub(r'(?i)важно[:\s]', r'<emoji document_id=5327771435571651917>⚠️</emoji> Важно: ', text)
        text = re.sub(r'(?i)внимание[:\s]', r'<emoji document_id=5327771435571651917>⚠️</emoji> Внимание: ', text)
        text = re.sub(r'(?i)примечание[:\s]', r'<emoji document_id=5354765867371013144>📌</emoji> Примечание: ', text)
        text = re.sub(r'(?i)пример[:\s]', r'<emoji document_id=5353227595135439209>📝</emoji> Пример: ', text)
        
        # Делаем списки более красивыми
        text = re.sub(r'(?m)^- (.+)$', r'<emoji document_id=5316559247461712404>•</emoji> \1', text)
        text = re.sub(r'(?m)^(\d+)\. (.+)$', r'<emoji document_id=5313792399839332005>\1</emoji> \2', text)
        
        return text

    @loader.command(ru_doc="Сгенерировать изображение с помощью Grok AI")
    async def grokimg(self, message):
        """Сгенерировать изображение с помощью Grok AI"""
        q = utils.get_args_raw(message)
        if not q:
            return await utils.answer(
                message, 
                self.strings["no_args"].format(self.get_prefix(), "grokimg", "[описание]")
            )
            
        if not self.config['api_key']:
            return await utils.answer(message, self.strings["no_token"].format(self.get_prefix()))
            
        # Отправляем статус ожидания
        status_message = await utils.answer(message, self.strings['generating_image'])
        if isinstance(status_message, list):
            status_message = status_message[0]
            
        try:
            # Создаем запрос на генерацию изображения у Grok
            data = {
                "model": "grok-vision",
                "prompt": q,
                "n": 1,
                "size": "1024x1024"
            }
            
            # Отправляем запрос к Grok API
            response = self._make_grok_request("images/generations", data)
            
            # Получаем URL изображения
            image_url = response["data"][0]["url"]
            
            # Загружаем изображение
            image_data = requests.get(image_url).content
            
            # Отправляем изображение пользователю
            await self._client.send_file(
                message.peer_id,
                image_data,
                caption=f"<emoji document_id=5314250708508220914>✅</emoji> <b>Изображение по запросу:</b> {q}"
            )
            
            # Удаляем сообщение со статусом
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Error in Grok AI image generation: {e}")
            await utils.answer(
                status_message, 
                self.strings["error"].format(error=str(e))
            )

    @loader.command(ru_doc="Расшифровать голосовое сообщение с помощью Grok AI")
    async def grokv(self, message):
        """Расшифровать голосовое сообщение с помощью Grok AI"""
        reply_to = await message.get_reply_message()
        
        if not reply_to or not reply_to.media:
            return await utils.answer(
                message, 
                self.strings["no_args"].format(self.get_prefix(), "groktranscribe", "[ответ на голосовое]")
            )
            
        if not self.config['api_key']:
            return await utils.answer(message, self.strings["no_token"].format(self.get_prefix()))
            
        # Отправляем статус ожидания
        status_message = await utils.answer(message, self.strings['transcribing_audio'])
        if isinstance(status_message, list):
            status_message = status_message[0]
            
        try:
            # Загружаем медиа
            media_data = await self._process_media_content(reply_to)
            
            if not media_data or media_data.get("media_type") not in ["audio"]:
                await self._cleanup_media(media_data["file_path"] if media_data else None)
                return await utils.answer(status_message, self.strings["no_media"])
                
            # Создаем запрос к Grok API для транскрибации
            data = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Расшифруй это голосовое сообщение максимально точно"
                            },
                            *media_data["content_parts"]
                        ]
                    }
                ],
                "model": self.config["model"],
                "max_tokens": self.config["max_tokens"],
                "temperature": 0.3,  # Используем низкую температуру для более точной расшифровки
            }
            
            # Отправляем запрос
            response = self._make_grok_request("chat/completions", data)
            
            # Получаем ответ
            transcription = response["choices"][0]["message"]["content"]
            
            # Форматируем и отправляем ответ
            await utils.answer(
                status_message,
                f"<emoji document_id=5314250708508220914>✅</emoji> <b>Расшифровка голосового сообщения:</b>\n\n{transcription}"
            )
            
        except Exception as e:
            logger.error(f"Error in Grok AI audio transcription: {e}")
            await utils.answer(
                status_message, 
                self.strings["error"].format(error=str(e))
            )
        finally:
            # Очищаем временные файлы
            if media_data:
                await self._cleanup_media(media_data.get("file_path")))
