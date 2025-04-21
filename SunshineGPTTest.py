__version__ = (1, 4, 8 , 8)

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
import base64
import hashlib
from typing import Tuple, Optional, Dict, Any, List, Union, Callable
import logging
from contextlib import suppress
from functools import wraps
from PIL import Image
from .. import loader, utils
import aiohttp


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


class AIModel:
    """Базовый класс для моделей ИИ"""
    def __init__(self, api_key: str, proxy: Optional[str] = None, timeout: int = 60):
        self.api_key = api_key
        self.proxy = proxy
        self.timeout = timeout

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Генерирует текстовый ответ на основе запроса"""
        raise NotImplementedError("Subclasses must implement this method")

    async def generate_with_image(self, prompt: str, image_data: bytes, mime_type: str, system_prompt: Optional[str] = None) -> str:
        """Генерирует текстовый ответ на основе изображения и запроса"""
        raise NotImplementedError("Subclasses must implement this method")

    async def get_connector_and_timeout(self):
        """Возвращает соединение и таймаут для HTTP-запросов"""
        conn = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        return conn, timeout


class GeminiModel(AIModel):
    """Класс для работы с моделями Gemini от Google"""
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash", system_instruction: str = "", proxy: Optional[str] = None, timeout: int = 60):
        super().__init__(api_key, proxy, timeout)
        self.model_name = model_name
        self.system_instruction = system_instruction
        if proxy:
            os.environ["HTTP_PROXY"] = proxy
            os.environ["HTTPS_PROXY"] = proxy

    @retry_decorator()
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Генерирует текстовый ответ с помощью Gemini"""
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt or self.system_instruction or None,
        )
        
        content_parts = [genai.protos.Part(text=prompt)]
        response = model.generate_content(content_parts)
        return response.text.strip() if response.text else "Пустой ответ от Gemini."

    @retry_decorator()
    async def generate_with_image(self, prompt: str, image_data: bytes, mime_type: str, system_prompt: Optional[str] = None) -> str:
        """Генерирует текстовый ответ на основе изображения и запроса"""
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt or self.system_instruction or None,
        )
        
        content_parts = [
            genai.protos.Part(text=prompt),
            genai.protos.Part(
                inline_data=genai.protos.Blob(
                    mime_type=mime_type,
                    data=image_data
                )
            )
        ]
        
        response = model.generate_content(content_parts)
        return response.text.strip() if response.text else "Пустой ответ от Gemini."


class ChatGPTModel(AIModel):
    """Класс для работы с моделями ChatGPT от OpenAI"""
    def __init__(self, api_key: str, model_name: str = "gpt-4o", proxy: Optional[str] = None, timeout: int = 60):
        super().__init__(api_key, proxy, timeout)
        self.model_name = model_name

    @retry_decorator()
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Генерирует текстовый ответ с помощью ChatGPT"""
        conn, timeout = await self.get_connector_and_timeout()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": []
        }
        
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
            
        payload["messages"].append({"role": "user", "content": prompt})
        
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                proxy=self.proxy
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {error_text}")
                    raise Exception(f"Ошибка API OpenAI: {response.status} - {error_text}")

    @retry_decorator()
    async def generate_with_image(self, prompt: str, image_data: bytes, mime_type: str, system_prompt: Optional[str] = None) -> str:
        """Генерирует текстовый ответ на основе изображения и запроса"""
        conn, timeout = await self.get_connector_and_timeout()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert image data to base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        image_content_type = mime_type
        
        # Prepare messages for the API
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Add user message with image
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_content_type};base64,{base64_image}"
                    }
                }
            ]
        })
        
        payload = {
            "model": "gpt-4o",  # Using GPT-4 with vision capabilities
            "messages": messages
        }
        
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                proxy=self.proxy
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {error_text}")
                    raise Exception(f"Ошибка API OpenAI: {response.status} - {error_text}")


class DeepSeekModel(AIModel):
    """Класс для работы с моделями DeepSeek"""
    def __init__(self, api_key: str, model_name: str = "deepseek-chat", proxy: Optional[str] = None, timeout: int = 60):
        super().__init__(api_key, proxy, timeout)
        self.model_name = model_name

    @retry_decorator()
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Генерирует текстовый ответ с помощью DeepSeek"""
        conn, timeout = await self.get_connector_and_timeout()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": []
        }
        
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
            
        payload["messages"].append({"role": "user", "content": prompt})
        
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                proxy=self.proxy
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                else:
                    error_text = await response.text()
                    logger.error(f"DeepSeek API error: {error_text}")
                    raise Exception(f"Ошибка API DeepSeek: {response.status} - {error_text}")

    async def generate_with_image(self, prompt: str, image_data: bytes, mime_type: str, system_prompt: Optional[str] = None) -> str:
        """Генерирует текстовый ответ на основе изображения и запроса - для DeepSeek базовая версия не поддерживает мультимодальность"""
        raise NotImplementedError("DeepSeek не поддерживает мультимодальный ввод в базовой версии API")


