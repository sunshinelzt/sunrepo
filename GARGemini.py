# meta developer: @sunshinelzt

# @sunshinelzt
# Licensed under GNU AGPLv3
# https://www.gnu.org/licenses/agpl-3.0.html

import aiohttp
import asyncio
import logging
import json
import re
from datetime import datetime
from .. import loader, utils

logger = logging.getLogger(__name__)

# Эмоджи
EMOJI_ROBOT = "<emoji document_id=5931415565955503486>🤖</emoji>"
EMOJI_STOP = "<emoji document_id=5877413297170419326>🚫</emoji>"
EMOJI_WARNING = "<emoji document_id=5775887550262546277>❗️</emoji>"
EMOJI_INFO = "<emoji document_id=5877597667231534929>🗒</emoji>"
EMOJI_STATUS = "<emoji document_id=5931472654660800739>📊</emoji>"
EMOJI_CLEAR = "<emoji document_id=5879896690210639947>🗑</emoji>"
EMOJI_CHANGE = "<emoji document_id=6005843436479975944>🔁</emoji>"
EMOJI_TEMP = "<emoji document_id=5879585266426973039>🌐</emoji>"
EMOJI_TOKENS = "<emoji document_id=5877260593903177342>⚙</emoji>"
EMOJI_CHECK = "<emoji document_id=5776375003280838798>✅</emoji>"
EMOJI_CROSS = "<emoji document_id=5778527486270770928>❌</emoji>"

