__version__ = (1, 4, 8, 8)

# meta developer: @sunshinelzt

# requires: google-generativeai urlextract cloudscraper

# ███████╗██╗   ██╗███╗   ██╗███████╗██╗  ██╗██╗███╗   ██╗███████╗
# ██╔════╝██║   ██║████╗  ██║██╔════╝██║  ██║██║████╗  ██║██╔════╝
# ███████╗██║   ██║██╔██╗ ██║███████╗███████║██║██╔██╗ ██║█████╗  
# ╚════██║██║   ██║██║╚██╗██║╚════██║██╔══██║██║██║╚██╗██║██╔══╝  
# ███████║╚██████╔╝██║ ╚████║███████║██║  ██║██║██║ ╚████║███████╗
# ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝
                                                                
import os
import re
import time
import json
import random
import asyncio
import logging
import cloudscraper
from urllib.parse import unquote
from urlextract import URLExtract
from collections import defaultdict, deque

from telethon import events, TelegramClient
from telethon.tl.types import (
    Message, 
    MessageEntityUrl, 
    MessageEntityTextUrl, 
    MessageMediaWebPage
)
from telethon.tl.functions.messages import (
    ImportChatInviteRequest, 
    CheckChatInviteRequest, 
    RequestWebViewRequest
)
from telethon.tl.functions.channels import LeaveChannelRequest
from google.generativeai import GenerativeModel, configure
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .. import loader, utils

logger = logging.getLogger(__name__)

