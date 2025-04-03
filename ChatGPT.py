__version__ = (1, 1, 0)

# пися
# meta developer: @sunshinelzt

# ██████╗██╗  ██╗ █████╗ ████████╗ ██████╗ ██████╗ ████████╗
#██╔════╝██║  ██║██╔══██╗╚══██╔══╝██╔════╝ ██╔══██╗╚══██╔══╝
#██║     ███████║███████║   ██║   ██║  ███╗██████╔╝   ██║   
#██║     ██╔══██║██╔══██║   ██║   ██║   ██║██╔═══╝    ██║   
#╚██████╗██║  ██║██║  ██║   ██║   ╚██████╔╝██║        ██║   
# ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝        ╚═╝   

import os
import time
import json
import asyncio
import random
from typing import List, Dict, Any, Optional, Union
import logging
from PIL import Image
from .. import loader, utils
import aiohttp


logger = logging.getLogger(__name__)


@loader.tds
class ChatGPTMod(loader.Module):
    """Модуль для общения с ChatGPT"""

    strings = {
        "name": "ChatGPT",
        "no_api_key": "<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Получите его на platform.openai.com</b>",
        "no_prompt": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Введите запрос или ответьте на сообщение</b>",
        "processing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>{}</b>",
        "request_sent": "<emoji document_id=5325547803936572038>✨</emoji> <b>Запрос отправлен, ожидайте ответ...</b>",
        "error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка:</b> {}",
        "server_error": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка сервера:</b> {}",
        "empty_response": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ответ пустой.</b>",
        "empty_media": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Не удалось открыть изображение:</b> {}",
        "empty_content": "<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка: Запрос должен содержать текст или медиа.</b>",
        "collecting_history": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю сообщений для {}...</b>",
        "collecting_chat": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Собираю историю чата...</b>",
        "user_analysis_title": "<emoji document_id=5873121512445187130>❓</emoji> <b>Что сегодня обсуждал {}?</b>",
        "chat_analysis_title": "<emoji document_id=5873121512445187130>❓</emoji> <b>Что сегодня обсуждали участники чата?</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key", 
                "", 
                "API ключ для OpenAI (platform.openai.com)", 
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "model_name", 
                "gpt-4o", 
                "Модель ChatGPT. Примеры: gpt-4o, gpt-4-turbo, gpt-3.5-turbo", 
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "system_instruction", 
                "Ты - полезный помощник. Отвечай кратко и по делу.", 
                "Системная инструкция для ChatGPT", 
                validator=loader.validators.String()
            ),
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
                "max_tokens", 
                1000, 
                "Максимальное количество токенов в ответе", 
                validator=loader.validators.Integer(minimum=50, maximum=4096)
            ),
            loader.ConfigValue(
                "temperature", 
                0.7, 
                "Температура генерации (от 0 до 1)", 
                validator=loader.validators.Float(minimum=0, maximum=1)
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
        ]
        self.conversation_history = {}  # Для хранения историй диалогов

    async def client_ready(self, client, db):
        """Инициализация клиента"""
        self.client = client
        self.db = db
        
        if self.config["proxy"]:
            os.environ["HTTP_PROXY"] = self.config["proxy"]
            os.environ["HTTPS_PROXY"] = self.config["proxy"]
            logger.info(f"Proxy set to {self.config['proxy']}")

    async def _get_random_emoji(self) -> str:
        """Возвращает случайный эмодзи из списка"""
        return random.choice(self.emojis)

    async def _process_media(self, message) -> Optional[str]:
        """Обрабатывает медиа в сообщении и возвращает описание"""
        if not message:
            return None

        try:
            if getattr(message, "photo", None):
                media_path = await message.download_media()
                try:
                    # Для определения, что это изображение
                    img = Image.open(media_path)
                    return "[Изображение]"
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    return None
                finally:
                    if media_path and os.path.exists(media_path):
                        try:
                            os.remove(media_path)
                        except:
                            pass
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
                return f"[Документ: {message.document.attributes[0].file_name if message.document.attributes else 'без имени'}]"
        except Exception as e:
            logger.error(f"Error processing media: {e}")
            return None

        return None

    async def _call_chatgpt_api(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Вызов API ChatGPT по новой документации"""
        if not self.config["api_key"]:
            raise ValueError("API ключ не указан")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['api_key']}",
            "OpenAI-Beta": "assistants=v1"  # Актуальный заголовок для API v1
        }

        data = {
            "model": self.config["model_name"],
            "messages": messages,
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
        }

        http_proxy = self.config["proxy"] if self.config["proxy"] else None
        conn = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.config["timeout"])

        for attempt in range(self.config["max_retries"]):
            try:
                async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",  # Актуальный эндпоинт
                        headers=headers,
                        json=data,
                        proxy=http_proxy
                    ) as response:
                        response_text = await response.text()
                        
                        try:
                            response_json = json.loads(response_text)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode JSON response: {response_text}")
                            raise Exception(f"Некорректный ответ от API: {response_text[:100]}...")
                        
                        if response.status == 200:
                            # В соответствии с новой документацией
                            if "choices" in response_json and len(response_json["choices"]) > 0:
                                if "message" in response_json["choices"][0]:
                                    return response_json["choices"][0]["message"]["content"].strip()
                                else:
                                    logger.error(f"Unexpected response format: {response_json}")
                                    raise Exception("Неожиданный формат ответа от API")
                            else:
                                logger.error(f"No choices in response: {response_json}")
                                raise Exception("Пустой ответ от API")
                        elif response.status == 429:
                            # Обработка ограничения скорости
                            wait_time = 2 ** attempt
                            logger.warning(f"Rate limited, retrying in {wait_time}s (attempt {attempt+1}/{self.config['max_retries']})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            # Обработка ошибок
                            error_message = "Неизвестная ошибка"
                            if "error" in response_json:
                                if isinstance(response_json["error"], dict):
                                    error_message = response_json["error"].get("message", f"HTTP {response.status}")
                                else:
                                    error_message = str(response_json["error"])
                            logger.error(f"API error: {response.status} - {error_message}")
                            raise Exception(f"Ошибка API: {error_message}")
            except asyncio.TimeoutError:
                logger.error(f"Request timeout (attempt {attempt+1}/{self.config['max_retries']})")
                if attempt == self.config["max_retries"] - 1:
                    raise Exception("Таймаут запроса к API")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.exception(f"Error calling API: {str(e)}")
                if attempt == self.config["max_retries"] - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise Exception("Превышено максимальное количество попыток")

    @loader.command(ru_doc="- отправить запрос к ChatGPT")
    async def gpts(self, message):
        """- отправить запрос к ChatGPT"""
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        prompt = utils.get_args_raw(message)
        show_question = True
        chat_id = str(message.chat_id)

        try:
            # Обработка ответа на сообщение
            if message.is_reply:
                reply = await message.get_reply_message()
                media_description = await self._process_media(reply)
                
                if media_description:
                    if not prompt:
                        prompt = f"Опиши это {media_description}"
                        show_question = False
                else:
                    prompt = prompt or reply.text

            if not prompt:
                await utils.answer(message, self.strings["no_prompt"])
                return

            await utils.answer(message, self.strings["request_sent"])

            # Инициализация или получение истории чата
            if chat_id not in self.conversation_history:
                self.conversation_history[chat_id] = []
                # Добавляем системное сообщение в начало истории
                if self.config["system_instruction"]:
                    self.conversation_history[chat_id].append({
                        "role": "system",
                        "content": self.config["system_instruction"]
                    })

            # Добавление сообщения пользователя в историю
            self.conversation_history[chat_id].append({
                "role": "user",
                "content": prompt
            })

            # Отправка запроса к API
            response = await self._call_chatgpt_api(self.conversation_history[chat_id])

            if not response:
                await utils.answer(message, self.strings["empty_response"])
                return

            # Добавление ответа в историю
            self.conversation_history[chat_id].append({
                "role": "assistant",
                "content": response
            })

            # Ограничение истории для экономии памяти (оставляем системное сообщение + последние N сообщений)
            max_history_items = 10  # Количество пар вопрос-ответ
            if len(self.conversation_history[chat_id]) > max_history_items * 2 + 1:
                # Сохраняем системное сообщение если оно есть
                system_message = None
                if self.conversation_history[chat_id][0]["role"] == "system":
                    system_message = self.conversation_history[chat_id][0]
                    self.conversation_history[chat_id] = self.conversation_history[chat_id][-(max_history_items*2):]
                    self.conversation_history[chat_id].insert(0, system_message)
                else:
                    self.conversation_history[chat_id] = self.conversation_history[chat_id][-(max_history_items*2):]

            random_emoji = await self._get_random_emoji()
            
            if show_question:
                result = f"<emoji document_id=5443038326535759644>💬</emoji> <b>Вопрос:</b> {prompt}\n\n<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ ChatGPT:</b>\n{response} {random_emoji}"
            else:
                result = f"<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ ChatGPT:</b>\n{response} {random_emoji}"
            
            await utils.answer(message, result)
            
        except Exception as e:
            logger.exception(f"Error in gpt command: {e}")
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(ru_doc="- очистить историю диалога в текущем чате")
    async def gptclear(self, message):
        """- очистить историю диалога в текущем чате"""
        chat_id = str(message.chat_id)
        
        if chat_id in self.conversation_history:
            # Сохраняем системное сообщение если оно есть
            if self.conversation_history[chat_id] and self.conversation_history[chat_id][0]["role"] == "system":
                system_message = self.conversation_history[chat_id][0]
                self.conversation_history[chat_id] = [system_message]
            else:
                self.conversation_history[chat_id] = []
                
            await utils.answer(message, "<emoji document_id=5325547803936572038>✨</emoji> <b>История диалога очищена!</b>")
        else:
            await utils.answer(message, "<emoji document_id=5325547803936572038>✨</emoji> <b>История диалога уже пуста.</b>")

    @loader.command(ru_doc="- анализ последних сообщений чата")
    async def gptanal(self, message):
        """- анализ последних сообщений чата"""
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
            
            total_collected = 0
            async for msg in self.client.iter_messages(chat_id, limit=history_limit):
                if msg and msg.sender and not getattr(msg.sender, "bot", False) and not msg.action:
                    sender_name = msg.sender.first_name if hasattr(msg.sender, "first_name") else "Unknown"
                    sender_username = msg.sender.username if hasattr(msg.sender, "username") else None
                    
                    if user and sender_username != user:
                        continue
                        
                    msg_text = msg.text if msg.text else ""
                    
                    # Добавляем информацию о медиа
                    if not msg_text:
                        media_description = await self._process_media(msg)
                        if media_description:
                            msg_text = media_description
                    
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
                context += "его интересах, вопросах, общем настроении. Выдели основные темы обсуждения. В конце напиши шутку про то что ты прочитал и запиши как Шутка от ИИ."
                title = self.strings["user_analysis_title"].format(user_name)
            else:
                context += "Проанализируй все сообщения и составь краткую сводку о том, что обсуждалось в чате сегодня. "
                context += "Выдели основные темы обсуждения, активных участников, общее настроение беседы. В конце напиши шутку про то что ты прочитал и запиши как Шутка от ИИ."
                title = self.strings["chat_analysis_title"]
                
            history_text = "\n".join([f"[{msg['time']}] {msg['sender']}: {msg['text']}" for msg in all_messages])
            
            prompt = f"{context}\n\nИстория сообщений:\n{history_text}"
            
            processing_msg = await utils.answer(
                message, 
                self.strings["processing"].format("Анализирую сообщения...")
            )
            
            # Отправляем запрос к API (без сохранения в историю беседы)
            messages = [
                {"role": "system", "content": "Ты - аналитик чатов. Твоя задача - анализировать сообщения и выявлять закономерности."},
                {"role": "user", "content": prompt}
            ]
            
            analysis = await self._call_chatgpt_api(messages)
            
            random_emoji = await self._get_random_emoji()
            result = f"{title}\n\n{analysis} {random_emoji}"
            
            await utils.answer(processing_msg, result)
            
        except Exception as e:
            logger.exception(f"Error in gptanal: {e}")
            await utils.answer(message, self.strings["error"].format(e))
