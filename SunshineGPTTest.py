__version__ = (1, 5, 0, 0)

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
from typing import Tuple, Optional, Dict, Any, List, Union
import logging
from contextlib import suppress
from PIL import Image
from .. import loader, utils
import aiohttp


logger = logging.getLogger(__name__)


@loader.tds
class SunshineGPT(loader.Module):
    """Улучшенный модуль для общения с Gemini AI и генерации изображений"""

    strings = {
        "name": "SunshineGPT",
        "no_api_key": "<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Получите его на aistudio.google.com/apikey</b>",
        "no_prompt": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Введите запрос или ответьте на сообщение (изображение, видео, GIF, стикер, голосовое)</b>",
        "processing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>{}</b>",
        "request_sent": "<emoji document_id=5325547803936572038>✨</emoji> <b>Запрос отправлен, ожидайте ответ...</b>",
        "generating_image": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Сервер генерирует картинку, пожалуйста, подождите...</b>",
        "describe_this": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Опиши это...</b>",
        "error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка:</b> {}",
        "server_error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка сервера:</b> {}",
        "empty_response": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ответ пустой.</b>",
        "no_image_prompt": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Пожалуйста, укажите описание для генерации изображения.</b>",
        "image_caption": "<blockquote><emoji document_id=5465143921912846619>💭</emoji> <b>Промт:</b> <code>{prompt}</code></blockquote>\n"
                         "<blockquote><emoji document_id=5877260593903177342>⚙️</emoji> <b>Модель:</b> <code>{model}</code></blockquote>\n"
                         "<blockquote><emoji document_id=5199457120428249992>🕘</emoji> <b>Время генерации:</b> {time} сек.</blockquote>",
        "collecting_history": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю сообщений для {}...</b>",
        "collecting_chat": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю чата...</b>",
        "user_analysis_title": "<b>Что сегодня обсуждал {}?</b>",
        "chat_analysis_title": "<b>Что сегодня обсуждали участники чата?</b>",
        "empty_media": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Не удалось открыть изображение:</b> {}",
        "empty_content": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка: Запрос должен содержать текст или медиа.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key", 
                "", 
                "API ключ для Gemini AI (aistudio.google.com/apikey)", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "api_key_image", 
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", 
                "Это не трогай!", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "model_name", 
                "gemini-1.5-flash", 
                "Модель для Gemini AI. Примеры: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp, gemini-2.0-flash-thinking-exp-1219", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "system_instruction", 
                "", 
                "Инструкция для Gemini AI", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "proxy", 
                "", 
                "Прокси в формате http://<user>:<pass>@<proxy>:<port>, или http://<proxy>:<port>", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "default_image_model", 
                "flux", 
                "Модель для генерации изображений. Примеры: sdxl-turbo, flux, flux-pro, flux-dev, flux-schnell, dall-e-3, midjourney", 
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
            "<emoji document_id=5447482135923406987>🌺</emoji>",
            "<emoji document_id=5447118373668274107>😈</emoji>",
            "<emoji document_id=5447504955084652371>⚰️</emoji>",
            "<emoji document_id=5449461939753204225>🤩</emoji>",
            "<emoji document_id=5449918091049844581>🆒</emoji>",
            "<emoji document_id=5449356850493406098>❄️</emoji>",
            "<emoji document_id=5447103766484499962>😂</emoji>",
            "<emoji document_id=5382065579232347995>🙄</emoji>",
            "<emoji document_id=5382255777564083766>😒</emoji>",
            "<emoji document_id=5382160888851615895>😄</emoji>",
            "<emoji document_id=5382243558382144304>👆</emoji>",
            "<emoji document_id=5381982145197654105>😨</emoji>",
            "<emoji document_id=5262687736334139937>🤐</emoji>",
            "<emoji document_id=5265154593750271127>😊</emoji>",
            "<emoji document_id=5265180513877903121>😕</emoji>",
            "<emoji document_id=5292183561678375848>😁</emoji>",
            "<emoji document_id=5292092972228169457>😧</emoji>",
            "<emoji document_id=5294439768128508029>☺️</emoji>",
            "<emoji document_id=5291813515886089464>🎩</emoji>",
            "<emoji document_id=5294269446905416769>😎</emoji>",
            "<emoji document_id=5278474666019665313>🌟</emoji>",
            "<emoji document_id=5278273197693743570>🌟</emoji>",
            "<emoji document_id=5278340607205453195>🌟</emoji>",
            "<emoji document_id=5319299223521338293>😱</emoji>",
            "<emoji document_id=5319055531371930585>🙅‍♂️</emoji>",
            "<emoji document_id=5319016550248751722>👋</emoji>",
            "<emoji document_id=5318773107207447403>😱</emoji>",
            "<emoji document_id=5319018096436977294>🔫</emoji>",
            "<emoji document_id=5319116781900538765>😣</emoji>",
            "<emoji document_id=5229159576649093081>❤️</emoji>",
            "<emoji document_id=5456439526442409796>👍</emoji>",
            "<emoji document_id=5458837140395793861>👎</emoji>",
            "<emoji document_id=5456307778320603813>😏</emoji>"
        ]

    async def client_ready(self, client, db):
        """Инициализация клиента"""
        self.client = client
        self.db = db
        
        # Настройка прокси если указан
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
        except AttributeError as e:
            logger.error(f"Error getting mime type: {e}")
            return None

        return None

    async def _setup_genai(self) -> None:
        """Настраивает Gemini API с заданным ключом"""
        if not self.config["api_key"]:
            raise ValueError("API ключ не указан")
        
        genai.configure(api_key=self.config["api_key"])

    async def _get_random_emoji(self) -> str:
        """Возвращает случайный эмодзи из списка"""
        return random.choice(self.emojis)

    async def generate_image(self, prompt: str) -> Tuple[Optional[str], Union[float, str]]:
        """Генерация изображения с API"""
        start_time = time.time()

        payload = {
            "model": self.config["default_image_model"],
            "prompt": prompt,
            "response_format": "url"
        }

        # Настройка HTTP-клиента с учетом прокси
        http_proxy = self.config["proxy"] if self.config["proxy"] else None
        conn = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.config["timeout"])
        
        headers = {
            "Authorization": f"Bearer {self.config['api_key_image']}", 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
            "Content-Type": "application/json"
        }

        # Система повторных попыток с экспоненциальной задержкой
        for attempt in range(self.config["max_retries"]):
            try:
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
                        elif response.status == 429:
                            # Rate limit - ждем и пробуем снова
                            wait_time = 2 ** attempt  # Экспоненциальная задержка
                            logger.warning(f"Rate limited, retrying in {wait_time}s (attempt {attempt+1}/{self.config['max_retries']})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_msg = f"Ошибка сервера: {response.status}"
                            logger.error(f"Server error: {response.status} - {await response.text()}")
                            return None, error_msg
            except asyncio.TimeoutError:
                logger.error(f"Request timeout (attempt {attempt+1}/{self.config['max_retries']})")
                if attempt == self.config["max_retries"] - 1:
                    return None, "Таймаут запроса к серверу"
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.exception(f"Error generating image: {str(e)}")
                return None, f"Ошибка: {str(e)}"

        return None, "Превышено максимальное количество попыток"

    async def _process_gemini_query(self, content_parts, model_name=None) -> str:
        """Обрабатывает запрос к Gemini API с повторными попытками"""
        if not model_name:
            model_name = self.config["model_name"]
            
        await self._setup_genai()
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self.config["system_instruction"] or None,
        )

        for attempt in range(self.config["max_retries"]):
            try:
                response = model.generate_content(content_parts)
                return response.text.strip() if response.text else self.strings["empty_response"]
            except Exception as e:
                logger.error(f"Gemini API error (attempt {attempt+1}): {str(e)}")
                if attempt == self.config["max_retries"] - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка

    @loader.command()
    async def gptcmd(self, message):
        """— отправить запрос к Gemini"""
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

            reply_text = await self._process_gemini_query(content_parts)
            random_emoji = await self._get_random_emoji()

            if show_question and prompt != "Опиши это":
                response = f"<emoji document_id=5443038326535759644>💬</emoji> <b>Вопрос:</b> {prompt}\n<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini:</b> {reply_text} {random_emoji}"
            else:
                response = f"<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini:</b> {reply_text} {random_emoji}"
            
            await utils.answer(message, response)
            
        except Exception as e:
            logger.exception(f"Error in gptcmd: {e}")
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
            # Конфигурация HTTP-клиента для загрузки изображения
            timeout = aiohttp.ClientTimeout(total=30)
            conn = aiohttp.TCPConnector(ssl=False)
            
            try:
                async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
                    async with session.get(image_url) as img_response:
                        if img_response.status != 200:
                            await utils.answer(message, self.strings["error"].format(f"Не удалось загрузить изображение (код: {img_response.status})"))
                            return
                            
                        img_content = io.BytesIO(await img_response.read())
                        img_content.name = "generated_image.png"

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
        """– анализ последних сообщений чата"""
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        user = None
        user_name = ""
        history_limit = self.config["history_limit"]
        
        if message.is_reply:
            reply = await message.get_reply_message()
            user = reply.sender.username if reply.sender else None
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
            
            # Собираем сообщения партиями по 100
            total_collected = 0
            async for msg in self.client.iter_messages(chat_id, limit=history_limit):
                # Пропускаем сообщения бота и служебные сообщения
                if msg and msg.sender and not getattr(msg.sender, "bot", False) and not msg.action:
                    # Сохраняем только текст сообщения, имя отправителя и дату
                    sender_name = msg.sender.first_name if hasattr(msg.sender, "first_name") else "Unknown"
                    sender_username = msg.sender.username if hasattr(msg.sender, "username") else None
                    
                    # Проверяем, ищем ли мы сообщения конкретного пользователя
                    if user and sender_username != user:
                        continue
                        
                    # Получаем текст сообщения или обозначение медиа
                    msg_text = msg.text if msg.text else ""
                    if not msg_text and msg.media:
                        msg_text = "[медиа]"
                    
                    # Формируем запись о сообщении
                    message_data = {
                        "sender": sender_name,
                        "time": msg.date.strftime("%H:%M:%S"),
                        "text": msg_text
                    }
                    
                    all_messages.append(message_data)
                    total_collected += 1
                    
                # Если достигли лимита или проанализировали достаточно сообщений
                if total_collected >= history_limit:
                    break
            
            if not all_messages:
                await utils.answer(message, self.strings["error"].format("Не найдено подходящих сообщений"))
                return
                
            # Сортируем сообщения по времени (от старых к новым)
            all_messages.sort(key=lambda x: x["time"])
            
            # Создаем запрос для Gemini API
            context = "Ниже представлена история сообщений из чата. "
            if user:
                context += f"Проанализируй все сообщения пользователя {user_name} и составь краткую сводку о чем он писал сегодня, "
                context += "его интересах, вопросах, общем настроении. Выдели основные темы обсуждения. В конце напиши шутку про то что ты прочитал и запиши как Шутка от ИИ."
                title = self.strings["user_analysis_title"].format(user_name)
            else:
                context += "Проанализируй все сообщения и составь краткую сводку о том, что обсуждалось в чате сегодня. "
                context += "Выдели основные темы обсуждения, активных участников, общее настроение беседы. В конце напиши шутку про то что ты прочитал и запиши как Шутка от ИИ."
                title = self.strings["chat_analysis_title"]
                
            # Форматируем историю сообщений для запроса
            history_text = "\n".join([f"[{msg['time']}] {msg['sender']}: {msg['text']}" for msg in all_messages])
            
            # Формируем полный запрос
            prompt = f"{context}\n\nИстория сообщений:\n{history_text}"
            
            # Показываем статус обработки
            processing_msg = await utils.answer(
                message, 
                self.strings["processing"].format("Анализирую сообщения...")
            )
            
            # Выполняем запрос к API
            content_parts = [genai.protos.Part(text=prompt)]
            analysis = await self._process_gemini_query(content_parts)
            
            # Форматируем и отправляем результат
            random_emoji = await self._get_random_emoji()
            result = f"{title}\n\n{analysis} {random_emoji}"
            
            await utils.answer(processing_msg, result)
            
        except Exception as e:
            logger.exception(f"Error in ghist: {e}")
            await utils.answer(message, self.strings["error"].format(e))