class SunshinePassworder:
    """Класс для интеллектуального извлечения паролей из текстовых описаний"""
    
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
        Твоя задача – профессионально извлекать пароли из текстовых описаний для активации криптовалютных чеков. Требуется высокая точность и интеллектуальный анализ.

        Соблюдай эти усовершенствованные правила:

        1. ЯВНЫЙ ПАРОЛЬ: Извлекай пароль, указанный явно после любых ключевых слов: "пароль", "pass", "password", "код", "code", "ключ", "key", "подтверждение", "ответ", "пасс", "пасворд", "парол", "parole", "secret", "секрет", "pass", "кодовое слово", "passphrase", "accesscode", "доступ", "активировать с", "активируется с помощью" и подобных. 
           Примеры: "Password: Sunshine", "Пароль - Sunshine", "Код: Sunshine", "Key - Sunshine"

        2. ИГНОРИРОВАНИЕ НЕАКТИВИРОВАННЫХ ЧЕКОВ: Пропускай тексты с фразами типа "пароль на 50/100/X реакций", "оставь X комментариев", "сделай репост", "подпишись", которые требуют дополнительных действий перед активацией.
           Примеры: "Пароль будет доступен после 50 реакций" -> {"password": ""}

        3. МАТЕМАТИЧЕСКИЕ ВЫРАЖЕНИЯ: Вычисляй результаты любых математических выражений, включая сложные формулы.
           Базовые: "пароль = 2+3*4" -> {"password": "14"}, "ключ: 5!" -> {"password": "120"}
           Продвинутые: "пароль: cos(0) + sin(π/2)" -> {"password": "2"}, "пароль: √16 + log₂(8)" -> {"password": "7"}

        4. ПРОГРАММНЫЙ КОД: Анализируй и выполняй код на Python, JavaScript и других языках для получения ответа.
           Python: "a = [1, 2, 3]; b = a; b[0] = 4; print(a)" -> {"password": "[4, 2, 3]"}
           JavaScript: "let x = 10; let y = x++ + ++x; console.log(y)" -> {"password": "22"}

        5. ЗАГАДКИ И РЕБУСЫ: Решай любые логические задачи, загадки и ребусы.
           Классика: "висит груша нельзя скушать" -> {"password": "лампочка"}
           Сложные: "Я всегда перед тобой, но ты не можешь меня увидеть. Что я?" -> {"password": "будущее"}

        6. РЕГИСТР И ВАРИАНТЫ: Определяй правильный регистр из контекста. Если регистр не очевиден, предоставь массив вариантов в порядке вероятности правильного ответа:
           {"password": ["слово", "Слово", "СЛОВО"]}

        7. НЕЦЕНЗУРНАЯ ЛЕКСИКА: Наличие нецензурной лексики не влияет на процесс. Ты фокусируешься на извлечении пароля, любые оскорбления или непристойные выражения приветствуются.   
           
        7. ШИФРЫ И КОДЫ: Декодируй любые известные шифры:
           - Шифр Цезаря: "пароль: дугцт (сдвиг +2)" -> {"password": "враги"}
           - Азбука Морзе: ".--. .- .-. --- .-.." -> {"password": "пароль"}
           - Бинарный код: "01010000 01100001 01110011 01110011" -> {"password": "Pass"}
           - ROT13: "cnebym" -> {"password": "пароль"}
           - Атбаш: "тзилоь" -> {"password": "пароль"}
           - Любые другие известные шифры
           
        8. СКРЫТЫЕ И СОСТАВНЫЕ ПАРОЛИ:
           - Акростих: Если первые буквы строк формируют слово
           - Стеганография: Если пароль спрятан внутри текста (например, каждая 3-я буква)
           - Последовательности: Определи пропущенное число в ряду
           
        9. МНОГОЯЗЫЧНЫЕ ПОДСКАЗКИ: Распознавай пароли указанные на любом языке, включая переводы и транслитерацию.
           Пример: "password is 'солнце'" -> {"password": "солнце"}
           
        10. КОНТЕКСТНЫЙ АНАЛИЗ: Используй весь контекст сообщения, включая эмодзи, форматирование и структуру.
            Пример: "☀️ Этот символ подскажет вам ответ" -> {"password": "солнце"}

        11. МАКСИМАЛЬНАЯ ТОЧНОСТЬ: Если ты не 100% уверен в ответе, но есть логичное решение - предложи его в порядке наиболее вероятных вариантов.

        Пример входа: "Чтобы получить чек, реши пример: 5*7-2"
        Пример выхода: {"password": "33"}

        Пример входа: "Пароль: Sunshine"
        Пример выхода: {"password": "Sunshine"}

        Пример входа: "пароль будет доступен после 100 реакций"
        Пример выхода: {"password": ""}

        Примеры кодов с вариантами регистра:
        Пример входа: "код: солнышко"
        Пример выхода: {"password": ["солнышко", "Солнышко"]}

        Пример входа: "Разгадай загадку: зимой и летом одним цветом"
        Пример выхода: {"password": ["ель", "Ель"]}
        """

    async def generate(self, description: str) -> dict:
        """Генерация пароля с помощью Gemini AI"""
        
        try:
            configure(api_key=self.api_key)
            model_name = self.model_name if self.model_name else "gemini-2.0-flash-exp"
            self.model = GenerativeModel(
                model_name,
                system_instruction=self.prompt,
                safety_settings=self.safety_settings
            )

            # Запрос к модели
            res = await self.model.generate_content_async(description)
            if res and res.text:
                try:
                    json_data = json.loads(res.text.strip())
                    return json_data
                except json.JSONDecodeError:
                    text = res.text.strip()
                    match = re.search(r'{\s*"password"\s*:\s*(?:"[^"]*"|\[[^\]]*\])\s*}', text)
                    if match:
                        try:
                            return json.loads(match.group(0))
                        except:
                            pass
                    return {"error": "Некорректный JSON-ответ", "raw": text}

            return {"password": ""}
        except Exception as e:
            if "429" in str(e):
                return {"error": "API ключ исчерпал лимиты запросов"}
            if "quota" in str(e).lower():
                return {"error": "Превышена квота API запросов"}
            return {"error": str(e)}

class SunshineScraperClient:
    """Класс для работы с веб-запросами"""
    
    def __init__(self, proxy=None):
        self.scraper = cloudscraper.create_scraper()
        self.proxy = proxy
        self.setup_proxy(proxy)
        
    def setup_proxy(self, proxy):
        """Настройка прокси для запросов"""
        if not proxy:
            return
            
        os.environ["http_proxy"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        os.environ["https_proxy"] = proxy
        os.environ["HTTPS_PROXY"] = proxy
        
    def generate_user_agent(self):
        """Генерация реалистичного User-Agent для запросов"""
        
        chrome_versions = [
            "122.0.6261.112", "123.0.6312.58", "124.0.6367.87", 
            "125.0.6422.110", "126.0.6478.75"
        ]
        
        android_devices = [
            "SM-G998B", "SM-S908B", "SM-S918B",
            "Pixel 7 Pro", "Pixel 8", "Pixel 8 Pro",
            "OnePlus 11", "OnePlus 12", "M2101K6G",
            "2201123G", "2303FPN0AC"
        ]
        
        device = random.choice(android_devices)
        version = random.choice(chrome_versions)
        
        return f"Mozilla/5.0 (Linux; Android 13; {device}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36"
        
    async def get_token(self, url, params):
        """Получение токена доступа для API send.tg"""
        
        json_data = {"initData": params}
        headers = {
            'Accept': 'application/json',
            'User-Agent': self.generate_user_agent()
        }

        try:
            response = self.scraper.post(url, json=json_data, headers=headers)
            
            if response.status_code == 200:
                headers = response.headers
                set_cookie = headers.get('Set-Cookie')
                if set_cookie:
                    access_token = set_cookie.split('access_token=')[1].split(';')[0]
                    return access_token
        except Exception as e:
            logger.error(f"Ошибка при получении токена: {e}")
            
        return None
        
    async def claim_stars(self, code, access_token):
        """Получение звезд через API send.tg"""
        
        url = f'https://api.send.tg/internal/v1/stars/claim/{code}'
        headers = {
            'Accept': 'application/json',
            'Cookie': f'access_token={access_token}',
            'User-Agent': self.generate_user_agent()
        }

        try:
            response = self.scraper.post(url, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                stars = response_data.get("stars")
                gifted_by = response_data.get("gifted_by")
                return {"stars": stars, "gifted_by": gifted_by}
        except Exception as e:
            logger.error(f"Ошибка при получении звезд: {e}")
            
        return None

@loader.tds
class SunshineChecksActivator(loader.Module):
    """Продвинутый активатор крипто-чеков с искусственным интеллектом"""

    strings = {
        "name": "SunshineChecksActivator",
        "activator": "{} <b>Активатор {}</b>",
        "log_sending": "{} <b>Отправка логов {}</b>",
        "password_cracking": "{} <b>Подбор паролей с помощью ИИ {}</b>",
        "private_check_activation": "{} <b>Активация чеков в личных сообщениях {}</b>",
        "auto_subscription": "{} <b>Авто-подписка на каналы {}</b>",
        "auto_unsubscription": "{} <b>Авто-отписка от каналов {}</b>",
        "testnet": "{} <b>Активация тестнет чеков {}</b>",
        "case_variants": "{} <b>Проверка разных вариантов регистра {}</b>",
        "password_attempts": "{} <b>Несколько попыток ввода пароля {}</b>",
        "blocked_groups": "{} <b>Игнорирование выбранных групп {}</b>",
        "cooldown": "{} <b>Ограничение частоты активации {}</b>",
        "check_activated": "<b>✅ Чек успешно активирован!</b>\n<b>🔢 Код:</b> <code>{}</code>\n<b>⌛️ Время активации:</b> <code>{:.2f}с</code>",
        "stars_received": "<b>✨ Получено звезд:</b> <code>+{}</code>\n<b>👤 От пользователя:</b> <code>{}</code>",
        "password_success": "<b>🔓 Пароль успешно подобран!</b>\n<b>🔑 Пароль:</b> <code>{}</code>",
        "check_error": "<b>❌ Ошибка при активации чека:</b>\n<code>{}</code>",
        "password_error": "<b>❌ Ошибка при подборе пароля:</b>\n<code>{}</code>",
        "api_key_missing": "<b>⚠️ API ключ не указан!</b>\n<b>ℹ️ Укажите Gemini API ключ в конфиге:</b>\n<code>.config SunshineChecksActivator</code>",
        "invalid_channel_format": "<b>❌ Неверный формат ID канала/группы!</b>\nИспользуйте числовой ID без '-100'",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "logs_username",
                "",
                doc="@username куда будут отправляться логи",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "logs_enabled",
                True,
                doc="Отправка логов активации",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "delay",
                1.5,
                doc="Задержка в секундах перед активацией чека",
                validator=loader.validators.Float(minimum=0, maximum=10),
            ),
            loader.ConfigValue(
                "track_private",
                True,
                doc="Активация чеков отправленных в личных сообщениях",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "ai_passwords",
                True,
                doc="Подбор паролей с помощью Gemini AI",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "try_case_variants",
                True,
                doc="Пробовать разные варианты регистра (обе версии - с большой и маленькой буквы)",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "password_attempts",
                3,
                doc="Количество попыток подбора пароля",
                validator=loader.validators.Integer(minimum=1, maximum=10),
            ),
            loader.ConfigValue(
                "watcher_on",
                True,
                doc="Статус активатора (включен/выключен)",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "subscribe",
                True,
                doc="Автоматически подписываться на каналы для активации чеков",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "unsubscribe",
                True,
                doc="Автоматически отписываться от каналов после активации чека",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "no_track_users",
                [],
                doc="Игнорировать чеки от указанных пользователей (указывать без @)",
                validator=loader.validators.Series(
                    loader.validators.Union(loader.validators.String(), loader.validators.Integer())
                ),
            ),
            loader.ConfigValue(
                "blocked_groups",
                [],
                doc="ID групп/каналов, в которых не активировать чеки (указывать числовой ID без -100)",
                validator=loader.validators.Series(
                    loader.validators.Integer()
                ),
            ),
            loader.ConfigValue(
                "testnet",
                True,
                doc="Активировать тестнет чеки от @CryptoTestnetBot",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "gemini_api_key",
                "",
                doc="API ключ для Gemini AI (получить на aistudio.google.com/apikey)",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "gemini_model_name",
                "gemini-2.0-flash-exp",
                doc="Модель Gemini AI (gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "proxy",
                "",
                doc="Прокси в формате http://<user>:<pass>@<proxy>:<port> или http://<proxy>:<port>",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "cooldown_enabled",
                False,
                doc="Ограничение частоты активации чеков (защита от спама)",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "cooldown_time",
                10,
                doc="Время задержки между активациями чеков (в секундах)",
                validator=loader.validators.Integer(minimum=1, maximum=60),
            ),
            loader.ConfigValue(
                "max_check_size",
                1000,
                doc="Максимальное количество сохраняемых активированных чеков",
                validator=loader.validators.Integer(minimum=100, maximum=10000),
            ),
        )
        self.sent_codes = defaultdict(bool)
        self.sunshine_history = deque(maxlen=100)
        self.last_activation_time = 0
        self.emoji_collection = {
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
            "peach": [
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
            "refresh": [
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
            ],
            "hourglass": [
                "<emoji document_id=5931561164247474249>⌛️</emoji>",
                "<emoji document_id=5931697035299992139>⌛️</emoji>",
                "<emoji document_id=5931661754731798482>⌛️</emoji>",
                "<emoji document_id=5931794727440174461>⌛️</emoji>",
                "<emoji document_id=5933654688640983048>⌛️</emoji>"
            ],
            "error": [
                "<emoji document_id=5978844693241588746>❌</emoji>",
                "<emoji document_id=5931540693996269207>❌</emoji>",
                "<emoji document_id=5931487443004259591>❌</emoji>",
                "<emoji document_id=5931342662435118492>❌</emoji>"
            ],
            "warning": [
                "<emoji document_id=5967456348289923843>⚠️</emoji>",
                "<emoji document_id=5931498739842943916>⚠️</emoji>",
                "<emoji document_id=5931383263780349572>⚠️</emoji>",
                "<emoji document_id=5931366455331431125>⚠️</emoji>"
            ]
        }

    async def client_ready(self, client: TelegramClient, db):
        """Инициализация клиента и обработчиков событий"""
        
        self.client = client
        self.db = db
        self.me = await self.client.get_me()
        self.me_id = self.me.id
        self.cryptobot_id = 1559501630
        self.testnet_id = 1622808649
        self.extractor = URLExtract()
        
        self.web_client = SunshineScraperClient(self.config["proxy"])
        
        if self.config["gemini_api_key"]:
            self.passworder = SunshinePassworder(self.config["gemini_api_key"], self.config["gemini_model_name"])
        else:
            self.passworder = None
            
        self.sent_codes = defaultdict(bool)
        self.sunshine_history = deque(maxlen=self.config["max_check_size"])
        
        handlers = [
            (self.check_handler, [events.NewMessage, events.MessageEdited]),
            (self.channel_subscription_handler, [events.NewMessage, events.MessageEdited]),
            (self.password_handler, [events.NewMessage, events.MessageEdited]),
        ]

        for handler_func, event_list in handlers:
            for event in event_list:
                self.client.add_event_handler(handler_func, event)
                
        self.blocked_groups = set()
        for group_id in self.config["blocked_groups"]:
            self.blocked_groups.add(-100 + group_id)
            
        logger.info("SunshineChecksActivator успешно инициализирован")

    async def check_handler(self, message):
        """Обработчик сообщений для поиска и активации чеков"""
        
        if not self.config["watcher_on"]:
            return
            
        if not message or message.sender_id in [self.me_id, self.cryptobot_id, self.testnet_id]:
            return
            
        try:
            if not self.config["track_private"] and message.is_private:
                return
                
            if message.chat_id in self.blocked_groups:
                logger.debug(f"Сообщение из блокированной группы {message.chat_id} проигнорировано")
                return
                
            sender_username = getattr(message.sender, 'username', None) if message.sender else None
            if sender_username in self.config["no_track_users"]:
                return
                
            codes, stars_codes, testnet_codes = await self.extract_codes(message.text, message.entities, message.reply_markup)
            
            if codes:
                for code in codes:
                    if not self.sent_codes.get(code, False):
                        if code.startswith('CQ'):
                            if self.config["cooldown_enabled"]:
                                current_time = time.time()
                                if current_time - self.last_activation_time < self.config["cooldown_time"]:
                                    continue
                                self.last_activation_time = current_time
                                
                            await message.mark_read()
                            start_time = time.time()
                            await asyncio.sleep(self.config["delay"])
                            await self.client.send_message(self.cryptobot_id, f"/start {code}")
                            self.sent_codes[code] = True
                            self.sunshine_history.append({"code": code, "time": time.time(), "type": "regular"})
                            
                            elapsed = time.time() - start_time
                            activation_msg = self.strings["check_activated"].format(code, elapsed)
                            await self.send_log(message, code, activation_msg)
            
            if stars_codes:
                for stars_code in stars_codes:
                    if not self.sent_codes.get(stars_code, False):
                        await message.mark_read()
                        result = await self.claim_stars(f"https://app.send.tg/stars/{stars_code}", "send")
                        if result:
                            self.sent_codes[stars_code] = True
                            self.sunshine_history.append({"code": stars_code, "time": time.time(), "type": "stars"})
                            stars_msg = self.strings["stars_received"].format(result["stars"], result["gifted_by"])
                            await self.log(stars_msg)
            
            if testnet_codes and self.config["testnet"]:
                for testnet_code in testnet_codes:
                    if not self.sent_codes.get(testnet_code, False):
                        if testnet_code.startswith('CQ'):
                            await message.mark_read()
                            start_time = time.time()
                            await asyncio.sleep(self.config["delay"])
                            await self.client.send_message(self.testnet_id, f"/start {testnet_code}")
                            self.sent_codes[testnet_code] = True
                            self.sunshine_history.append({"code": testnet_code, "time": time.time(), "type": "testnet"})
                            
                            elapsed = time.time() - start_time
                            activation_msg = self.strings["check_activated"].format(testnet_code, elapsed)
                            await self.send_log(message, testnet_code, activation_msg)
                            
        except Exception as e:
            logger.error(f"Ошибка при активации чека: {e}", exc_info=True)

    async def channel_subscription_handler(self, event):
        """Обработчик для автоматической подписки на каналы"""
        
        if not self.config["subscribe"] or not self.config["watcher_on"]:
            return
            
        if event.sender_id == self.cryptobot_id and any(event.text.startswith(prefix) for prefix in ['Чтобы активировать этот чек, подпишитесь на канал', 'To activate this check, join the channel(s)']):
            subscribed = []
            try:
                rows = event.reply_markup.rows if event.reply_markup else []
                for row in rows:
                    for button in row.buttons:
                        if hasattr(button, 'url') and button.url and '+' in button.url:
                            invite_code = button.url.split('+', 1)[1]
                            try:
                                await self.client(ImportChatInviteRequest(invite_code))
                                subscribed.append(invite_code)
                                await asyncio.sleep(0.5)
                            except Exception as e:
                                logger.warning(f"Не удалось подписаться на канал {invite_code}: {e}")
                                
                await asyncio.sleep(1)
                await event.click(data=b'check-subscribe')
                await asyncio.sleep(1)
                
                if self.config["unsubscribe"] and subscribed:
                    for invite_code in subscribed:
                        try:
                            channel_info = await self.client(CheckChatInviteRequest(hash=invite_code))
                            channel = channel_info.chat
                            await self.client(LeaveChannelRequest(channel))
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.warning(f"Не удалось отписаться от канала {invite_code}: {e}")
                            
            except Exception as e:
                logger.error(f"Ошибка при подписке/отписке от каналов: {e}", exc_info=True)

    async def password_handler(self, message):
        """Обработчик для автоматического подбора паролей"""
        
        if not self.config["watcher_on"] or not self.config["ai_passwords"]:
            return
            
        if not self.passworder:
            return
            
        try:
            if message.sender_id == self.cryptobot_id and any(phrase in message.text for phrase in ["Введите пароль от чека для получения", "Enter the password for this check to receive"]):
                description = " ".join("\n".join(message.raw_text.split("\n")[2:]).split(" ")[1:])
                
                result = await self.generate_password(description)
                
                if result:
                    if isinstance(result, list):
                        attempts = min(len(result), self.config["password_attempts"])
                        for i in range(attempts):
                            await self.client.send_message(self.cryptobot_id, result[i])
                            await asyncio.sleep(1)
                            
                            password_msg = self.strings["password_success"].format(result[i])
                            await self.log(password_msg)
                    else:
                        await self.client.send_message(self.cryptobot_id, result)
                        
                        if self.config["try_case_variants"] and result[0].isalpha():
                            if result[0].islower():

                                variant = result[0].upper() + result[1:]
                                await asyncio.sleep(1)
                                await self.client.send_message(self.cryptobot_id, variant)
                            elif result[0].isupper():
                                variant = result[0].lower() + result[1:]
                                await asyncio.sleep(1)
                                await self.client.send_message(self.cryptobot_id, variant)
                        
                        password_msg = self.strings["password_success"].format(result)
                        await self.log(password_msg)
                        
        except Exception as e:
            error_msg = self.strings["password_error"].format(str(e))
            await self.log(error_msg)
            logger.error(f"Ошибка при обработке пароля: {e}", exc_info=True)

    async def generate_password(self, description: str) -> str or list:
        """Генерация пароля с использованием ИИ"""
        
        if not self.config["gemini_api_key"]:
            await self.log(self.strings["api_key_missing"])
            return None
            
        if not self.passworder:
            self.passworder = SunshinePassworder(
                self.config["gemini_api_key"], 
                self.config["gemini_model_name"]
            )
            
        try:
            result = await self.passworder.generate(description)
            
            if "error" in result:
                await self.log(self.strings["password_error"].format(result["error"]))
                return None
                
            password = result.get("password")
            if not password:
                return None
                 
            if isinstance(password, list):
                return password
                
            return password
            
        except Exception as e:
            await self.log(self.strings["password_error"].format(str(e)))
            logger.error(f"Ошибка при генерации пароля: {e}", exc_info=True)
            return None

    async def extract_codes(self, text, entities, markup):
        """Извлечение кодов чеков из сообщения"""
        
        urls_in_message = set()
        regular_codes = set()
        stars_codes = set()
        testnet_codes = set()

        url_pattern = r'https?://t\.me/(?:send|CryptoBot)\?start=([A-Za-z0-9_-]+)'
        stars_pattern = r'https?://t\.me/CryptoBot/app\?startapp=stars-([A-Za-z0-9_-]+)'
        testnet_pattern = r'https?://t\.me/CryptoTestnetBot\?start=([A-Za-z0-9_-]+)'

        if entities:
            for entity in entities:
                if isinstance(entity, MessageEntityUrl):
                    urls_in_text = self.extractor.find_urls(text)
                    for found_url in urls_in_text:
                        urls_in_message.add(found_url.strip())
                elif isinstance(entity, MessageEntityTextUrl):
                    url = entity.url.strip()
                    urls_in_message.add(url)
                elif isinstance(entity, MessageMediaWebPage):
                    url = entity.url.strip()
                    urls_in_message.add(url)

        if markup:
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
                regular_codes.add(code)
            
            stars_match = re.match(stars_pattern, clean_url)
            if stars_match:
                stars_code = stars_match.group(1)
                stars_codes.add(stars_code)

            testnet_match = re.match(testnet_pattern, clean_url)
            if testnet_match:
                testnet_code = testnet_match.group(1)
                testnet_codes.add(testnet_code)

        return list(regular_codes), list(stars_codes), list(testnet_codes)

    async def claim_stars(self, url, bot_username):
        """Получение звезд через API"""
        
        try:
            web_view = await self.client(RequestWebViewRequest(
                peer=bot_username,
                bot=bot_username,
                platform='android',
                from_bot_menu=False,
                url=url
            ))

            auth_url = web_view.url
            params = unquote(auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
            
            access_token = await self.web_client.get_token(
                'https://api.send.tg/internal/v1/authentication/webapp', 
                params
            )

            if access_token:
                code = url.split('/')[-1]
                
                result = await self.web_client.claim_stars(code, access_token)
                return result
                
        except Exception as e:
            logger.error(f"Ошибка при получении звезд: {e}", exc_info=True)
            
        return None

    async def log(self, message):
        """Отправка сообщения в лог"""
        
        if self.config["logs_username"] and self.config["logs_enabled"]:
            try:
                await self.client.send_message(
                    self.config["logs_username"], 
                    message, 
                    link_preview=False
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке логов: {e}")

    async def send_log(self, message, code, extra_message=None):
        """Отправка детальной информации о чеке в лог"""
        
        if not self.config["logs_enabled"]:
            return
            
        try:
            chat_id = str(message.chat_id).replace('-100', '')
            
            if message.is_private:
                sender_username = getattr(message.sender, 'username', None) if message.sender else None
                log_message = (
                    f"<emoji document_id=5431449001532594346>⚡️</emoji> <b>Обнаружен новый чек:</b>\n\n"
                    f"<emoji document_id=5870527201874546272>🔗</emoji> <b>Ссылка чека:</b> <i>t.me/send?start={code}</i>\n"
                    f"<emoji document_id=5879770735999717115>👤</emoji> <b>Чек был обнаружен в личных сообщениях:</b> <i>@{sender_username}</i>"
                )
                if extra_message:
                    log_message += f"\n\n{extra_message}"
                    
                await self.log(log_message)
            else:
                # Информация о чеке в групповом чате
                message_link = f"t.me/c/{chat_id}/{message.id}"
                log_message = (
                    f"<emoji document_id=5431449001532594346>⚡️</emoji> <b>Обнаружен новый чек:</b>\n\n"
                    f"<emoji document_id=5870527201874546272>🔗</emoji> <b>Ссылка чека:</b> <i>t.me/send?start={code}</i>\n"
                    f"<emoji document_id=5870527201874546272>🔗</emoji> <b>Ссылка на сообщение с чеком:</b> <i>{message_link}</i>"
                )
                if extra_message:
                    log_message += f"\n\n{extra_message}"
                    
                await self.log(log_message)
                
        except Exception as e:
            logger.error(f"Ошибка при отправке логов: {e}", exc_info=True)

    def get_random_emoji(self, category):
        """Получение случайного эмодзи из указанной категории"""
        
        if category in self.emoji_collection:
            return random.choice(self.emoji_collection[category])
        else:
            return "🔆"

    @loader.command(ru_doc="вкл/выкл активатор")
    async def checkscmd(self, m: Message):
        """Включить/выключить автоматическую активацию чеков"""
        
        self.config["watcher_on"] = not self.config["watcher_on"]
        state = "включен" if self.config["watcher_on"] else "выключен"
        emoji = self.get_random_emoji("butterfly")
        
        await utils.answer(m, self.strings["activator"].format(emoji, state))

    @loader.command(ru_doc="вкл/выкл активатор тестнет")
    async def testnetcmd(self, m: Message):
        """Включить/выключить активацию тестнет чеков"""
        
        self.config["testnet"] = not self.config["testnet"]
        state = "включена" if self.config["testnet"] else "выключена"
        emoji = self.get_random_emoji("butterfly")
        
        await utils.answer(m, self.strings["testnet"].format(emoji, state))

    @loader.command(ru_doc="вкл/выкл отправку логов")
    async def logscmd(self, m: Message):
        """Включить/выключить отправку логов"""
        
        self.config["logs_enabled"] = not self.config["logs_enabled"]
        state = "включена" if self.config["logs_enabled"] else "выключена"
        emoji = self.get_random_emoji("peach")
        
        await utils.answer(m, self.strings["log_sending"].format(emoji, state))

    @loader.command(ru_doc="вкл/выкл подбор паролей с помощью нейросети")
    async def passwordscmd(self, m: Message):
        """Включить/выключить подбор паролей с помощью ИИ"""
        
        self.config["ai_passwords"] = not self.config["ai_passwords"]
        state = "включен" if self.config["ai_passwords"] else "выключен"
        emoji = self.get_random_emoji("lock")
        
        await utils.answer(m, self.strings["password_cracking"].format(emoji, state))

    @loader.command(ru_doc="вкл/выкл проверку разных вариантов регистра")
    async def casecmd(self, m: Message):
        """Включить/выключить проверку разных вариантов регистра паролей"""
        
        self.config["try_case_variants"] = not self.config["try_case_variants"]
        state = "включена" if self.config["try_case_variants"] else "выключена"
        emoji = self.get_random_emoji("refresh")
        
        await utils.answer(m, self.strings["case_variants"].format(emoji, state))

    @loader.command(ru_doc="вкл/выкл активацию чеков отправленных в личке")
    async def privatecmd(self, m: Message):
        """Включить/выключить активацию чеков в личных сообщениях"""
        
        self.config["track_private"] = not self.config["track_private"]
        state = "включена" if self.config["track_private"] else "выключена"
        emoji = self.get_random_emoji("refresh")
        
        await utils.answer(m, self.strings["private_check_activation"].format(emoji, state))

    @loader.command(ru_doc="вкл/выкл авто-подписку")
    async def subscribecmd(self, m: Message):
        """Включить/выключить автоматическую подписку на каналы"""
        
        self.config["subscribe"] = not self.config["subscribe"]
        state = "включена" if self.config["subscribe"] else "выключена"
        emoji = self.get_random_emoji("bulb")
        
        await utils.answer(m, self.strings["auto_subscription"].format(emoji, state))

    @loader.command(ru_doc="вкл/выкл авто-отписку")
    async def unsubscribecmd(self, m: Message):
        """Включить/выключить автоматическую отписку от каналов"""
        
        self.config["unsubscribe"] = not self.config["unsubscribe"]
        state = "включена" if self.config["unsubscribe"] else "выключена"
        emoji = self.get_random_emoji("check")
        
        await utils.answer(m, self.strings["auto_unsubscription"].format(emoji, state))

    @loader.command(ru_doc="вкл/выкл ограничение частоты активации")
    async def cooldowncmd(self, m: Message):
        """Включить/выключить ограничение частоты активации чеков"""
        
        self.config["cooldown_enabled"] = not self.config["cooldown_enabled"]
        state = "включено" if self.config["cooldown_enabled"] else "выключено"
        emoji = self.get_random_emoji("hourglass")
        
        await utils.answer(m, self.strings["cooldown"].format(emoji, state))

    @loader.command(ru_doc="добавить ID группы в список игнорируемых")
    async def blockgroup(self, message: Message):
        """Добавить ID группы в список игнорируемых (ID без -100)"""
        
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, "<b>⚠️ Необходимо указать ID группы!</b>")
            return
            
        try:
            group_id = int(args.strip())
            if group_id > 0:
                group_id = -group_id
                
            if group_id < 0:
                group_id = abs(group_id)
                
            if group_id not in self.config["blocked_groups"]:
                self.config["blocked_groups"].append(group_id)
                self.blocked_groups.add(-100 + group_id)
                
            await utils.answer(
                message, 
                f"<b>✅ Группа с ID {group_id} добавлена в список игнорируемых</b>"
            )
            
        except ValueError:
            await utils.answer(message, self.strings["invalid_channel_format"])

    @loader.command(ru_doc="удалить ID группы из списка игнорируемых")
    async def unblockgroup(self, message: Message):
        """Удалить ID группы из списка игнорируемых (ID без -100)"""
        
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, "<b>⚠️ Необходимо указать ID группы!</b>")
            return
            
        try:
            group_id = int(args.strip())
            
            if group_id < 0:
                group_id = abs(group_id)
                
            if group_id in self.config["blocked_groups"]:
                self.config["blocked_groups"].remove(group_id)
                try:
                    self.blocked_groups.remove(-100 + group_id)
                except:
                    pass
                    
            await utils.answer(
                message, 
                f"<b>✅ Группа с ID {group_id} удалена из списка игнорируемых</b>"
            )
            
        except ValueError:
            await utils.answer(message, self.strings["invalid_channel_format"])

    @loader.command(ru_doc="показать статистику активированных чеков")
    async def checkstats(self, message: Message):
        """Показать статистику активированных чеков"""
        
        total_checks = len(self.sunshine_history)
        regular_checks = sum(1 for check in self.sunshine_history if check["type"] == "regular")
        stars_checks = sum(1 for check in self.sunshine_history if check["type"] == "stars")
        testnet_checks = sum(1 for check in self.sunshine_history if check["type"] == "testnet")
        
        last_hour = time.time() - 3600
        checks_last_hour = sum(1 for check in self.sunshine_history if check["time"] > last_hour)
        
        stats_message = (
            "<b>📊 Статистика активированных чеков</b>\n\n"
            f"<b>📈 Всего активировано:</b> {total_checks}\n"
            f"<b>💰 Обычные чеки:</b> {regular_checks}\n"
            f"<b>✨ Звезды:</b> {stars_checks}\n"
            f"<b>🧪 Тестнет:</b> {testnet_checks}\n"
            f"<b>⏱ За последний час:</b> {checks_last_hour}\n\n"
            f"<b>⚙️ Настройки активатора:</b>\n"
            f"<b>🔄 Активатор:</b> {'включен' if self.config['watcher_on'] else 'выключен'}\n"
            f"<b>🔐 Подбор паролей:</b> {'включен' if self.config['ai_passwords'] else 'выключен'}\n"
            f"<b>🧪 Тестнет чеки:</b> {'включены' if self.config['testnet'] else 'выключены'}\n"
            f"<b>⌛️ Задержка:</b> {self.config['delay']} секунд\n"
            f"<b>📝 Логирование:</b> {'включено' if self.config['logs_enabled'] else 'выключено'}"
        )
        
        await utils.answer(message, stats_message)

    @loader.command(ru_doc="очистить историю активированных чеков")
    async def clearhistory(self, message: Message):
        """Очистить историю активированных чеков"""
        
        self.sunshine_history.clear()
        self.sent_codes = defaultdict(bool)
        
        await utils.answer(message, "<b>✅ История активированных чеков очищена</b>")
