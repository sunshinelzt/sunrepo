# meta developer: @sunshinelzt

import asyncio
import logging
import os
import re
import base64
import mimetypes
from typing import Union, List, Optional, Dict, Any

try:
    import requests
except ImportError:
    requests = None

from telethon.tl.types import Message, DocumentAttributeFilename

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class GrokAIMod(loader.Module):
    """Мощный модуль для взаимодействия с Grok AI с поддержкой мультимедиа"""
    
    strings = {
        "name": "GrokAI",
        "no_args": "<emoji document_id=5854929766146118183>❌</emoji> <b>Необходимо указать запрос или ответить на сообщение</b>",
        "no_token": "<emoji document_id=5854929766146118183>❌</emoji> <b>API ключ не установлен!</b>\n<i>Используйте </i><code>.groksetup</code><i> для установки ключа</i>",
        "asking_grok": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Запрашиваю Grok AI...</b>",
        "answer": """<emoji document_id=5355148941878900494>🌐</emoji> <b>Ответ от Grok AI:</b> 

{answer}

<emoji document_id=5785419053354979106>❔</emoji> <b>Запрос:</b> {question}""",
        "error": "<emoji document_id=5854929766146118183>❌</emoji> <b>Ошибка при запросе к Grok AI:</b>\n<code>{error}</code>",
        "processing_media": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Обрабатываю медиафайл...</b>",
        "media_processed": "<emoji document_id=5314250708508220914>✅</emoji> <b>Медиафайл обработан успешно!</b>",
        "no_media": "<emoji document_id=5854929766146118183>❌</emoji> <b>Не удалось обработать медиафайл</b>",
        "media_too_large": "<emoji document_id=5854929766146118183>❌</emoji> <b>Медиафайл слишком большой (>25МБ)</b>",
        "generating_image": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Генерирую изображение...</b>",
        "unknown_type": "<emoji document_id=5854929766146118183>❌</emoji> <b>Неизвестный тип файла</b>",
        "uploading_file": "<emoji document_id=5325787248363314644>🔄</emoji> <b>Загружаю файл на сервер...</b>",
        "file_ready": "<emoji document_id=5314250708508220914>✅</emoji> <b>Файл загружен и готов к анализу!</b>",
        "config_saved": "<emoji document_id=5314250708508220914>✅</emoji> <b>Настройки сохранены!</b>",
        "setup_guide": """
<emoji document_id=5467928559664242360>⚙️</emoji> <b>Настройка модуля GrokAI</b>

<emoji document_id=5467666648263564704>🔑</emoji> <b>API ключ</b>: <code>{api_key}</code>
<emoji document_id=5467894085538451347>🤖</emoji> <b>Модель</b>: <code>{model}</code>
<emoji document_id=5467894085538451347>🎚️</emoji> <b>Температура</b>: <code>{temperature}</code>
<emoji document_id=5467894085538451347>📊</emoji> <b>Макс. токенов</b>: <code>{max_tokens}</code>

<emoji document_id=5210952531676504517>ℹ️</emoji> <b>Для изменения настроек используйте:</b>
<code>.groksetup ключ значение</code>

<b>Возможные ключи:</b>
<code>api_key</code> - API ключ от X.ai
<code>model</code> - модель (<code>grok-1</code>, <code>grok-2</code>, <code>grok-vision</code>)
<code>temperature</code> - температура генерации (0.0-1.0)
<code>max_tokens</code> - максимальное число токенов
<code>beautify</code> - украшать вывод (<code>true</code>/<code>false</code>)
<code>media_support</code> - поддержка медиа (<code>true</code>/<code>false</code>)
""",
        "no_requests": "<emoji document_id=5854929766146118183>❌</emoji> <b>Установите модуль requests:</b>\n<code>pip install requests</code>",
        "invalid_key": "<emoji document_id=5854929766146118183>❌</emoji> <b>Неверный ключ настройки</b>",
        "image_caption": "<emoji document_id=5314250708508220914>✅</emoji> <b>Изображение по запросу:</b> {prompt}"
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "api_key", None, "API ключ Grok AI",
            "model", "grok-2", "Модель Grok AI (grok-1, grok-2, grok-vision)",
            "max_tokens", 4096, "Максимальное количество токенов в ответе",
            "temperature", 0.7, "Температура генерации (0.0-1.0)",
            "beautify", True, "Украшать вывод ответов",
            "media_support", True, "Поддержка медиафайлов"
        )

    async def client_ready(self, client, db):
        """Инициализация модуля при загрузке"""
        self._client = client
        self._db = db
        
        # Проверяем наличие модуля requests
        if requests is None:
            logger.error("Модуль requests не установлен")

    def _make_grok_request(self, endpoint: str, data: dict) -> dict:
        """Отправляет запрос к API Grok"""
        if not self.config["api_key"]:
            raise ValueError("API ключ не установлен")
            
        if requests is None:
            raise ValueError("Модуль requests не установлен")
        
        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"https://api.x.ai/v1/{endpoint}",
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
            # Определяем тип медиа
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
                
            # Скачиваем файл
            file_path = await self._client.download_media(message.media, file="groktemp_")
            
            if not file_path:
                return {"error": "no_media"}
                
            # Получаем MIME тип файла
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"
                
            # Конвертируем стикеры в изображения
            if media_type == "sticker" and mime_type == "image/webp":
                media_type = "image"
                
            # Читаем файл в base64    
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
            logger.error(f"Ошибка обработки медиа: {e}")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            return {"error": str(e)}

    async def _cleanup_media(self, file_path: Optional[str]) -> None:
        """Очищает временные файлы"""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Ошибка удаления временного файла: {e}")

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
            # Формируем контент для запроса к Grok
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
            logger.error(f"Ошибка обработки медиаконтента: {e}")
            await utils.answer(media_status, self.strings["error"].format(error=str(e)))
            await self._cleanup_media(file_path)
            return None

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

    @loader.command(ru_doc="Задать вопрос Grok AI")
    async def grok(self, message: Message):
        """Задать вопрос Grok AI"""
        if requests is None:
            return await utils.answer(message, self.strings["no_requests"])
        
        # Проверяем наличие ответа
        reply_to = await message.get_reply_message()
        q = utils.get_args_raw(message)
        
        # Проверяем, что есть вопрос либо в аргументах, либо в ответе
        if not q and not reply_to:
            return await utils.answer(message, self.strings["no_args"])
            
        # Проверяем наличие токена
        if not self.config['api_key']:
            return await utils.answer(message, self.strings["no_token"])
            
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
                return await utils.answer(status_message, self.strings["no_args"])
                
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
            if self.config["beautify"]:
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
            logger.error(f"Ошибка в запросе к Grok AI: {e}")
            await utils.answer(
                status_message, 
                self.strings["error"].format(error=str(e))
            )
        finally:
            # Очищаем временные файлы
            if media_data:
                await self._cleanup_media(media_data.get("file_path"))

    @loader.command(ru_doc="Сгенерировать изображение с помощью Grok AI")
    async def grokimg(self, message: Message):
        """Сгенерировать изображение с помощью Grok AI"""
        if requests is None:
            return await utils.answer(message, self.strings["no_requests"])
            
        q = utils.get_args_raw(message)
        if not q:
            return await utils.answer(message, self.strings["no_args"])
            
        if not self.config['api_key']:
            return await utils.answer(message, self.strings["no_token"])
            
        # Отправляем статус ожидания
        status_message = await utils.answer(message, self.strings['generating_image'])
        if isinstance(status_message, list):
            status_message = status_message[0]
            
        try:
            # Создаем запрос на генерацию изображения у Grok
            data = {
                "model": "grok-vision",  # Используем модель для изображений
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
                caption=self.strings["image_caption"].format(prompt=q)
            )
            
            # Удаляем сообщение со статусом
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {e}")
            await utils.answer(
                status_message, 
                self.strings["error"].format(error=str(e))
            )

    @loader.command(ru_doc="Настройка модуля Grok AI")
    async def groksetup(self, message: Message):
        """Настройка модуля Grok AI"""
        args = utils.get_args_raw(message).split(maxsplit=1)
        
        # Если нет аргументов - показываем текущие настройки
        if not args or not args[0]:
            return await utils.answer(
                message,
                self.strings["setup_guide"].format(
                    api_key=self.config["api_key"] or "не установлен",
                    model=self.config["model"],
                    temperature=self.config["temperature"],
                    max_tokens=self.config["max_tokens"]
                )
            )
            
        # Если есть аргументы - меняем настройки
        try:
            key, value = args[0], args[1] if len(args) > 1 else None
            
            if key == "api_key":
                self.config["api_key"] = value
            elif key == "model":
                if value in ["grok-1", "grok-2", "grok-vision"]:
                    self.config["model"] = value
                else:
                    return await utils.answer(message, self.strings["invalid_key"])
            elif key == "temperature":
                self.config["temperature"] = float(value)
            elif key == "max_tokens":
                self.config["max_tokens"] = int(value)
            elif key == "beautify":
                self.config["beautify"] = value.lower() == "true"
            elif key == "media_support":
                self.config["media_support"] = value.lower() == "true"
            else:
                return await utils.answer(message, self.strings["invalid_key"])
                
            await utils.answer(message, self.strings["config_saved"])
            
        except Exception as e:
            logger.error(f"Ошибка при настройке: {e}")
            await utils.answer(
                message, 
                self.strings["error"].format(error=str(e))
            )
