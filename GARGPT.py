# meta developer: @sunshinelzt

# @sunshinelzt
# Licensed under GNU AGPLv3
# https://www.gnu.org/licenses/agpl-3.0.html

import aiohttp
import asyncio
import logging
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class GlobalAutoReplyGPTMod(loader.Module):
    """AI автоответчик с памятью для всех личных чатов и готовыми конфигурациями в настройках"""
    strings = {
        "name": "GARGPT",
        "_cfg_doc_api_url": "URL API для запросов к ИИ",
        "_cfg_doc_default_model": "Используемая модель ИИ",
        "_cfg_doc_prompt_1": "Конфигурация 1",
        "_cfg_doc_prompt_2": "Конфигурация 2",
        "_cfg_doc_prompt_3": "Конфигурация 3",
        "_cfg_doc_prompt_4": "Конфигурация 4",
        "_cfg_doc_prompt_5": "Конфигурация 5",
        
        # Сообщения
        "activated": "<b>🤖 Автоответчик активирован</b>\nИнструкция: <i>{}</i>",
        "deactivated": "<b>🚫 Автоответчик выключен</b>",
        "no_instruction": "<b>⚠️ Укажите инструкцию для автоответчика или номер конфигурации</b>",
        "unknown_config": "<b>⚠️ Неизвестная конфигурация</b>\nДоступные конфигурации: 1-5",
        "api_error": "<b>⚠️ Ошибка API:</b> {}"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_url",
                "http://api.onlysq.ru/ai/v2",
                doc=lambda: self.strings["_cfg_doc_api_url"]
            ),
            loader.ConfigValue(
                "default_model",
                "gpt-4o-mini",
                doc=lambda: self.strings["_cfg_doc_default_model"]
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
            )
        )
        self.auto_reply_active = False  # Состояние автоответчика
        self.global_instruction = None  # Глобальная инструкция для всех чатов
        self.chat_memory = {}  # Словарь для хранения памяти чатов

    async def client_ready(self, client, db):
        """Инициализация при загрузке модуля"""
        self.client = client
        self.db = db
        
        # Загрузка состояния из БД
        stored_data = self.db.get(self.strings["name"], {})
        self.auto_reply_active = stored_data.get("auto_reply_active", False)
        self.global_instruction = stored_data.get("global_instruction", None)
        self.chat_memory = stored_data.get("chat_memory", {})
        
        logger.info(f"GlobalAutoReplyGPT загружен: активен = {self.auto_reply_active}")

    def _save_db(self):
        """Сохранение состояния в БД"""
        self.db.set(self.strings["name"], {
            "auto_reply_active": self.auto_reply_active,
            "global_instruction": self.global_instruction,
            "chat_memory": self.chat_memory
        })

    @loader.unrestricted
    async def lsbotcmd(self, message):
        """Включает автоответчик с инструкцией или готовой конфигурацией
        
        Использование: 
        .lsbot <инструкция>
        .lsbot конфиг <номер>
        """
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
        
        await utils.answer(message, self.strings["activated"].format(instruction))
    
    @loader.unrestricted
    async def offmonitoringcmd(self, message):
        """Выключает автоответчик для всех чатов"""
        self.auto_reply_active = False
        self._save_db()
        
        await utils.answer(message, self.strings["deactivated"])

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
            
        if message.text and message.text.startswith("."):  # Игнорируем команды
            return
            
        # Обработка сообщения
        user_message = message.text
        chat_id = message.chat_id
        
        # Инициализируем память для чата, если её ещё нет
        if chat_id not in self.chat_memory:
            self.chat_memory[chat_id] = []
        
        # Добавляем текущее сообщение в историю
        self.chat_memory[chat_id].append({"role": "user", "content": user_message})
        
        # Ограничиваем количество сообщений в истории (200 последних)
        history = self.chat_memory[chat_id]
        if len(history) > 200:
            history = history[-200:]
            self.chat_memory[chat_id] = history
            
        # Сохраняем в БД обновленную историю
        self._save_db()
            
        # Формируем запрос к API
        api_url = self.config["api_url"]
        payload = {
            "model": self.config["default_model"],
            "request": {
                "messages": [
                    {"role": "system", "content": "Ты — автоответчик для личных чатов, являешься модулем юзер бота Hikka в телеграм, и ты пишешь от аккаунта реального человека. Твоя задача — отвечать на сообщения людей в рамках заданной инструкции. Не используй Latex или особое форматирование. Не давай личной информации, и не оскорбляй себя. Твоя память запоминает 200 последних сообщений. Не планируй встречи и дела. Ты не можешь управлять графиком владельца юзер бота."},
                    {"role": "system", "content": f"Инструкция: {self.global_instruction}."}
                ] + history
            }
        }
        
        try:
            # Делаем запрос к API
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload) as response:
                    response.raise_for_status()
                    response_json = await response.json()
                    
                    # Получаем ответ от ассистента
                    reply_text = response_json.get("answer", "Ответ не получен.")
                    
                    # Отправляем ответ
                    await message.reply(reply_text)
                    
                    # Обновляем историю после ответа
                    self.chat_memory[chat_id].append({"role": "assistant", "content": reply_text})
                    self._save_db()
                    
        except Exception as e:
            logger.error(f"Ошибка при запросе к API: {e}")
            await message.reply(self.strings["api_error"].format(str(e)))