@loader.tds
class GlobalAutoReplyGeminiMod(loader.Module):
    """AI автоответчик с памятью для всех личных чатов и готовыми конфигурациями (Gemini API)"""
    strings = {
        "name": "GARGemini",
        "_cfg_doc_api_key": "API ключ для Gemini API (обязательно)",
        "_cfg_doc_api_url": "URL API для запросов к Gemini (не меняйте без необходимости)",
        "_cfg_doc_default_model": "Используемая модель Gemini (gemini-1.5-flash/pro/pro-latest/ultra-latest)",
        "_cfg_doc_temperature": "Температура генерации (от 0.0 до 1.0, 0 - более предсказуемо, 1 - более креативно)",
        "_cfg_doc_max_tokens": "Максимальное количество токенов в ответе",
        "_cfg_doc_max_history": "Максимальное количество сообщений в истории чата",
        "_cfg_doc_prompt_1": "Конфигурация 1",
        "_cfg_doc_prompt_2": "Конфигурация 2",
        "_cfg_doc_prompt_3": "Конфигурация 3",
        "_cfg_doc_prompt_4": "Конфигурация 4",
        "_cfg_doc_prompt_5": "Конфигурация 5",
        "_cfg_doc_logging": "Включить логирование запросов/ответов (может занимать место в логах)",
        "_cfg_doc_typing": "Включить 'печатает...' во время генерации ответа", 
        "_cfg_doc_retry_count": "Количество попыток при ошибке API",
        "_cfg_doc_emoji_enabled": "Включить эмоджи в ответах",
        
        # Сообщения
        "activated": f"<b>{EMOJI_ROBOT} Автоответчик Gemini активирован</b>\nМодель: <code>{{model}}</code>\nИнструкция: <i>{{instruction}}</i>",
        "deactivated": f"<b>{EMOJI_STOP} Автоответчик Gemini выключен</b>",
        "no_instruction": f"<b>{EMOJI_WARNING} Укажите инструкцию для автоответчика или номер конфигурации</b>",
        "unknown_config": f"<b>{EMOJI_WARNING} Неизвестная конфигурация</b>\nДоступные конфигурации: 1-5",
        "api_error": f"<b>{EMOJI_WARNING} Ошибка API:</b> {{}}",
        "no_api_key": f"<b>{EMOJI_WARNING} API ключ Gemini не установлен</b>\n\nПолучите ключ на https://aistudio.google.com/app/apikey\nУстановите через: <code>.config GARGemini</code>",
        "model_info": f"<b>{EMOJI_INFO} Информация о моделях Gemini:</b>\n\n<b>gemini-1.5-flash</b> - Быстрая и эффективная модель для повседневных задач\n<b>gemini-1.5-pro</b> - Продвинутая модель с глубоким пониманием контекста\n<b>gemini-1.5-pro-latest</b> - Последняя версия Pro с улучшениями\n<b>gemini-ultra-latest</b> - Наиболее мощная модель Gemini\n\n<b>Текущая модель:</b> <code>{{model}}</code>",
        "status": f"<b>{EMOJI_STATUS} Статус автоответчика Gemini:</b>\n\n<b>Активен:</b> {{}}\n<b>Модель:</b> <code>{{}}</code>\n<b>Температура:</b> {{}}\n<b>Макс. токенов:</b> {{}}\n<b>Макс. история:</b> {{}} сообщений\n<b>Активных чатов:</b> {{}}",
        "history_cleared": f"<b>{EMOJI_CLEAR} История чатов очищена</b>",
        "model_changed": f"<b>{EMOJI_CHANGE} Модель изменена на:</b> <code>{{}}</code>",
        "temp_changed": f"<b>{EMOJI_TEMP} Температура изменена на:</b> {{}}",
        "tokens_changed": f"<b>{EMOJI_TOKENS} Максимум токенов изменен на:</b> {{}}"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                doc=lambda: self.strings["_cfg_doc_api_key"]
            ),
            loader.ConfigValue(
                "api_url",
                "https://generativelanguage.googleapis.com/v1beta/models",
                doc=lambda: self.strings["_cfg_doc_api_url"]
            ),
            loader.ConfigValue(
                "default_model",
                "gemini-1.5-pro-latest",
                doc=lambda: self.strings["_cfg_doc_default_model"]
            ),
            loader.ConfigValue(
                "temperature",
                0.7,
                doc=lambda: self.strings["_cfg_doc_temperature"]
            ),
            loader.ConfigValue(
                "max_tokens",
                1024,
                doc=lambda: self.strings["_cfg_doc_max_tokens"]
            ),
            loader.ConfigValue(
                "max_history",
                200,
                doc=lambda: self.strings["_cfg_doc_max_history"]
            ),
            loader.ConfigValue(
                "prompt_1",
                "Общайся за меня, не проявляй излишней вежливости и милости. Признавай, что ты автоответчик.",
                doc=lambda: self.strings["_cfg_doc_prompt_1"]
            ),
            loader.ConfigValue(
                "prompt_2",
                "Отвечай на все вопросы нейтрально и сухо, без эмоций. Признавай, что ты автоответчик.",
                doc=lambda: self.strings["_cfg_doc_prompt_2"]
            ),
            loader.ConfigValue(
                "prompt_3",
                "Будь дружелюбным и позитивным в общении. Признавай, что ты автоответчик.",
                doc=lambda: self.strings["_cfg_doc_prompt_3"]
            ),
            loader.ConfigValue(
                "prompt_4",
                "Отвечай кратко и по делу, избегай лишних слов. Признавай, что ты автоответчик.",
                doc=lambda: self.strings["_cfg_doc_prompt_4"]
            ),
            loader.ConfigValue(
                "prompt_5",
                "Общайся в неформальном стиле, можешь использовать сленг и шутки. Признавай, что ты автоответчик.",
                doc=lambda: self.strings["_cfg_doc_prompt_5"]
            ),
            loader.ConfigValue(
                "logging",
                False,
                doc=lambda: self.strings["_cfg_doc_logging"]
            ),
            loader.ConfigValue(
                "typing",
                True,
                doc=lambda: self.strings["_cfg_doc_typing"]
            ),
            loader.ConfigValue(
                "retry_count",
                3,
                doc=lambda: self.strings["_cfg_doc_retry_count"]
            ),
            loader.ConfigValue(
                "emoji_enabled",
                True,
                doc=lambda: self.strings["_cfg_doc_emoji_enabled"]
            ),
        )
        self.auto_reply_active = False  # Состояние автоответчика
        self.global_instruction = None  # Глобальная инструкция для всех чатов
        self.chat_memory = {}  # Словарь для хранения памяти чатов
        self.processing_chats = set()  # Множество чатов, для которых идет обработка

    async def client_ready(self, client, db):
        """Инициализация при загрузке модуля"""
        self.client = client
        self.db = db
        
        # Загрузка состояния из БД
        stored_data = self.db.get(self.strings["name"], {})
        self.auto_reply_active = stored_data.get("auto_reply_active", False)
        self.global_instruction = stored_data.get("global_instruction", None)
        self.chat_memory = stored_data.get("chat_memory", {})
        
        logger.info(f"GlobalAutoReplyGemini загружен: активен = {self.auto_reply_active}")

    def _save_db(self):
        """Сохранение состояния в БД"""
        self.db.set(self.strings["name"], {
            "auto_reply_active": self.auto_reply_active,
            "global_instruction": self.global_instruction,
            "chat_memory": self.chat_memory
        })
    
    def _limit_history(self, chat_id):
        """Ограничение количества сообщений в истории чата"""
        if chat_id in self.chat_memory and len(self.chat_memory[chat_id]) > self.config["max_history"]:
            self.chat_memory[chat_id] = self.chat_memory[chat_id][-self.config["max_history"]:]

    @loader.unrestricted
    async def lsbotcmd(self, message):
        """Включает автоответчик с инструкцией или готовой конфигурацией
        
        Использование: 
        .lsbot <инструкция>
        .lsbot конфиг <номер>
        """
        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return
            
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, self.strings["no_instruction"])
            return
        
        instruction = args
        
        # Обработка команды с конфигом
        if args.startswith("конфиг"):
            config_parts = args.split(maxsplit=1)
            config_id = config_parts[1] if len(config_parts) > 1 else None
            
            if config_id and config_id in ["1", "2", "3", "4", "5"]:
                instruction = getattr(self.config, f"prompt_{config_id}")
            else:
                await utils.answer(message, self.strings["unknown_config"])
                return
        
        # Активация автоответчика
        self.auto_reply_active = True
        self.global_instruction = instruction
        self._save_db()
        
        await utils.answer(
            message, 
            self.strings["activated"].format(
                model=self.config["default_model"],
                instruction=instruction
            )
        )
    
    @loader.unrestricted
    async def offmonitoringcmd(self, message):
        """Выключает автоответчик для всех чатов"""
        self.auto_reply_active = False
        self._save_db()
        
        await utils.answer(message, self.strings["deactivated"])
    
    @loader.unrestricted
    async def geminimodelscmd(self, message):
        """Показывает информацию о доступных моделях Gemini"""
        await utils.answer(
            message,
            self.strings["model_info"].format(model=self.config["default_model"])
        )
    
    @loader.unrestricted
    async def geministatuscmd(self, message):
        """Показывает текущий статус автоответчика Gemini"""
        active_chats = len(self.chat_memory.keys())
        
        await utils.answer(
            message,
            self.strings["status"].format(
                EMOJI_CHECK if self.auto_reply_active else EMOJI_CROSS,
                self.config["default_model"],
                self.config["temperature"],
                self.config["max_tokens"],
                self.config["max_history"],
                active_chats
            )
        )
    
    @loader.unrestricted
    async def geminisetchatcmd(self, message):
        """Очищает историю всех чатов"""
        self.chat_memory = {}
        self._save_db()
        await utils.answer(message, self.strings["history_cleared"])
    
    @loader.unrestricted
    async def geminimodelcmd(self, message):
        """Изменяет используемую модель Gemini
        
        Использование:
        .geminimodel <название_модели>
        
        Например: .geminimodel gemini-1.5-pro
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["model_info"].format(model=self.config["default_model"]))
            return
            
        if not re.match(r"^gemini-[\w\.\-]+$", args):
            await utils.answer(message, self.strings["model_info"].format(model=self.config["default_model"]))
            return
            
        self.config["default_model"] = args
        await utils.answer(message, self.strings["model_changed"].format(args))

    async def format_gemini_messages(self, chat_id):
        """Форматирует историю сообщений для Gemini API"""
        # Преобразуем историю в формат для Gemini
        formatted_messages = []
        
        # Системный промпт и инструкция
        system_content = "Ты — автоответчик для личных чатов, являешься модулем юзер бота Heroku в телеграм, и ты пишешь от аккаунта реального человека. Твоя задача — отвечать на сообщения людей в рамках заданной инструкции. Не используй Latex или особое форматирование. Не давай личной информации и не оскорбляй. Ты не можешь управлять графиком или планировать встречи."
        
        if self.global_instruction:
            system_content += f"\n\nИнструкция: {self.global_instruction}"
        
        formatted_messages.append({
            "role": "user",
            "parts": [{"text": system_content}]
        })
        
        formatted_messages.append({
            "role": "model",
            "parts": [{"text": "Понял, я буду действовать как автоответчик в соответствии с инструкцией."}]
        })
        
        # Добавляем историю сообщений
        if chat_id in self.chat_memory:
            for msg in self.chat_memory[chat_id]:
                role = "user" if msg["role"] == "user" else "model"
                formatted_messages.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
        
        return formatted_messages

    async def generate_gemini_response(self, chat_id, user_message):
        """Генерирует ответ от Gemini API"""
        if chat_id not in self.chat_memory:
            self.chat_memory[chat_id] = []
            
        # Добавляем сообщение пользователя в историю
        self.chat_memory[chat_id].append({"role": "user", "content": user_message})
        self._limit_history(chat_id)
        self._save_db()
        
        # Форматируем сообщения для API
        formatted_messages = await self.format_gemini_messages(chat_id)
        
        # Формируем запрос к API
        model = self.config["default_model"]
        api_url = f"{self.config['api_url']}/{model}:generateContent?key={self.config['api_key']}"
        
        payload = {
            "contents": formatted_messages,
            "generationConfig": {
                "temperature": self.config["temperature"],
                "maxOutputTokens": self.config["max_tokens"],
                "topP": 0.95,
                "topK": 40
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
        }
        
        retry_count = self.config["retry_count"]
        response_text = ""
        
        while retry_count > 0:
            try:
                if self.config["logging"]:
                    logger.info(f"Отправка запроса к Gemini API: {api_url}")
                    
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            if self.config["logging"]:
                                logger.error(f"Ошибка API: {error_text}")
                            retry_count -= 1
                            continue
                            
                        response_json = await response.json()
                        
                        if self.config["logging"]:
                            logger.info(f"Ответ Gemini API: {json.dumps(response_json, ensure_ascii=False)}")
                        
                        # Извлекаем текст из ответа
                        try:
                            response_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
                        except (KeyError, IndexError) as e:
                            if self.config["logging"]:
                                logger.error(f"Ошибка при извлечении текста: {e}")
                            retry_count -= 1
                            continue
                            
                        # Добавляем ответ в историю
                        self.chat_memory[chat_id].append({"role": "assistant", "content": response_text})
                        self._limit_history(chat_id)
                        self._save_db()
                        
                        return response_text
                        
            except Exception as e:
                if self.config["logging"]:
                    logger.error(f"Исключение при запросе к API: {e}")
                retry_count -= 1
                
            # Небольшая задержка перед повторной попыткой
            await asyncio.sleep(1)
        
        # Если все попытки исчерпаны, возвращаем ошибку
        return f"{EMOJI_WARNING} Ошибка при генерации ответа. Пожалуйста, попробуйте позже."

    async def watcher(self, message):
        """Автоматически отвечает на сообщения в личных чатах, если автоответчик активен"""
        if not isinstance(message, message.__class__):
            return
        
        # Проверки на условия работы автоответчика
        if not self.auto_reply_active:  # Автоответчик выключен
            return
            
        if not message.is_private:  # Только личные чаты
            return
            
        if message.sender_id == self.client.uid:  # Игнорируем свои сообщения
            return
            
        if message.sender and message.sender.bot:  # Игнорируем ботов
            return
            
        if not message.text:  # Только текстовые сообщения
            return
            
        if message.text.startswith("."):  # Игнорируем команды
            return
            
        chat_id = message.chat_id
        
        # Проверяем, не обрабатывается ли уже этот чат
        if chat_id in self.processing_chats:
            return
            
        self.processing_chats.add(chat_id)
        
        try:
            user_message = message.text
            
            # Включаем "печатает..." если настроено
            if self.config["typing"]:
                async with self.client.action(message.chat_id, 'typing'):
                    response = await self.generate_gemini_response(chat_id, user_message)
                    await message.reply(response)
            else:
                response = await self.generate_gemini_response(chat_id, user_message)
                await message.reply(response)
                
        except Exception as e:
            logger.error(f"Ошибка в watcher: {e}")
            if self.config["logging"]:
                await message.reply(self.strings["api_error"].format(str(e)))
        finally:
            # Удаляем чат из списка обрабатываемых
            self.processing_chats.discard(chat_id)
