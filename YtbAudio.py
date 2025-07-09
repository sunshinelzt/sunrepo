# meta developer: @sunshinelzt

import asyncio
import re
import json
import aiohttp
from urllib.parse import quote, urlparse, parse_qs
from telethon import events
from telethon.errors import ChatWriteForbiddenError, FloodWaitError
from .. import loader, utils
import logging

@loader.tds
class YtbAudioModule(loader.Module):
    """Модуль для загрузки музыки с YouTube"""
    
    strings = {
        "name": "YtbAudio",
        "searching": "<b><emoji document_id=5874960879434338403>🔎</emoji> Ищу трек на YouTube...</b>",
        "downloading": "<b><emoji document_id=6005843436479975944>🔁</emoji> Загружаю аудио...</b>",
        "no_query": "<b><emoji document_id=5778527486270770928>❌</emoji> Укажите название трека или YouTube ссылку</b>",
        "error": "<b><emoji document_id=5778527486270770928>❌</emoji> Произошла ошибка при загрузке</b>\n<i>Попробуйте другой запрос или повторите позже</i>",
        "processing": "<b><emoji document_id=5877260593903177342>⚙</emoji> Обрабатываю запрос...</b>",
        "found": "<b><emoji document_id=5776375003280838798>✅</emoji> Найдено:</b> <code>{}</code>\n<b><emoji document_id=5879770735999717115>👤</emoji> Автор:</b> <code>{}</code>",
        "sending": "<b><emoji document_id=5877540355187937244>📤</emoji> Отправляю трек...</b>",
        "bot_error": "<b><emoji document_id=5778527486270770928>❌</emoji> Ошибка при работе с ботом</b>\n<i>Попробуйте позже</i>",
        "timeout": "<b><emoji document_id=5877500027378171759>⏰</emoji> Превышено время ожидания</b>\n<i>Попробуйте снова</i>",
        "invalid_url": "<b><emoji document_id=5778527486270770928>❌</emoji> Неверная ссылка YouTube</b>"
    }
    
    strings_en = {
        "name": "YtbAudio",
        "searching": "<b><emoji document_id=5874960879434338403>🔎</emoji> Searching track on YouTube...</b>",
        "downloading": "<b><emoji document_id=6005843436479975944>🔁</emoji> Downloading audio...</b>",
        "no_query": "<b><emoji document_id=5778527486270770928>❌</emoji> Please specify track name or YouTube URL</b>",
        "error": "<b><emoji document_id=5778527486270770928>❌</emoji> Error occurred while downloading</b>\n<i>Try another query or retry later</i>",
        "processing": "<b><emoji document_id=5877260593903177342>⚙</emoji> Processing request...</b>",
        "found": "<b><emoji document_id=5776375003280838798>✅</emoji> Found:</b> <code>{}</code>\n<b><emoji document_id=5879770735999717115>👤</emoji> Author:</b> <code>{}</code>",
        "sending": "<b><emoji document_id=5877540355187937244>📤</emoji> Sending track...</b>",
        "bot_error": "<b><emoji document_id=5778527486270770928>❌</emoji> Bot interaction error</b>\n<i>Try again later</i>",
        "timeout": "<b><emoji document_id=5877500027378171759>⏰</emoji> Request timeout</b>\n<i>Please try again</i>",
        "invalid_url": "<b><emoji document_id=5778527486270770928>❌</emoji> Invalid YouTube URL</b>"
    }

    def __init__(self):
        self.bot_username = "@YtbAudioBot"
        self.name = self.strings["name"]
        self.logger = logging.getLogger(__name__)

    async def extract_video_id(self, url):
        """Извлечение ID видео из различных форматов ссылок YouTube"""
        if not url:
            return None
            
        # Нормализация URL
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        try:
            parsed_url = urlparse(url)
            
            # Обработка youtu.be ссылок
            if 'youtu.be' in parsed_url.netloc:
                path = parsed_url.path.strip('/')
                # Удаляем дополнительные параметры
                return path.split('?')[0].split('&')[0]
                
            # Обработка стандартных youtube.com и music.youtube.com ссылок
            if any(domain in parsed_url.netloc for domain in ['youtube.com', 'music.youtube.com']):
                query_params = parse_qs(parsed_url.query)
                
                # Проверка параметра v для watch ссылок
                if 'v' in query_params:
                    return query_params['v'][0]
                    
                # Проверка для других форматов (shorts, live и т.д.)
                path_parts = parsed_url.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    if path_parts[0] in ['shorts', 'live', 'embed', 'v']:
                        return path_parts[1]
            
            # Резервный метод через регулярные выражения
            patterns = [
                r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/shorts\/|youtube\.com\/live\/|music\.youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
                r'youtube\.com\/attribution_link\?.*v%3D([a-zA-Z0-9_-]{11})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
                    
        except Exception as e:
            self.logger.error(f"Error extracting video ID: {str(e)}")
            
        return None

    async def search_youtube(self, query):
        """Поиск видео на YouTube"""
        try:
            search_url = f"https://www.youtube.com/results?search_query={quote(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(search_url) as response:
                    if response.status != 200:
                        return None
                    html = await response.text()
            
            # Множественные методы поиска video ID
            patterns = [
                r'"videoId":"([a-zA-Z0-9_-]{11})"',
                r'watch\?v=([a-zA-Z0-9_-]{11})',
                r'/watch\?v=([a-zA-Z0-9_-]{11})',
                r'videoId&quot;:&quot;([a-zA-Z0-9_-]{11})&quot;'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html)
                if matches:
                    return f"https://www.youtube.com/watch?v={matches[0]}"
            
        except Exception as e:
            self.logger.error(f"Error searching YouTube: {str(e)}")
            
        return None
    
    async def get_video_info(self, video_url):
        """Получение информации о видео"""
        try:
            video_id = await self.extract_video_id(video_url)
            if not video_id:
                return "Неизвестный трек", "Неизвестный исполнитель"
            
            # Используем oembed API
            api_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            title = data.get('title', 'Неизвестный трек')
                            author = data.get('author_name', 'Неизвестный исполнитель')
                            
                            # Очищаем название от "- YouTube"
                            title = re.sub(r'\s*-\s*YouTube\s*$', '', title)
                            
                            return title, author
                        except json.JSONDecodeError:
                            pass
            
            # Запасной метод через HTML парсинг
            video_page_url = f"https://www.youtube.com/watch?v={video_id}"
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(video_page_url) as response:
                    if response.status != 200:
                        return "Неизвестный трек", "Неизвестный исполнитель"
                    html = await response.text()
            
            # Улучшенные паттерны для извлечения информации
            title_match = re.search(r'<title>([^<]+)</title>', html)
            title = title_match.group(1) if title_match else "Неизвестный трек"
            title = re.sub(r'\s*-\s*YouTube\s*$', '', title)
            
            author_patterns = [
                r'"ownerChannelName":"([^"]+)"',
                r'"author":"([^"]+)"',
                r'<link itemprop="name" content="([^"]+)"'
            ]
            
            author = "Неизвестный исполнитель"
            for pattern in author_patterns:
                match = re.search(pattern, html)
                if match:
                    author = match.group(1)
                    break
            
            return title, author
            
        except Exception as e:
            self.logger.error(f"Error getting video info: {str(e)}")
            return "Неизвестный трек", "Неизвестный исполнитель"

    async def cleanup_bot_chat(self, message):
        """Очистка чата с ботом"""
        try:
            deleted_count = 0
            async for msg in message.client.iter_messages(self.bot_username, limit=50):
                try:
                    await msg.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.1)  # Небольшая задержка для избежания флуда
                except Exception as e:
                    self.logger.debug(f"Could not delete message: {str(e)}")
                    
            #self.logger.info(f"Deleted {deleted_count} messages from bot chat")
            
        except Exception as e:
            self.logger.error(f"Error cleaning bot chat: {str(e)}")

    @loader.unrestricted
    @loader.ratelimit
    async def ytbcmd(self, message):
        """[YouTube URL или название трека] - Загрузить аудио с YouTube"""
        query = utils.get_args_raw(message)
        if not query:
            return await utils.answer(message, self.strings["no_query"])
        
        status_msg = await utils.answer(message, self.strings["processing"])
        
        try:
            # Определяем тип запроса
            youtube_patterns = [
                r'(https?://)?(www\.)?(youtube\.com|music\.youtube\.com|youtu\.be)/.+',
                r'(youtube\.com|music\.youtube\.com|youtu\.be)/.+'
            ]
            
            is_youtube_url = any(re.match(pattern, query, re.IGNORECASE) for pattern in youtube_patterns)
            
            if not is_youtube_url:
                await utils.answer(status_msg, self.strings["searching"])
                youtube_url = await self.search_youtube(query)
                if not youtube_url:
                    return await utils.answer(status_msg, self.strings["error"])
            else:
                youtube_url = query
                # Проверяем валидность URL
                video_id = await self.extract_video_id(youtube_url)
                if not video_id:
                    return await utils.answer(status_msg, self.strings["invalid_url"])
            
            # Получаем информацию о треке
            title, author = await self.get_video_info(youtube_url)
            await utils.answer(status_msg, self.strings["found"].format(title, author))
            
            # Нормализуем URL для бота
            video_id = await self.extract_video_id(youtube_url)
            normalized_url = f"https://www.youtube.com/watch?v={video_id}"
            
            await utils.answer(status_msg, self.strings["downloading"])
            
            # Взаимодействие с ботом
            try:
                async with message.client.conversation(self.bot_username) as conv:
                    # Отправляем запрос
                    await conv.send_message(normalized_url)
                    
                    audio_file = None
                    audio_response = None
                    
                    # Ждем ответ с аудио
                    for attempt in range(3):  # Максимум 3 попытки получить ответ
                        try:
                            response = await conv.get_response(timeout=60)
                            
                            if response.media:
                                audio_file = response.media
                                audio_response = response
                                break
                            elif response.text and any(word in response.text.lower() for word in ['error', 'ошибка', 'failed']):
                                raise Exception("Bot returned error")
                                
                        except asyncio.TimeoutError:
                            if attempt == 2:  # Последняя попытка
                                raise Exception("Timeout waiting for bot response")
                            await asyncio.sleep(2)
                            continue
                    
                    if audio_file:
                        await utils.answer(status_msg, self.strings["sending"])
                        
                        # Создаем красивую подпись
                        caption = (
                            f"<emoji document_id=5891249688933305846>🎵</emoji> <b>{title}</b>\n"
                            f"<emoji document_id=5879770735999717115>👤</emoji> <i>{author}</i>\n"
                            f"<emoji document_id=5877465816030515018>🔗</emoji> <a href='{youtube_url}'>Открыть в YouTube</a>"
                        )
                        
                        # Отправляем аудио
                        await message.client.send_file(
                            message.chat_id,
                            audio_file,
                            caption=caption,
                            parse_mode='html',
                            reply_to=message.reply_to_msg_id
                        )
                        
                        # Моментально очищаем чат с ботом
                        await self.cleanup_bot_chat(message)
                        
                        # Удаляем статусное сообщение
                        await status_msg.delete()
                        return
                    else:
                        raise Exception("No audio received from bot")
                        
            except FloodWaitError as e:
                await utils.answer(status_msg, f"<b><emoji document_id=5877500027378171759>⏰</emoji> Флуд-контроль</b>\n<i>Подождите {e.seconds} секунд</i>")
                return
                
            except ChatWriteForbiddenError:
                await utils.answer(status_msg, f"<b><emoji document_id=5778527486270770928>❌</emoji> Нет доступа к боту</b>\n<i>Проверьте, запущен ли бот @{self.bot_username.replace('@', '')}</i>")
                return
                
            except Exception as e:
                self.logger.error(f"Bot interaction error: {str(e)}")
                await utils.answer(status_msg, self.strings["bot_error"])
                return
            
        except Exception as e:
            self.logger.error(f"Error in ytbcmd: {str(e)}")
            await utils.answer(status_msg, self.strings["error"])
            
        finally:
            # Всегда пытаемся очистить чат с ботом в случае ошибки
            try:
                await self.cleanup_bot_chat(message)
            except Exception:
                pass

    async def client_ready(self, client, db):
        """Вызывается при готовности клиента"""
        #self.logger.info(f"YtbAudio module loaded successfully")
        
        # Проверяем доступность бота
        try:
            await client.get_entity(self.bot_username)
            #self.logger.info(f"Bot {self.bot_username} is accessible")
        except Exception as e:
            self.logger.warning(f"Bot {self.bot_username} might not be accessible: {str(e)}")
