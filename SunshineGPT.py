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
import asyncio
import mimetypes
import random
from typing import Optional, List, Union, Tuple
import logging
from contextlib import suppress
from functools import wraps
from PIL import Image
from .. import loader, utils

logger = logging.getLogger(__name__)


class MediaProcessor:
    """Класс для обработки медиа файлов"""
    
    SUPPORTED_MIME_TYPES = {
        "image/jpeg", "image/jpg", "image/png", "image/gif", 
        "image/webp", "image/bmp", "image/tiff",
        "video/mp4", "video/avi", "video/mov", "video/webm",
        "video/mkv", "video/flv", "video/wmv",
        "audio/mp3", "audio/wav", "audio/ogg", "audio/m4a",
        "audio/flac", "audio/aac", "audio/wma",
        "application/pdf", "text/plain", "text/csv",
        "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
    
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
    MAX_IMAGE_SIZE = 4096
    
    @classmethod
    async def detect_mime_type(cls, file_path: str) -> Optional[str]:
        """Определяет MIME тип файла"""
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            
            if mime_type and mime_type in cls.SUPPORTED_MIME_TYPES:
                return mime_type
                
            if mime_type and mime_type.startswith("image/"):
                try:
                    with Image.open(file_path) as img:
                        format_map = {
                            "JPEG": "image/jpeg", "PNG": "image/png", 
                            "GIF": "image/gif", "WEBP": "image/webp",
                            "BMP": "image/bmp", "TIFF": "image/tiff"
                        }
                        return format_map.get(img.format, "image/jpeg")
                except Exception:
                    pass
                    
            return mime_type if mime_type in cls.SUPPORTED_MIME_TYPES else None
            
        except Exception as e:
            logger.error(f"Ошибка определения MIME типа: {e}")
            return None
    
    @classmethod
    async def process_media_file(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Обрабатывает медиа файл для отправки в Gemini"""
        try:
            mime_type = await cls.detect_mime_type(file_path)
            
            if not mime_type:
                return None, "Неподдерживаемый тип файла"
                
            file_size = os.path.getsize(file_path)
            
            if file_size > cls.MAX_FILE_SIZE:
                return None, f"Файл слишком большой ({file_size // 1024 // 1024} MB > 20 MB)"
                
            if mime_type.startswith("image/"):
                try:
                    with Image.open(file_path) as img:
                        if img.width > cls.MAX_IMAGE_SIZE or img.height > cls.MAX_IMAGE_SIZE:
                            img.thumbnail((cls.MAX_IMAGE_SIZE, cls.MAX_IMAGE_SIZE), Image.Resampling.LANCZOS)
                            optimized_path = file_path + "_optimized"
                            img.save(optimized_path, optimize=True, quality=85)
                            file_path = optimized_path
                except Exception as e:
                    return None, f"Ошибка обработки изображения: {e}"
                    
            return file_path, mime_type
            
        except Exception as e:
            logger.error(f"Ошибка обработки медиа: {e}")
            return None, str(e)


class GeminiAPI:
    """Класс для работы с Gemini API"""
    
    def __init__(self, config: dict):
        self.config = config
        
    def _setup_proxy(self):
        """Настраивает прокси если указан"""
        if self.config.get("proxy"):
            os.environ["HTTP_PROXY"] = self.config["proxy"]
            os.environ["HTTPS_PROXY"] = self.config["proxy"]
            logger.info(f"Прокси установлен: {self.config['proxy']}")
    
    async def setup_model(self) -> genai.GenerativeModel:
        """Настраивает и возвращает модель Gemini"""
        if not self.config.get("api_key"):
            raise ValueError("API ключ не указан")
            
        genai.configure(api_key=self.config["api_key"])
        
        generation_config = genai.types.GenerationConfig(
            temperature=self.config.get("temperature", 0.7),
            max_output_tokens=8192,
            response_mime_type="text/plain"
        )
        
        return genai.GenerativeModel(
            model_name=self.config.get("model_name", "gemini-1.5-flash"),
            system_instruction=self.config.get("system_instruction") or None,
            generation_config=generation_config
        )
    
    async def generate_content(self, content_parts: List) -> str:
        """Генерирует контент через Gemini API"""
        model = await self.setup_model()
        
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, content_parts),
                timeout=self.config.get("timeout", 60)
            )
            
            if not response or not response.text:
                return "Gemini вернул пустой ответ. Попробуйте переформулировать запрос."
                
            return response.text.strip()
            
        except asyncio.TimeoutError:
            raise Exception(f"Таймаут запроса ({self.config.get('timeout', 60)} сек)")
        except Exception as e:
            logger.error(f"Ошибка Gemini API: {e}")
            raise


def retry_decorator(max_retries: int = 3, delay_base: float = 2.0):
    """Декоратор для повторных попыток выполнения функции при ошибках"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Попытка {attempt + 1}/{max_retries} для {func.__name__} неудачна: {e}"
                    )
                    if attempt == max_retries - 1:
                        break
                    
                    wait_time = delay_base ** attempt
                    await asyncio.sleep(wait_time)
            
            raise last_exception
        return wrapper
    return decorator


@loader.tds
class SunshineGPT(loader.Module):
    """Улучшенный модуль для работы с Google Gemini AI"""

    strings = {
        "name": "SunshineGPT",
        "no_api_key": "<emoji document_id=6005570495603282482>🔑</emoji> <b>API ключ не указан!</b>\n\n"
                     "Получите ключ на: <code>aistudio.google.com/apikey</code>\n"
                     "Установите через: <code>.config SunshineGPT api_key ВАШ_КЛЮЧ</code>",
        "no_prompt": "<emoji document_id=5884510167986343350>💬</emoji> <b>Использование команды:</b>\n\n"
                    "• <code>.gpt ваш вопрос</code> - задать вопрос\n"
                    "• <code>.gpt</code> (ответ на медиа) - анализ медиа\n"
                    "• <code>.gpt ваш вопрос</code> (ответ на медиа) - вопрос о медиа",
        "processing": "<emoji document_id=5931415565955503486>🤖</emoji> <b>Gemini обрабатывает запрос...</b>",
        "processing_media": "<emoji document_id=5775949822993371030>🖼</emoji> <b>Анализирую медиа...</b>",
        "processing_audio": "<emoji document_id=5891249688933305846>🎵</emoji> <b>Обрабатываю аудио...</b>",
        "processing_video": "<emoji document_id=6005986106703613755>📷</emoji> <b>Анализирую видео...</b>",
        "processing_sticker": "<emoji document_id=5775949822993371030>🎭</emoji> <b>Анализирую стикер...</b>",
        "processing_document": "<emoji document_id=5877332341331857066>📄</emoji> <b>Обрабатываю документ...</b>",
        "error": "<emoji document_id=5778527486270770928>❌</emoji> <b>Ошибка:</b> <code>{}</code>",
        "media_error": "<emoji document_id=5877332341331857066>📁</emoji> <b>Ошибка обработки медиа:</b> <code>{}</code>",
        "unsupported_media": "<emoji document_id=5872829476143894491>🚫</emoji> <b>Неподдерживаемый тип медиа</b>\n\n"
                            "Поддерживаются: изображения, видео, аудио, документы",
        "response_header": "<emoji document_id=5931415565955503486>🤖</emoji> <b>Ответ от Gemini:</b>\n\n",
        "question_header": "<emoji document_id=5879585266426973039>🌐</emoji> <b>Вопрос:</b> <code>{}</code>\n\n",
        "download_failed": "<emoji document_id=5778527486270770928>❌</emoji> <b>Не удалось скачать медиа файл</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                "API ключ для Gemini AI",
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "model_name",
                "gemini-1.5-flash",
                "Модель Gemini AI",
                validator=loader.validators.Choice([
                    "gemini-1.5-flash",
                    "gemini-1.5-pro", 
                    "gemini-1.5-flash-preview",
                    "gemini-1.5-pro-preview",
                    "gemini-pro",
                    "gemini-pro-vision"
                ])
            ),
            loader.ConfigValue(
                "system_instruction",
                "Ты полезный AI-ассистент. Отвечай кратко, информативно и дружелюбно.",
                "Системная инструкция для AI",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "temperature",
                0.7,
                "Температура генерации (0.0-1.0)",
                validator=loader.validators.Float(minimum=0.0, maximum=1.0)
            ),
            loader.ConfigValue(
                "max_retries",
                3,
                "Количество повторных попыток",
                validator=loader.validators.Integer(minimum=1, maximum=5)
            ),
            loader.ConfigValue(
                "timeout",
                60,
                "Таймаут запроса (секунды)",
                validator=loader.validators.Integer(minimum=10, maximum=300)
            ),
            loader.ConfigValue(
                "proxy",
                "",
                "HTTP прокси (http://proxy:port)",
                validator=loader.validators.String()
            )
        )
        
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
            "<emoji document_id=5447223407093497907>☺️</emoji>",
            "<emoji document_id=6046616063532078187>🇩🇪</emoji>",
            "<emoji document_id=6046335370239416531>🌟</emoji>",
            "<emoji document_id=6044327262575141199>🌟</emoji>",
            "<emoji document_id=6046225998897223421>👀</emoji>",
            "<emoji document_id=6046562814527543035>🤩</emoji>",
            "<emoji document_id=6044261085719041523>😎</emoji>",
            "<emoji document_id=6044091335726601513>🤩</emoji>",
            "<emoji document_id=6046633015767996424>😋</emoji>",
            "<emoji document_id=6046372495936721916>🤩</emoji>",
            "<emoji document_id=6046236414192915496>😎</emoji>",
            "<emoji document_id=6046410905829251121>💥</emoji>",
            "<emoji document_id=6046322944899027585>🔪</emoji>",
            "<emoji document_id=6044004585977157491>🌟</emoji>"
        ]
        
        self.gemini_api = None
        self.temp_files = set()

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.client = client
        self.db = db
        
        # Инициализируем API
        self.gemini_api = GeminiAPI(self.config)
        self.gemini_api._setup_proxy()

    def _get_random_emoji(self) -> str:
        """Возвращает случайное эмодзи"""
        return random.choice(self.emojis)

    def _get_media_type_and_status(self, reply) -> Tuple[str, str]:
        """Определяет тип медиа и возвращает соответствующий статус"""
        if reply.photo:
            return "image", self.strings["processing_media"]
        elif reply.video or reply.video_note:
            return "video", self.strings["processing_video"]
        elif hasattr(reply, 'gif') and reply.gif:
            return "gif", self.strings["processing_video"]
        elif reply.voice or reply.audio:
            return "audio", self.strings["processing_audio"]
        elif reply.sticker:
            return "sticker", self.strings["processing_sticker"]
        elif reply.document:
            return "document", self.strings["processing_document"]
        else:
            return "unknown", self.strings["processing_media"]

    def _cleanup_temp_files(self):
        """Очищает временные файлы"""
        for file_path in self.temp_files.copy():
            if os.path.exists(file_path):
                with suppress(Exception):
                    os.remove(file_path)
                    self.temp_files.remove(file_path)

    @retry_decorator()
    async def _process_gemini_request(self, content_parts: List) -> str:
        """Обрабатывает запрос к Gemini с повторными попытками"""
        return await self.gemini_api.generate_content(content_parts)

    @loader.command(alias="gpt")
    async def gpt(self, message):
        """Отправить запрос к Gemini AI"""
        
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return
            
        prompt = utils.get_args_raw(message)
        media_file = None
        show_question = True
        status_msg = None
        
        try:
            # Обработка ответа на сообщение
            if message.is_reply:
                reply = await message.get_reply_message()
                
                if reply.media:
                    # Определяем тип медиа и статус
                    media_type, status_text = self._get_media_type_and_status(reply)
                    status_msg = await utils.answer(message, status_text)
                    
                    try:
                        # Скачиваем медиа файл
                        media_file = await reply.download_media()
                        if not media_file:
                            await utils.answer(status_msg, self.strings["download_failed"])
                            return
                        
                        # Добавляем файл в список для очистки
                        self.temp_files.add(media_file)
                        
                        # Обрабатываем медиа файл
                        processed_file, mime_type = await MediaProcessor.process_media_file(media_file)
                        if not processed_file:
                            await utils.answer(status_msg, self.strings["media_error"].format(mime_type))
                            return
                        
                        # Если создан оптимизированный файл, добавляем его в список для очистки
                        if processed_file != media_file:
                            self.temp_files.add(processed_file)
                        
                        media_file = processed_file
                        
                        # Если промпт не указан, используем стандартный
                        if not prompt:
                            prompt = "Опиши детально что изображено на этом медиа"
                            show_question = False
                            
                    except Exception as e:
                        await utils.answer(status_msg, self.strings["media_error"].format(str(e)))
                        return
                else:
                    # Если это текстовое сообщение без медиа
                    if not prompt and hasattr(reply, 'text') and reply.text:
                        prompt = reply.text
                    status_msg = await utils.answer(message, self.strings["processing"])
            else:
                status_msg = await utils.answer(message, self.strings["processing"])
            
            # Проверяем наличие промпта
            if not prompt:
                await utils.answer(status_msg, self.strings["no_prompt"])
                return
            
            # Готовим контент для отправки
            content_parts = [genai.protos.Part(text=prompt)]
            
            # Добавляем медиа файл если есть
            if media_file:
                try:
                    mime_type = await MediaProcessor.detect_mime_type(media_file)
                    if mime_type:
                        with open(media_file, "rb") as f:
                            content_parts.append(genai.protos.Part(
                                inline_data=genai.protos.Blob(
                                    mime_type=mime_type,
                                    data=f.read()
                                )
                            ))
                    else:
                        await utils.answer(status_msg, self.strings["unsupported_media"])
                        return
                except Exception as e:
                    await utils.answer(status_msg, self.strings["media_error"].format(str(e)))
                    return
            
            # Отправляем запрос к Gemini
            response_text = await self._process_gemini_request(content_parts)
            
            # Формируем финальный ответ
            final_response = ""
            
            if show_question:
                final_response += self.strings["question_header"].format(prompt)
                
            final_response += self.strings["response_header"] + response_text
            final_response += f" {self._get_random_emoji()}"
                
            await utils.answer(status_msg, final_response)
            
        except Exception as e:
            logger.exception(f"Ошибка в команде gpt: {e}")
            try:
                error_message = self.strings["error"].format(str(e))
                error_message += f" {self._get_random_emoji()}"
                target_message = status_msg if status_msg else message
                await utils.answer(target_message, error_message)
            except Exception as inner_e:
                logger.error(f"Критическая ошибка при отправке сообщения об ошибке: {inner_e}")
        finally:
            # Очищаем временные файлы
            self._cleanup_temp_files()
