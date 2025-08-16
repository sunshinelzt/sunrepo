__version__ = (1, 0, 0, 0)

# meta developer: @sunshinelzt
# scope: heroku_only
# scope: heroku_min 1.7.0

import re
from telethon import events
from collections import defaultdict
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl, MessageMediaWebPage
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from telethon.tl.functions.channels import LeaveChannelRequest
from google.generativeai import GenerativeModel, configure
from telethon.tl.types import Message
from telethon import TelegramClient
from urlextract import URLExtract
import asyncio
import random
import json

from .. import loader, utils

class Passworder:
    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model_name = model_name
        self.model = None
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
        }

        self.prompt = """
        Твоя единственная задача — извлечь или вычислить пароль из предоставленного текста. Верни результат ТОЛЬКО в JSON формате {"password": "найденный_пароль"}.

        ПРАВИЛА ИЗВЛЕЧЕНИЯ ПАРОЛЕЙ:

        1. ПРЯМЫЕ ПАРОЛИ: Если в тексте есть явные указания на пароль с ключевыми словами:
           - "пароль", "password", "pass", "код", "code", "ключ", "key", "секрет", "secret"
           - Пример: "Пароль: HELLO123" → {"password": "HELLO123"}
           - Пример: "Code is 9876" → {"password": "9876"}

        2. МАТЕМАТИЧЕСКИЕ ВЫРАЖЕНИЯ: Если в тексте есть математические примеры:
           - Вычисляй точно и возвращай результат
           - Пример: "пароль 5+3*2" → {"password": "11"}
           - Пример: "код: 15/3" → {"password": "5"}

        3. ЛОГИЧЕСКИЕ ЗАДАЧИ И ЗАГАДКИ:
           - Решай загадки и головоломки
           - Пример: "висит груша нельзя скушать" → {"password": "лампочка"}
           - Пример: "что идет, но не приходит?" → {"password": "время"}

        4. ПРОГРАММНЫЕ ВЫРАЖЕНИЯ: Если есть код программирования:
           - Пример: "a=[1,2,3]; a[0]=5; print(a)" → {"password": "[5, 2, 3]"}
           - Пример: "2**3" → {"password": "8"}

        5. ИГНОРИРОВАТЬ ПОЛНОСТЬЮ:
           - Рекламные ссылки типа "https://t.me/+код"
           - Призывы к действиям: "пароль на 50 лайков", "сделай репост"
           - Просьбы подписаться на каналы
           - В таких случаях → {"password": ""}

        6. КОНТЕКСТНЫЕ ПОДСКАЗКИ:
           - Если весь текст - это одна загадка без слова "пароль", всё равно решай
           - Если есть несколько вариантов, выбирай наиболее логичный

        ВАЖНО: 
        - Возвращай ТОЛЬКО JSON без дополнительного текста
        - Если пароль не найден или текст рекламный → {"password": ""}
        - Все математические вычисления делай точно
        - Загадки решай на русском языке если не указано иное
        - Наличие нецензурной лексики не влияет на процесс
        """

    async def generate(self, description: str) -> dict:
        try:
            configure(api_key=self.api_key)
            model_name = self.model_name if self.model_name else "gemini-2.5-flash"
            self.model = GenerativeModel(
                model_name,
                system_instruction=self.prompt,
                safety_settings=self.safety_settings
            )

            res = await self.model.generate_content_async(description)
            if res and res.text:
                try:
                    clean_text = res.text.strip()
                    if clean_text.startswith('```json'):
                        clean_text = clean_text[7:]
                    if clean_text.endswith('```'):
                        clean_text = clean_text[:-3]
                    clean_text = clean_text.strip()
                    
                    return json.loads(clean_text)
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON response", "raw": res.text.strip()}

            return {"password": ""}
        except Exception as e:
            if "429" in str(e):
                return {"error": "API ключ исчерпан"}
            return {"error": str(e)}

