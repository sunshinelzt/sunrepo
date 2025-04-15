# meta developer: @sunshinelzt
# scope: hikka_only
# scope: hikka_min 1.3.0
# requires: telegraph requests

import logging
import random
import string
import re
import json
from telethon.tl.types import Message
from .. import loader, utils
import aiohttp
import asyncio
from datetime import datetime
import requests
from telegraph import Telegraph
from telegraph.exceptions import TelegraphException
from urllib.parse import quote, urlencode

logger = logging.getLogger(__name__)

@loader.tds
class TelegraphIPLoggerMod(loader.Module):
    """Создает статьи в Telegraph с трекером IPLogger для сбора информации о посетителях"""
    
    strings = {
        "name": "TelegraphIPLogger",
        "loading": "🔄 <b>Создание статьи в Telegraph с IPLogger...</b>",
        "tgph_created": "📝 <b>Telegraph статья успешно создана!</b>\n\n<b>Название:</b> <code>{title}</code>\n<b>URL:</b> <code>{url}</code>\n<b>Статистика:</b> <code>{stats_url}</code>",
        "account_created": "✅ <b>Telegraph аккаунт создан!</b>\n<b>Имя:</b> {name}\n<b>Токен:</b> <code>{token}</code>",
        "error": "❌ <b>Ошибка:</b> {error}",
        "no_iplogger": "⚠️ <b>Для работы необходим API ключ IPLogger.</b>\n\nПолучите ключ на сайте https://iplogger.org и добавьте его через команду:\n<code>.iplogset ваш_ключ</code>",
        "iplogger_set": "✅ <b>API ключ IPLogger успешно установлен!</b>",
        "preview_article": "📋 <b>Предпросмотр статьи:</b>\n\n<b>Заголовок:</b> {title}\n<b>Автор:</b> {author}\n<b>Текст:</b> {text_preview}...\n\n<b>Для публикации используйте:</b> <code>.tgph publish</code>",
        "retrieving_stats": "🔄 <b>Получение статистики IPLogger...</b>",
        "stats": "📊 <b>Статистика посещений</b>\n\n<b>URL:</b> <code>{url}</code>\n<b>Посещений:</b> {visits}\n<b>Уникальных посетителей:</b> {unique}\n<b>Последнее посещение:</b> {last_visit}\n\n<b>Детальная статистика:</b> <code>{stats_url}</code>",
        "iplogger_type_help": "⚙️ <b>Доступные типы трекеров IPLogger:</b>\n\n" +
                             "• <code>image</code> - Невидимое изображение 1x1 пиксель\n" +
                             "• <code>redirect</code> - Редирект на указанный URL\n" +
                             "• <code>webroot</code> - Веб-документ с JavaScript трекером\n" +
                             "• <code>invisible</code> - Полностью невидимый JavaScript трекер\n\n" +
                             "Используйте: <code>.iplogset type тип_трекера</code>",
        "iplogger_type_set": "✅ <b>Тип трекера IPLogger установлен:</b> {type}",
        "help_info": "ℹ️ <b>TelegraphIPLogger - модуль для создания статей Telegraph с трекером IPLogger</b>\n\n" +
                     "<b>Команды:</b>\n" +
                     "• <code>.tgph</code> - создать новую статью с трекером\n" +
                     "• <code>.tgph publish</code> - опубликовать подготовленную статью\n" +
                     "• <code>.tgphset</code> - настроить Telegraph аккаунт\n" +
                     "• <code>.iplogset ключ_api</code> - установить API ключ IPLogger\n" +
                     "• <code>.iplogset type тип_трекера</code> - установить тип трекера\n" +
                     "• <code>.iplogset redirect url</code> - установить URL для редиректа\n" +
                     "• <code>.tgphlogs [ID]</code> - получить статистику посещений\n" +
                     "• <code>.tgphlist</code> - список созданных статей\n\n" +
                     "<b>Настройки:</b>\n" +
                     "• ARTICLE_TITLE - заголовок статьи\n" +
                     "• ARTICLE_TEXT - содержимое статьи\n" +
                     "• NOTIFY_ON_VISIT - уведомлять о новых посещениях"
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "ARTICLE_TITLE", "Интересная информация о Telegram", "Заголовок статьи Telegraph",
            "ARTICLE_TEXT", "Telegram - это мессенджер, который сочетает в себе скорость, безопасность и удобство. Узнайте больше о функциях и возможностях этой платформы.", 
            "Текст для статьи Telegraph (поддерживает HTML-форматирование)",
            "AUTHOR_NAME", "Telegram Expert", "Имя автора статьи",
            "NOTIFY_ON_VISIT", True, "Уведомлять о посещениях статьи"
        )
        
        # Временное хранилище для создаваемой статьи
        self.temp_article = None
        
        # Хранилище данных о статьях
        self.articles = {}
        self.telegraph_token = None
        self.telegraph_author = None
        self.iplogger_api_key = None
        self.iplogger_tracker_type = "image"  # По умолчанию невидимое изображение
        self.iplogger_redirect_url = None
    
    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        
        # Загружаем сохраненные данные
        self.articles = self.db.get(self.__class__.__name__, "articles", {})
        self.telegraph_token = self.db.get(self.__class__.__name__, "telegraph_token", None)
        self.telegraph_author = self.db.get(self.__class__.__name__, "telegraph_author", self.config["AUTHOR_NAME"])
        self.iplogger_api_key = self.db.get(self.__class__.__name__, "iplogger_api_key", None)
        self.iplogger_tracker_type = self.db.get(self.__class__.__name__, "iplogger_tracker_type", "image")
        self.iplogger_redirect_url = self.db.get(self.__class__.__name__, "iplogger_redirect_url", None)
        
    def _save_data(self):
        """Сохраняет данные в базу"""
        self.db.set(self.__class__.__name__, "articles", self.articles)
        self.db.set(self.__class__.__name__, "telegraph_token", self.telegraph_token)
        self.db.set(self.__class__.__name__, "telegraph_author", self.telegraph_author)
        self.db.set(self.__class__.__name__, "iplogger_api_key", self.iplogger_api_key)
        self.db.set(self.__class__.__name__, "iplogger_tracker_type", self.iplogger_tracker_type)
        self.db.set(self.__class__.__name__, "iplogger_redirect_url", self.iplogger_redirect_url)
        
    def _generate_random_id(self, length=8):
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
            
            self.telegraph_token = account["access_token"]
            self.telegraph_author = author_name
            self._save_data()
            
            return account
        except Exception as e:
            logger.exception(f"Ошибка при создании аккаунта Telegraph: {e}")
            return None
    
    async def _create_iplogger_tracker(self, domain="iplogger.org"):
        """Создает трекер IPLogger"""
        if not self.iplogger_api_key:
            return None, "API ключ IPLogger не установлен"
        
        # Определяем тип трекера
        tracker_type = self.iplogger_tracker_type
        
        # Базовый URL для API IPLogger
        api_url = "https://iplogger.org/logger/new/"
        
        # Параметры для создания трекера
        params = {
            'key': self.iplogger_api_key,
            'type': tracker_type,
            'domain': domain
        }
        
        # Если тип трекера redirect, добавляем URL для перенаправления
        if tracker_type == "redirect" and self.iplogger_redirect_url:
            params['redirect'] = self.iplogger_redirect_url
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, data=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("status") == "success":
                            logger_data = result.get("data", {})
                            return logger_data, None
                        else:
                            return None, result.get("error", "Неизвестная ошибка IPLogger")
                    else:
                        return None, f"Ошибка запроса к API IPLogger: {response.status}"
        except Exception as e:
            logger.exception(f"Ошибка при создании трекера IPLogger: {e}")
            return None, str(e)
    
    async def _get_iplogger_stats(self, iplogger_id):
        """Получает статистику посещений IPLogger"""
        if not self.iplogger_api_key:
            return None, "API ключ IPLogger не установлен"
        
        api_url = f"https://iplogger.org/logger/{iplogger_id}/stat/"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params={'key': self.iplogger_api_key}) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("status") == "success":
                            return result.get("data", {}), None
                        else:
                            return None, result.get("error", "Неизвестная ошибка IPLogger")
                    else:
                        return None, f"Ошибка запроса к API IPLogger: {response.status}"
        except Exception as e:
            logger.exception(f"Ошибка при получении статистики IPLogger: {e}")
            return None, str(e)
    
    async def _create_telegraph_page(self, title, content, author_name, iplogger_tracker):
        """Создает страницу в Telegraph с трекером IPLogger"""
        telegraph = None
        
        # Инициализируем Telegraph API
        if self.telegraph_token:
            telegraph = Telegraph(self.telegraph_token)
        else:
            account = await self._create_telegraph_account(author_name=author_name)
            if account:
                telegraph = Telegraph(self.telegraph_token)
            else:
                return None, "Не удалось создать аккаунт Telegraph"
        
        try:
            # Подготавливаем контент для Telegraph
            content_html = ""
            for paragraph in content.split("\n\n"):
                if paragraph.strip():
                    content_html += f"<p>{paragraph.strip()}</p>"
            
            # Добавляем трекер IPLogger в зависимости от типа
            if self.iplogger_tracker_type == "image":
                # Невидимое изображение
                content_html += f'<img src="{iplogger_tracker["tracking_link"]}" style="position:absolute;opacity:0;width:1px;height:1px;" />'
            elif self.iplogger_tracker_type == "invisible":
                # Невидимый JavaScript трекер
                content_html += f'<script src="{iplogger_tracker["tracking_link"]}"></script>'
            elif self.iplogger_tracker_type == "webroot":
                # Веб-документ с JavaScript трекером
                content_html += f'<iframe src="{iplogger_tracker["tracking_link"]}" style="width:1px;height:1px;position:absolute;opacity:0;"></iframe>'
            
            # Создаем страницу в Telegraph
            response = telegraph.create_page(
                title=title,
                author_name=author_name,
                html_content=content_html
            )
            
            page_url = f"https://telegra.ph/{response['path']}"
            return page_url, None
            
        except Exception as e:
            logger.exception(f"Ошибка при создании страницы Telegraph: {e}")
            return None, str(e)
    
    @loader.owner
    async def iplogsetcmd(self, message: Message):
        """Настроить API ключ и параметры IPLogger"""
        args = utils.get_args_raw(message)
        
        if not args:
            if not self.iplogger_api_key:
                await utils.answer(message, self.strings["no_iplogger"])
            else:
                key_preview = f"{self.iplogger_api_key[:5]}...{self.iplogger_api_key[-3:]}"
                await utils.answer(
                    message, 
                    f"ℹ️ <b>Текущие настройки IPLogger:</b>\n\n"
                    f"<b>API ключ:</b> <code>{key_preview}</code>\n"
                    f"<b>Тип трекера:</b> <code>{self.iplogger_tracker_type}</code>\n"
                    f"<b>URL редиректа:</b> <code>{self.iplogger_redirect_url or 'Не установлен'}</code>\n\n"
                    f"<b>Для изменения параметров используйте:</b>\n"
                    f"• <code>.iplogset ключ_api</code> - установить API ключ\n"
                    f"• <code>.iplogset type тип_трекера</code> - установить тип трекера\n"
                    f"• <code>.iplogset redirect url</code> - установить URL для редиректа\n"
                    f"• <code>.iplogset help</code> - показать информацию о типах трекеров"
                )
            return
        
        if args == "help":
            await utils.answer(message, self.strings["iplogger_type_help"])
            return
            
        if args.startswith("type "):
            # Установка типа трекера
            tracker_type = args.split("type ")[1].strip()
            
            if tracker_type not in ["image", "redirect", "webroot", "invisible"]:
                return await utils.answer(
                    message, 
                    f"❌ <b>Неверный тип трекера:</b> {tracker_type}\n\n"
                    f"Используйте <code>.iplogset help</code> для просмотра доступных типов."
                )
            
            self.iplogger_tracker_type = tracker_type
            self._save_data()
            
            await utils.answer(
                message, 
                self.strings["iplogger_type_set"].format(type=tracker_type)
            )
            
        elif args.startswith("redirect "):
            # Установка URL для редиректа
            redirect_url = args.split("redirect ")[1].strip()
            
            # Проверяем, что URL корректный
            if not redirect_url.startswith(("http://", "https://")):
                redirect_url = f"https://{redirect_url}"
            
            self.iplogger_redirect_url = redirect_url
            self._save_data()
            
            await utils.answer(
                message, 
                f"✅ <b>URL для редиректа установлен:</b>\n<code>{redirect_url}</code>"
            )
            
        else:
            # Считаем, что передан API ключ
            api_key = args.strip()
            
            # Простая проверка формата API ключа IPLogger (обычно 32 символа)
            if len(api_key) < 20:
                return await utils.answer(
                    message, 
                    "❌ <b>Неверный формат API ключа IPLogger.</b>\n\n"
                    "Получите ключ на сайте https://iplogger.org"
                )
            
            self.iplogger_api_key = api_key
            self._save_data()
            
            await utils.answer(message, self.strings["iplogger_set"])
    
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
            
            # Обновляем имя автора в Telegraph, если есть токен
            if self.telegraph_token:
                try:
                    telegraph = Telegraph(self.telegraph_token)
                    telegraph.edit_account_info(author_name=author_name)
                except Exception as e:
                    logger.warning(f"Не удалось обновить имя автора в Telegraph: {e}")
            
            await utils.answer(message, f"✅ <b>Имя автора установлено:</b> {author_name}")
    
    @loader.owner
    async def tgphcmd(self, message: Message):
        """Создать статью в Telegraph с трекером IPLogger"""
        args = utils.get_args_raw(message)
        
        # Проверяем, установлен ли API ключ IPLogger
        if not self.iplogger_api_key:
            return await utils.answer(message, self.strings["no_iplogger"])
            
        if args == "publish" and self.temp_article:
            # Публикуем подготовленную статью
            await utils.answer(message, self.strings["loading"])
            
            title = self.temp_article["title"]
            content = self.temp_article["content"]
            author = self.temp_article["author"]
            
            # Создаем трекер IPLogger
            iplogger_tracker, error = await self._create_iplogger_tracker()
            if error:
                return await utils.answer(message, self.strings["error"].format(error=error))
            
            # Создаем страницу в Telegraph с трекером
            page_url, error = await self._create_telegraph_page(title, content, author, iplogger_tracker)
            if error:
                return await utils.answer(message, self.strings["error"].format(error=error))
            
            # Получаем данные о трекере
            iplogger_id = iplogger_tracker.get("id")
            stats_url = iplogger_tracker.get("stat_link")
            
            # Сохраняем информацию о статье
            article_id = self._generate_random_id()
            self.articles[article_id] = {
                "title": title,
                "url": page_url,
                "author": author,
                "iplogger_id": iplogger_id,
                "stats_url": stats_url,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_data()
            
            # Сбрасываем временную статью
            self.temp_article = None
            
            await utils.answer(
                message, 
                self.strings["tgph_created"].format(
                    title=title,
                    url=page_url,
                    stats_url=stats_url
                )
            )
            return
            
        # Создаем новую статью
        title = self.config["ARTICLE_TITLE"]
        content = self.config["ARTICLE_TEXT"]
        author = self.telegraph_author or self.config["AUTHOR_NAME"]
        
        # Сохраняем во временное хранилище
        self.temp_article = {
            "title": title,
            "content": content,
            "author": author
        }
        
        # Показываем предпросмотр статьи
        text_preview = content[:100].replace("\n", " ")
        await utils.answer(
            message,
            self.strings["preview_article"].format(
                title=title,
                author=author,
                text_preview=text_preview
            )
        )
    
    @loader.owner
    async def tgphlogscmd(self, message: Message):
        """Получить статистику посещений IPLogger"""
        args = utils.get_args_raw(message)
        
        # Проверяем, установлен ли API ключ IPLogger
        if not self.iplogger_api_key:
            return await utils.answer(message, self.strings["no_iplogger"])
        
        if not args:
            # Если ID не указан, берем последнюю созданную статью
            if not self.articles:
                return await utils.answer(message, "❌ <b>У вас нет созданных статей с трекером.</b>")
            
            article_id = list(self.articles.keys())[-1]
            iplogger_id = self.articles[article_id]["iplogger_id"]
        else:
            # Проверяем, есть ли статья с указанным ID
            if args not in self.articles:
                # Возможно, был передан непосредственно ID трекера IPLogger
                iplogger_id = args
            else:
                article_id = args
                iplogger_id = self.articles[article_id]["iplogger_id"]
        
        await utils.answer(message, self.strings["retrieving_stats"])
        
        # Получаем статистику
        stats, error = await self._get_iplogger_stats(iplogger_id)
        if error:
            return await utils.answer(message, self.strings["error"].format(error=error))
        
        # Формируем ответ со статистикой
        article = None
        for a_id, a_data in self.articles.items():
            if a_data["iplogger_id"] == iplogger_id:
                article = a_data
                break
        
        title = article["title"] if article else "Неизвестная статья"
        url = article["url"] if article else "Неизвестно"
        stats_url = article["stats_url"] if article else stats.get("stat_link", "")
        
        visits = stats.get("visits", 0)
        unique = stats.get("unique", 0)
        last_visit = stats.get("last_visit", "Нет посещений")
        
        response = f"📊 <b>Статистика посещений статьи</b>\n\n"
        response += f"<b>Название:</b> {title}\n"
        response += f"<b>URL:</b> <code>{url}</code>\n"
        response += f"<b>Посещений:</b> {visits}\n"
        response += f"<b>Уникальных посетителей:</b> {unique}\n"
        
        if last_visit and last_visit != "Нет посещений":
            response += f"<b>Последнее посещение:</b> {last_visit}\n"
        
        # Если есть данные о последних посетителях
        if "logs" in stats and stats["logs"]:
            response += "\n<b>Последние посещения:</b>\n"
            
            for i, log in enumerate(stats["logs"][:5], 1):
                ip = log.get("ip", "Скрыто")
                country = log.get("country", "Неизвестно")
                city = log.get("city", "")
                device = log.get("device", {}).get("name", "Неизвестно")
                browser = log.get("browser", {}).get("name", "")
                time = log.get("time", "")
                
                location = f"{country}, {city}" if city else country
                browser_info = f"{browser}" if browser else ""
                
                response += f"{i}. IP: <code>{ip}</code> | {location} | {device} {browser_info} | {time}\n"
        
        response += f"\n<b>Полная статистика:</b> <code>{stats_url}</code>"
        
        await utils.answer(message, response)
    
    @loader.owner
    async def tgphlistcmd(self, message: Message):
        """Показать список созданных статей с трекером"""
        if not self.articles:
            return await utils.answer(message, "❌ <b>У вас нет созданных статей с трекером.</b>")
        
        response = f"📋 <b>Созданные статьи ({len(self.articles)}):</b>\n\n"
        
        for idx, (article_id, article) in enumerate(sorted(self.articles.items(), key=lambda x: x[1]["created"], reverse=True), 1):
            response += f"{idx}. <b>{article['title']}</b>\n"
            response += f"   🆔 <code>{article_id}</code>\n"
            response += f"   🔗 <code>{article['url']}</code>\n"
            response += f"   📊 <code>{article['stats_url']}</code>\n"
            response += f"   📅 Создана: {article['created']}\n\n"
        
        response += "Используйте <code>.tgphlogs [ID]</code> для просмотра статистики."
        await utils.answer(message, response)
    
    @loader.owner
    async def tgphhelpcmd(self, message: Message):
        """Показать помощь по модулю"""
        await utils.answer(message, self.strings["help_info"])