class ImageGenerator:
    """Класс для генерации изображений с различными моделями"""
    def __init__(self, api_key: str, model_name: str = "flux", proxy: Optional[str] = None, timeout: int = 60, max_retries: int = 3):
        self.api_key = api_key
        self.model_name = model_name
        self.proxy = proxy
        self.timeout = timeout
        self.max_retries = max_retries

    @retry_decorator(max_retries=3)
    async def generate(self, prompt: str) -> Tuple[Optional[str], Union[float, str]]:
        """Генерирует изображение с помощью различных моделей"""
        start_time = time.time()

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "response_format": "url"
        }

        conn = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}", 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            async with session.post(
                "https://api.kshteam.top/v1/images/generate", 
                headers=headers, 
                json=payload, 
                proxy=self.proxy
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


@loader.tds
class SunshineGPTEnhanced(loader.Module):
    """
    Расширенный модуль для общения с различными AI моделями:
    
    • Gemini (Google AI)
    • GPT-4o (OpenAI)
    • DeepSeek AI
    
    Также включает генерацию изображений с различными моделями:
    
    • Flux, Flux Pro, DALL-E 3, MidJourney и другие
    
    Поддерживает анализ истории чата, работу с медиафайлами и многое другое.
    """

    strings = {
        "name": "SunshineGPTEnhanced",
        
        # Общие сообщения
        "no_api_key": "<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Проверьте конфигурацию модуля.</b>",
        "no_prompt": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Введите запрос или ответьте на сообщение (изображение, видео, GIF, стикер, голосовое)</b>",
        "processing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>{}</b>",
        "request_sent": "<emoji document_id=5325547803936572038>✨</emoji> <b>Запрос отправлен, ожидайте ответ...</b>",
        "error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка:</b> {}",
        "server_error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка сервера:</b> {}",
        "empty_response": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ответ пустой. Попробуйте переформулировать запрос.</b>",
        "empty_media": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Не удалось открыть изображение:</b> {}",
        "empty_content": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка: Запрос должен содержать текст или медиа.</b>",
        "describe_this": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Опиши это...</b>",
        
        # Сообщения для генерации изображений
        "generating_image": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Сервер генерирует картинку, пожалуйста, подождите...</b>",
        "no_image_prompt": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Пожалуйста, укажите описание для генерации изображения.</b>",
        "image_caption": "<blockquote><emoji document_id=5465143921912846619>💭</emoji> <b>Промт:</b> <code>{prompt}</code></blockquote>\n"
                         "<blockquote><emoji document_id=5877260593903177342>⚙️</emoji> <b>Модель:</b> <code>{model}</code></blockquote>\n"
                         "<blockquote><emoji document_id=5199457120428249992>🕘</emoji> <b>Время генерации:</b> {time} сек.</blockquote>",
        
        # Сообщения для анализа истории
        "collecting_history": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю сообщений для {}...</b>",
        "collecting_chat": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю чата...</b>",
        "user_analysis_title": "<emoji document_id=5873121512445187130>❓</emoji> <b>Что сегодня обсуждал {}?</b>",
        "chat_analysis_title": "<emoji document_id=5873121512445187130>❓</emoji> <b>Что сегодня обсуждали участники чата?</b>",
        
        # Сообщения для различных моделей AI
        "gemini_response": "<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini:</b> {} {}",
        "gpt_response": "<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от GPT:</b> {} {}",
        "deepseek_response": "<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от DeepSeek:</b> {} {}",
        
        # Вопросы и ответы
        "question": "<emoji document_id=5443038326535759644>💬</emoji> <b>Вопрос:</b> {}",
        
        # Ошибки API ключей
        "no_gemini_key": "<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ для Gemini не указан. Получите его на aistudio.google.com/apikey</b>",
        "no_openai_key": "<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ для OpenAI не указан. Получите его на platform.openai.com</b>",
        "no_deepseek_key": "<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ для DeepSeek не указан. Получите его на platform.deepseek.com</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            # Gemini конфигурация
            loader.ConfigValue(
                "gemini_api_key", 
                "", 
                "API ключ для Gemini AI (aistudio.google.com/apikey)", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "gemini_model_name", 
                "gemini-1.5-flash", 
                "Модель для Gemini AI. Примеры: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "gemini_system_instruction", 
                "", 
                "Инструкция для Gemini AI", 
                validator=loader.validators.String()
            ),
            
            # OpenAI конфигурация
            loader.ConfigValue(
                "openai_api_key", 
                "", 
                "API ключ для OpenAI (platform.openai.com)", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "openai_model_name", 
                "gpt-4o", 
                "Модель для OpenAI. Примеры: gpt-4o, gpt-4-turbo, gpt-3.5-turbo", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "openai_system_instruction", 
                "", 
                "Инструкция для OpenAI", 
                validator=loader.validators.String()
            ),
            
            # DeepSeek конфигурация
            loader.ConfigValue(
                "deepseek_api_key", 
                "", 
                "API ключ для DeepSeek (platform.deepseek.com)", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "deepseek_model_name", 
                "deepseek-chat", 
                "Модель для DeepSeek. Примеры: deepseek-chat, deepseek-coder", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "deepseek_system_instruction", 
                "", 
                "Инструкция для DeepSeek", 
                validator=loader.validators.String()
            ),
            
            # Генерация изображений
            loader.ConfigValue(
                "api_key_image", 
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", 
                "Ключ для API генерации изображений", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "default_image_model", 
                "flux", 
                "Модель для генерации изображений. Примеры: flux, flux-pro, flux-dev, flux-schnell, sdxl-turbo, dall-e-3, midjourney", 
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
                "default_ai", 
                "gemini", 
                "AI модель по умолчанию для команды .gpt (gemini, openai, deepseek)", 
                validator=loader.validators.String()
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
            "<emoji document_id=5445159739732279716>🫥</emoji>"
        ]
        
        # Для хранения созданных моделей
        self._models = {}

    async def client_ready(self, client, db):
        """Инициализация клиента"""
        self.client = client
        self.db = db
        
        if self.config["proxy"]:
            os.environ["HTTP_PROXY"] = self.config["proxy"]
            os.environ["HTTPS_PROXY"] = self.config["proxy"]
            logger.info(f"Proxy set to {self.config['proxy']}")

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
                
        except AttributeError as e:
            logger.error(f"Error getting mime type: {e}")
            return None

        return None

    async def _get_random_emoji(self) -> str:
        """Возвращает случайный эмодзи из списка"""
        return random.choice(self.emojis)
        
    def _get_model(self, model_type: str):
        """Возвращает инициализированную модель AI по типу"""
        if model_type in self._models:
            return self._models[model_type]
            
        if model_type == "gemini":
            if not self.config["gemini_api_key"]:
                raise ValueError("API ключ для Gemini не указан")
                
            model = GeminiModel(
                api_key=self.config["gemini_api_key"],
                model_name=self.config["gemini_model_name"],
                system_instruction=self.config["gemini_system_instruction"],
                proxy=self.config["proxy"],
                timeout=self.config["timeout"]
            )
            
        elif model_type == "openai":
            if not self.config["openai_api_key"]:
                raise ValueError("API ключ для OpenAI не указан")
                
            model = ChatGPTModel(
                api_key=self.config["openai_api_key"],
                model_name=self.config["openai_model_name"],
                proxy=self.config["proxy"],
                timeout=self.config["timeout"]
            )
            
        elif model_type == "deepseek":
            if not self.config["deepseek_api_key"]:
                raise ValueError("API ключ для DeepSeek не указан")
                
            model = DeepSeekModel(
                api_key=self.config["deepseek_api_key"],
                model_name=self.config["deepseek_model_name"],
                proxy=self.config["proxy"],
                timeout=self.config["timeout"]
            )
            
        else:
            raise ValueError(f"Неизвестный тип модели: {model_type}")
            
        # Сохраняем модель для повторного использования
        self._models[model_type] = model
        return model

    async def _process_ai_query(self, model_type: str, prompt: str, media_path: Optional[str] = None, mime_type: Optional[str] = None, system_prompt: Optional[str] = None) -> str:
        """Обрабатывает запрос к AI с опциональным медиа файлом"""
        try:
            model = self._get_model(model_type)
            
            if media_path and mime_type and mime_type.startswith("image"):
                with open(media_path, "rb") as f:
                    image_data = f.read()
                    
                result = await model.generate_with_image(prompt, image_data, mime_type, system_prompt)
            else:
                result = await model.generate_text(prompt, system_prompt)
                
            return result.strip() if result else self.strings["empty_response"]
            
        except Exception as e:
            logger.exception(f"Error in AI query processing: {e}")
            raise

    async def generate_image(self, prompt: str) -> Tuple[Optional[str], Union[float, str]]:
        """Генерация изображения с API"""
        generator = ImageGenerator(
            api_key=self.config["api_key_image"],
            model_name=self.config["default_image_model"],
            proxy=self.config["proxy"],
            timeout=self.config["timeout"],
            max_retries=self.config["max_retries"]
        )
        
        return await generator.generate(prompt)

    async def _process_ai_command(self, message, model_type: str, response_template: str):
        """Общая логика обработки команд AI моделей"""
        if model_type == "gemini" and not self.config["gemini_api_key"]:
            await utils.answer(message, self.strings["no_gemini_key"])
            return
        elif model_type == "openai" and not self.config["openai_api_key"]:
            await utils.answer(message, self.strings["no_openai_key"])
            return
        elif model_type == "deepseek" and not self.config["deepseek_api_key"]:
            await utils.answer(message, self.strings["no_deepseek_key"])
            return

        prompt = utils.get_args_raw(message)
        media_path = None
        img = None
        show_question = True
        mime_type = None

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

            # Выбираем системный промпт в зависимости от модели
            if model_type == "gemini":
                system_prompt = self.config["gemini_system_instruction"]
            elif model_type == "openai":
                system_prompt = self.config["openai_system_instruction"]
            elif model_type == "deepseek":
                system_prompt = self.config["deepseek_system_instruction"]
            else:
                system_prompt = None

            reply_text = await self._process_ai_query(model_type, prompt, media_path, mime_type, system_prompt)
            random_emoji = await self._get_random_emoji()

            if show_question and prompt != "Опиши это":
                response = f"{self.strings['question'].format(prompt)}\n\n{response_template.format(reply_text, random_emoji)}"
            else:
                response = f"\n{response_template.format(reply_text, random_emoji)}"
            
            await utils.answer(message, response)
            
        except ValueError as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
        except Exception as e:
            logger.exception(f"Error in AI command: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))
        finally:
            if media_path and os.path.exists(media_path):
                with suppress(Exception):
                    os.remove(media_path)

    @loader.command(alias="gpt")
    async def ai(self, message):
        """— отправить запрос к AI (используется модель по умолчанию из настроек)"""
        model_type = self.config["default_ai"]
        
        if model_type == "gemini":
            response_template = self.strings["gemini_response"]
        elif model_type == "openai":
            response_template = self.strings["gpt_response"]
        elif model_type == "deepseek":
            response_template = self.strings["deepseek_response"]
        else:
            response_template = self.strings["gemini_response"]
            model_type = "gemini"
            
        await self._process_ai_command(message, model_type, response_template)

    @loader.command()
    async def gemini(self, message):
        """— отправить запрос к Google Gemini"""
        await self._process_ai_command(message, "gemini", self.strings["gemini_response"])

    @loader.command()
    async def cgpt(self, message):
        """— отправить запрос к ChatGPT (OpenAI)"""
        await self._process_ai_command(message, "openai", self.strings["gpt_response"])

    @loader.command()
    async def dseek(self, message):
        """— отправить запрос к DeepSeek AI"""
        await self._process_ai_command(message, "deepseek", self.strings["deepseek_response"])

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
        """- анализ сообщений чата или пользователя (можно использовать с ответом на сообщение)"""
        if self.config["default_ai"] == "gemini" and not self.config["gemini_api_key"]:
            await utils.answer(message, self.strings["no_gemini_key"])
            return
        elif self.config["default_ai"] == "openai" and not self.config["openai_api_key"]:
            await utils.answer(message, self.strings["no_openai_key"])
            return
        elif self.config["default_ai"] == "deepseek" and not self.config["deepseek_api_key"]:
            await utils.answer(message, self.strings["no_deepseek_key"])
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
            async for msg in self.client.iter_messages(chat_id, limit=history_limit):
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
                
            all_messages.sort(key=lambda x: x["time"])
            
            context = "Ниже представлена история сообщений из чата. "
            if user:
                context += f"Проанализируй все сообщения пользователя {user_name} и составь краткую сводку о чем он писал сегодня, "
                context += "его интересах, вопросах, общем настроении. Выдели основные темы обсуждения. В конце напиши шутку про то что ты прочитал и запиши как Шутка от ИИ:"
                title = self.strings["user_analysis_title"].format(user_name)
            else:
                context += "Проанализируй все сообщения и составь краткую сводку о том, что обсуждалось в чате сегодня. "
                context += "Выдели основные темы обсуждения, активных участников, общее настроение беседы. В конце напиши шутку про то что ты прочитал и запиши как Шутка от ИИ:"
                title = self.strings["chat_analysis_title"]
                
            history_text = "\n".join([f"[{msg['time']}] {msg['sender']}: {msg['text']}" for msg in all_messages])
            
            prompt = f"{context}\n\nИстория сообщений:\n{history_text}"
            
            processing_msg = await utils.answer(
                message, 
                self.strings["processing"].format("Анализирую сообщения...")
            )
            
            # Выбираем модель для анализа истории
            model_type = self.config["default_ai"]
            analysis = await self._process_ai_query(model_type, prompt)
            
            random_emoji = await self._get_random_emoji()
            result = f"{title}\n\n{analysis} {random_emoji}"
            
            await utils.answer(processing_msg, result)
            
        except Exception as e:
            logger.exception(f"Error in ghist: {e}")
            await utils.answer(message, self.strings["error"].format(e))

    @loader.command()
    async def amodels(self, message):
        """— показать список доступных моделей ИИ"""
        available_models = {
            "Gemini": [
                "gemini-1.5-flash", 
                "gemini-1.5-pro", 
                "gemini-2.0-flash-exp", 
                "gemini-2.0-flash-thinking-exp-1219"
            ],
            "OpenAI": [
                "gpt-4o", 
                "gpt-4-turbo", 
                "gpt-4-vision", 
                "gpt-3.5-turbo"
            ],
            "DeepSeek": [
                "deepseek-chat", 
                "deepseek-coder", 
                "deepseek-lite"
            ],
            "Генерация изображений": [
                "flux", 
                "flux-pro", 
                "flux-dev", 
                "flux-schnell", 
                "dall-e-3", 
                "midjourney", 
                "sdxl-turbo"
            ]
        }
        
        msg = "<emoji document_id=5877260593903177342>⚙️</emoji> <b>Доступные модели ИИ:</b>\n\n"
        
        for category, models in available_models.items():
            msg += f"<emoji document_id=5325547803936572038>✨</emoji> <b>{category}:</b>\n"
            for model in models:
                msg += f"  • <code>{model}</code>\n"
            msg += "\n"
        
        msg += "<b>Как изменить модель:</b>\n"
        msg += "• Для изменения модели Gemini используйте <code>.config SunshineGPTEnhanced gemini_model_name модель</code>\n"
        msg += "• Для изменения модели OpenAI используйте <code>.config SunshineGPTEnhanced openai_model_name модель</code>\n"
        msg += "• Для изменения модели DeepSeek используйте <code>.config SunshineGPTEnhanced deepseek_model_name модель</code>\n"
        msg += "• Для изменения модели генерации изображений используйте <code>.config SunshineGPTEnhanced default_image_model модель</code>\n"
        
        await utils.answer(message, msg)

    @loader.command()
    async def ahelp(self, message):
        """— показать помощь по модулю"""
        reply = "<emoji document_id=5325547803936572038>✨</emoji> <b>SunshineGPT Enhanced</b>\n\n"
        reply += "<b>Основные команды:</b>\n"
        reply += "• <code>.ai</code> или <code>.gpt</code> - отправить запрос к AI модели по умолчанию\n"
        reply += "• <code>.gemini</code> - отправить запрос к Google Gemini\n"
        reply += "• <code>.cgpt</code> - отправить запрос к ChatGPT (OpenAI)\n"
        reply += "• <code>.dseek</code> - отправить запрос к DeepSeek AI\n"
        reply += "• <code>.gimg</code> - сгенерировать изображение\n"
        reply += "• <code>.ghist</code> - анализ истории чата (можно использовать с ответом на сообщение пользователя)\n"
        reply += "• <code>.amodels</code> - показать список доступных моделей AI\n\n"
        
        reply += "<b>Настройка модуля:</b>\n"
        reply += "• API ключи для всех моделей можно установить через <code>.config SunshineGPTEnhanced</code>\n"
        reply += "• Модель по умолчанию: <code>.config SunshineGPTEnhanced default_ai модель</code> (gemini, openai, deepseek)\n"
        reply += "• Системная инструкция: <code>.config SunshineGPTEnhanced {модель}_system_instruction текст</code>\n\n"
        
        reply += "<b>Использование с медиа:</b>\n"
        reply += "• Ответьте на изображение, видео, GIF, стикер или голосовое сообщение с командой\n"
        reply += "• Если не указан запрос, будет использован запрос «Опиши это»\n\n"
        
        reply += "<b>Генерация изображений:</b>\n"
        reply += "• <code>.gimg ваш промпт</code> - генерирует изображение по текстовому описанию\n"
        reply += "• Модель для генерации: <code>.config SunshineGPTEnhanced default_image_model модель</code>\n\n"
        
        reply += "<b>Версия:</b> 1.4.8.8"
        
        await utils.answer(message, reply)