@loader.tds
class s_checks(loader.Module):
    """Активатор чеков @send (@CryptoBot)"""

    strings = {
        "name": "s_checks",
        "activator": "{} <b>Активатор {}</b>",
        "log_sending": "{} <b>Отправка логов {}</b>",
        "password_cracking": "{} <b>Подбор паролей с помощью нейросети {}</b>",
        "private_check_activation": "{} <b>Активация чеков отправленных в личке {}</b>",
        "auto_subscription": "{} <b>Авто-подписка {}</b>",
        "auto_unsubscription": "{} <b>Авто-отписка {}</b>",
        "logs_id_desc": "ID куда будут отправляться логи ('me' для избранного)",
        "logs_enabled_desc": "отправка логов",
        "delay_desc": "задержка в секундах перед активацией чека",
        "track_private_desc": "активация чеков отправленных в личке",
        "ai_passwords_desc": "подбор паролей с помощью Gemini AI",
        "watcher_on_desc": "состояние активатора",
        "subscribe_desc": "подписываться ли на каналы чтобы активировать чеки которые этого требуют",
        "unsubscribe_desc": "отписываться ли от каналов после активации чека",
        "no_track_users_desc": "чьи чеки не активировать (юзер указывать обязательно без @)",
        "blocked_chats_desc": "ID чатов/каналов где чеки НЕ будут активироваться",
        "gemini_api_key_desc": "API ключ для Gemini AI (aistudio.google.com/apikey)",
        "gemini_model_name_desc": "модель для Gemini AI. Доступные: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-2.0-flash, gemini-1.5-flash",
        "check_found": "Обнаружен новый чек",
        "check_link": "Ссылка чека:",
        "found_in_private": "Обнаружен в личке:",
        "found_in_chat": "Обнаружен в чате:",
        "message_link": "Ссылка на сообщение:",
        "api_key_missing": "<b>API ключ не указан. Получить можно тут: aistudio.google.com/apikey (бесплатно), затем укажи в конфиге</b>",
        "password_error": "<b>Ошибка генерации пароля:</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "logs_id",
                "me",
                doc=lambda: self.strings("logs_id_desc"),
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "logs_enabled",
                True,
                doc=lambda: self.strings("logs_enabled_desc"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "delay",
                0,
                doc=lambda: self.strings("delay_desc"),
                validator=loader.validators.Integer(minimum=0),
            ),
            loader.ConfigValue(
                "track_private",
                True,
                doc=lambda: self.strings("track_private_desc"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "ai_passwords",
                False,
                doc=lambda: self.strings("ai_passwords_desc"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "watcher_on",
                True,
                doc=lambda: self.strings("watcher_on_desc"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "subscribe",
                True,
                doc=lambda: self.strings("subscribe_desc"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "unsubscribe",
                True,
                doc=lambda: self.strings("unsubscribe_desc"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "no_track_users",
                ["username"],
                doc=lambda: self.strings("no_track_users_desc"),
                validator=loader.validators.Series(
                    loader.validators.Union(loader.validators.String(), loader.validators.Integer())
                ),
            ),
            loader.ConfigValue(
                "blocked_chats",
                [],
                doc=lambda: self.strings("blocked_chats_desc"),
                validator=loader.validators.Series(loader.validators.Integer()),
            ),
            loader.ConfigValue(
                "gemini_api_key",
                "",
                doc=lambda: self.strings("gemini_api_key_desc"),
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "gemini_model_name",
                "gemini-2.5-flash",
                doc=lambda: self.strings("gemini_model_name_desc"),
                validator=loader.validators.String(),
            ),
        )
        self.sent_codes = defaultdict(bool)
        self._emojis = {
            "butterfly": [
                "<emoji document_id=5931703809800672260>🦋</emoji>",
                "<emoji document_id=5931685899787049183>🦋</emoji>",
                "<emoji document_id=5931254745200072637>🦋</emoji>",
                "<emoji document_id=5931420135800706406>🦋</emoji>",
                "<emoji document_id=5931579221389350286>🦋</emoji>",
                "<emoji document_id=5931796606864070138>🦋</emoji>",
                "<emoji document_id=5931709595121620710>🦋</emoji>",
                "<emoji document_id=5931689305696113988>🦋</emoji>"
            ],
            "cherry": [
                "<emoji document_id=5931246400078616786>🍑</emoji>",
                "<emoji document_id=5931283302437623922>🍑</emoji>",
                "<emoji document_id=5933573709712331850>🍑</emoji>",
                "<emoji document_id=5931412164341404834>🍑</emoji>",
                "<emoji document_id=5931408105597310922>🍑</emoji>",
                "<emoji document_id=5931347907335689957>🍑</emoji>",
                "<emoji document_id=5933527787922005080>🍑</emoji>",
                "<emoji document_id=5931255728747583490>🍑</emoji>"
            ],
            "lock": [
                "<emoji document_id=5931715028255249602>🔐</emoji>",
                "<emoji document_id=5931759476871797208>🔐</emoji>",
                "<emoji document_id=5931604879523976952>🔐</emoji>",
                "<emoji document_id=5931569115331306831>🔐</emoji>",
                "<emoji document_id=5931530997496551899>🔐</emoji>",
                "<emoji document_id=5931464008891635480>🔐</emoji>",
                "<emoji document_id=5931781312485529416>🔐</emoji>",
                "<emoji document_id=5931434210408536378>🔐</emoji>"
            ],
            "repeat": [
                "<emoji document_id=5931534008268625877>🔁</emoji>",
                "<emoji document_id=5933704920963225481>🔁</emoji>",
                "<emoji document_id=5931351192985671828>🔁</emoji>",
                "<emoji document_id=5931570287857374798>🔁</emoji>",
                "<emoji document_id=5931284676827158390>🔁</emoji>",
                "<emoji document_id=5931776850014508762>🔁</emoji>",
                "<emoji document_id=5931430675650451345>🔁</emoji>",
                "<emoji document_id=5931768827015602073>🔁</emoji>"
            ],
            "bulb": [
                "<emoji document_id=5931461638069687926>💡</emoji>",
                "<emoji document_id=5931599476455118181>💡</emoji>",
                "<emoji document_id=5931620642053953532>💡</emoji>",
                "<emoji document_id=5931776927323920236>💡</emoji>",
                "<emoji document_id=5931773113392962977>💡</emoji>",
                "<emoji document_id=5931673221043590661>💡</emoji>",
                "<emoji document_id=5931462436933604912>💡</emoji>",
                "<emoji document_id=5931295409950431661>💡</emoji>"
            ],
            "check": [
                "<emoji document_id=5931279570111043408>✅</emoji>",
                "<emoji document_id=5931602010485823634>✅</emoji>",
                "<emoji document_id=5931642602221737965>✅</emoji>",
                "<emoji document_id=5933944919440758085>✅</emoji>",
                "<emoji document_id=5933523918156469650>✅</emoji>",
                "<emoji document_id=5931644148409964015>✅</emoji>",
                "<emoji document_id=5931387421034812889>✅</emoji>",
                "<emoji document_id=5931344333922900261>✅</emoji>"
            ]
        }
        self._module_loaded = False
        self._handlers = []

    async def client_ready(self):
        """Инициализация модуля"""
        self._module_loaded = True
        self.me = await self._client.get_me()
        self.me_id = self.me.id
        self.cd_id = 1559501630
        self.extractor = URLExtract()
        
        handlers_config = [
            (self.cb_handler, [events.NewMessage, events.MessageEdited]),
            (self.channels_handler, [events.NewMessage, events.MessageEdited]),
            (self.passwords_handler, [events.NewMessage, events.MessageEdited]),
        ]

        for handler_func, event_list in handlers_config:
            for event_type in event_list:
                handler = self._client.add_event_handler(handler_func, event_type)
                self._handlers.append(handler)

        if self.config["gemini_api_key"]:
            self.passworder = Passworder(self.config["gemini_api_key"], self.config["gemini_model_name"])
        else:
            self.passworder = None
    
    async def on_unload(self):
        """Выгрузка модуля"""
        self._module_loaded = False
        
        if hasattr(self, '_handlers') and self._handlers:
            for handler in self._handlers:
                try:
                    self._client.remove_event_handler(handler)
                except Exception:
                    pass
            self._handlers.clear()
        
        if hasattr(self, 'sent_codes'):
            self.sent_codes.clear()
        
        if hasattr(self, 'passworder'):
            self.passworder = None
        
        for attr in ['me', 'me_id', 'cd_id', 'extractor']:
            if hasattr(self, attr):
                delattr(self, attr)

    async def get_codes(self, text, entities, markup):
        """Оптимизированное извлечение кодов чеков"""
        if not text and not markup:
            return []
            
        urls_in_message = set()
        finded_codes = set()

        url_pattern = r'https?://t\.me/(?:send|CryptoBot)\?start=([A-Za-z0-9_-]+)'

        if entities:
            for entity in entities:
                if isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl)):
                    if isinstance(entity, MessageEntityUrl):
                        urls_in_text = self.extractor.find_urls(text)
                        urls_in_message.update(url.strip() for url in urls_in_text)
                    elif isinstance(entity, MessageEntityTextUrl):
                        urls_in_message.add(entity.url.strip())

        if markup and hasattr(markup, 'rows'):
            for button_row in markup.rows:
                for button in button_row.buttons:
                    if hasattr(button, "url") and button.url:
                        urls_in_message.add(button.url.strip())

        for found_url in urls_in_message:
            if not found_url.startswith(('http://', 'https://')):
                found_url = 'https://' + found_url.strip()

            clean_url = re.sub(r'[^\w:/?&=.-]', '', found_url)
            code_match = re.match(url_pattern, clean_url)
            if code_match:
                code = code_match.group(1)
                if code.startswith('CQ'):
                    finded_codes.add(code)

        return list(finded_codes)

    async def generate_password(self, description):
        """Генерация пароля через AI"""
        if not self.config["gemini_api_key"]:
            await self.log(f"<emoji document_id=5274099962655816924>❗️</emoji> {self.strings['api_key_missing']}")
            return None

        if not self.passworder:
            return None

        try:
            result = await self.passworder.generate(description)
        except Exception as e:
            await self.log(f"{self.strings['password_error']} <code>{utils.escape_html(str(e))}</code>")
            return None

        if "error" in result:
            await self.log(f"{self.strings['password_error']} <code>{utils.escape_html(result['error'])}</code>")
            return None

        return result.get("password") if result.get("password") else None

    async def cb_handler(self, message):
        """Основной обработчик чеков"""
        if not getattr(self, '_module_loaded', False):
            return
            
        if not self.config["watcher_on"]:
            return

        if not message or message.sender_id in [self.me_id, self.cd_id]:
            return

        try:
            if not self.config["track_private"] and message.is_private:
                return

            if message.chat_id in self.config["blocked_chats"]:
                return

            if message.sender:
                sender_username = getattr(message.sender, 'username', None)
                if sender_username and sender_username in self.config["no_track_users"]:
                    return

            codes = await self.get_codes(message.text, message.entities, message.reply_markup)

            if codes:
                for code in codes:
                    if not self.sent_codes[code]:
                        await message.mark_read()
                        if self.config["delay"] > 0:
                            await asyncio.sleep(int(self.config["delay"]))
                        
                        await self._client.send_message(self.cd_id, f"/start {code}")
                        self.sent_codes[code] = True
                        await self.send_log_message(message, code)

        except Exception:
            pass

    async def channels_handler(self, event):
        """Обработчик подписок на каналы"""
        if not getattr(self, '_module_loaded', False):
            return
            
        if not all([self.config["subscribe"], self.config["watcher_on"]]):
            return

        if event.sender_id != self.cd_id:
            return

        subscribe_phrases = [
            'Чтобы активировать этот чек, подпишитесь на канал',
            'To activate this check, join the channel(s)'
        ]

        if not any(event.text.startswith(prefix) for prefix in subscribe_phrases):
            return

        subscribed = []
        try:
            if event.reply_markup and hasattr(event.reply_markup, 'rows'):
                for row in event.reply_markup.rows:
                    for button in row.buttons:
                        if button.url and '+' in button.url:
                            invite_code = button.url.split('+', 1)[1]
                            await self._client(ImportChatInviteRequest(invite_code))
                            subscribed.append(invite_code)

            await asyncio.sleep(1)
            await event.click(data=b'check-subscribe')

            if self.config["unsubscribe"] and subscribed:
                await asyncio.sleep(1)
                for invite_code in subscribed:
                    try:
                        channel_info = await self._client(CheckChatInviteRequest(hash=invite_code))
                        if hasattr(channel_info, 'chat'):
                            await self._client(LeaveChannelRequest(channel_info.chat))
                    except Exception:
                        continue

        except Exception:
            pass

    async def passwords_handler(self, message):
        """Обработчик паролей через ИИ"""
        if not getattr(self, '_module_loaded', False):
            return
            
        if not all([self.config["watcher_on"], self.config["ai_passwords"]]):
            return

        if message.sender_id != self.cd_id:
            return

        password_phrases = [
            "Введите пароль от чека для получения",
            "Enter the password for this check to receive"
        ]

        if not any(phrase in message.text for phrase in password_phrases):
            return

        lines = message.raw_text.split("\n")
        if len(lines) >= 3:
            description = "\n".join(lines[2:]).strip()
            password = await self.generate_password(description)
            if password:
                await self._client.send_message(self.cd_id, password)

    async def log(self, message):
        """Отправка логов"""
        if not self.config["logs_enabled"]:
            return

        logs_id = self.config["logs_id"]
        if logs_id == "me":
            await self._client.send_message("me", message, link_preview=False)
        else:
            try:
                await self._client.send_message(logs_id, message, link_preview=False)
            except Exception:
                await self._client.send_message("me", message, link_preview=False)

    async def send_log_message(self, message, code):
        """Отправка информации о найденном чеке"""
        if not self.config["logs_enabled"]:
            return

        try:
            log_parts = [
                f"<emoji document_id=5843553939672274145>⚡️</emoji> <b>{self.strings['check_found']}</b>",
                "",
                f"<emoji document_id=5870527201874546272>🔗</emoji> <b>{self.strings['check_link']}</b> <code>t.me/send?start={code}</code>"
            ]

            if message.is_private:
                sender_username = getattr(message.sender, 'username', None) if message.sender else None
                if sender_username:
                    log_parts.append(f"<emoji document_id=5879770735999717115>👤</emoji> <b>{self.strings['found_in_private']}</b> @{sender_username}")
            else:
                chat_title = getattr(message.chat, 'title', 'Неизвестный чат')
                chat_username = getattr(message.chat, 'username', None)
                
                if chat_username:
                    log_parts.append(f"<emoji document_id=5879770735999717115>💬</emoji> <b>{self.strings['found_in_chat']}</b> <code>@{chat_username}</code>")
                else:
                    log_parts.append(f"<emoji document_id=5879770735999717115>💬</emoji> <b>{self.strings['found_in_chat']}</b> <code>{chat_title}</code>")
                
                if hasattr(message, 'id'):
                    chat_id = str(message.chat_id).replace('-100', '')
                    message_link = f"t.me/c/{chat_id}/{message.id}"
                    log_parts.append(f"<emoji document_id=5870527201874546272>🔗</emoji> <b>{self.strings['message_link']}</b> {message_link}")

            await self.log("\n".join(log_parts))

        except Exception:
            await self.log(f"<emoji document_id=5843553939672274145>⚡️</emoji> Чек активирован: {code}")

    def _get_random_emoji(self, emoji_type):
        """Получение случайного эмодзи"""
        return random.choice(self._emojis.get(emoji_type, ["🔥"]))


    @loader.command()
    async def checkscmd(self, message: Message):
        """Вкл/выкл активатор чеков"""
        self.config["watcher_on"] = not self.config["watcher_on"]
        
        status = "включен" if self.config["watcher_on"] else "выключен"
        emoji = self._get_random_emoji("butterfly")
        
        await utils.answer(message, self.strings["activator"].format(emoji, status))

    @loader.command()
    async def slogscmd(self, message: Message):
        """Вкл/выкл отправку логов"""
        self.config["logs_enabled"] = not self.config["logs_enabled"]
        
        status = "включена" if self.config["logs_enabled"] else "выключена"
        emoji = self._get_random_emoji("cherry")
        
        await utils.answer(message, self.strings["log_sending"].format(emoji, status))

    @loader.command()
    async def passwordscmd(self, message: Message):
        """Вкл/выкл подбор паролей с помощью нейросети"""
        self.config["ai_passwords"] = not self.config["ai_passwords"]
        
        status = "включен" if self.config["ai_passwords"] else "выключен"
        emoji = self._get_random_emoji("lock")
        
        await utils.answer(message, self.strings["password_cracking"].format(emoji, status))

    @loader.command()
    async def sglscmd(self, message: Message):
        """Вкл/выкл активацию чеков в личных сообщениях"""
        self.config["track_private"] = not self.config["track_private"]
        
        status = "включена" if self.config["track_private"] else "выключена"
        emoji = self._get_random_emoji("repeat")
        
        await utils.answer(message, self.strings["private_check_activation"].format(emoji, status))

    @loader.command()
    async def subscribecmd(self, message: Message):
        """Вкл/выкл авто-подписку"""
        self.config["subscribe"] = not self.config["subscribe"]
        
        status = "включена" if self.config["subscribe"] else "выключена"
        emoji = self._get_random_emoji("bulb")
        
        await utils.answer(message, self.strings["auto_subscription"].format(emoji, status))

    @loader.command()
    async def unsubscribecmd(self, message: Message):
        """Вкл/выкл авто-отписку"""
        self.config["unsubscribe"] = not self.config["unsubscribe"]
        
        status = "включена" if self.config["unsubscribe"] else "выключена"
        emoji = self._get_random_emoji("check")
        
        await utils.answer(message, self.strings["auto_unsubscription"].format(emoji, status))