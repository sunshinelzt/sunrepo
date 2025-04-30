# meta developer: @sunshinelzt

import asyncio
import re
import json
import aiohttp
from urllib.parse import quote, urlparse, parse_qs
from telethon import events
from .. import loader, utils

@loader.tds
class YtbAudioModule(loader.Module):
    """Модуль для загрузки музыки с YouTube"""
    
    strings = {
        "name": "YtbAudio",
        "searching": "<b><emoji document_id=5874960879434338403>🔎</emoji> Ищу трек на YouTube...</b>",
        "downloading": "<b><emoji document_id=6005843436479975944>🔁</emoji> Загружаю аудио...</b>",
        "no_query": "<b><emoji document_id=5778527486270770928>❌</emoji> Укажите название трека или YouTube ссылку</b>",
        "error": "<b><emoji document_id=5778527486270770928>❌</emoji> Произошла ошибка при загрузке. Попробуйте другой запрос.</b>",
        "processing": "<b><emoji document_id=5877260593903177342>⚙</emoji> Обрабатываю запрос...</b>",
        "found": "<b><emoji document_id=5776375003280838798>✅</emoji> Найдено: </b><code>{}</code>\n<b><emoji document_id=5879770735999717115>👤</emoji> Автор: </b><code>{}</code>",
        "sending": "<b><emoji document_id=5877540355187937244>📤</emoji> Отправляю трек...</b>"
    }
    
    strings_en = {
        "name": "YtbAudio",
        "searching": "<b><emoji document_id=5874960879434338403>🔎</emoji> Searching track on YouTube...</b>",
        "downloading": "<b><emoji document_id=6005843436479975944>🔁</emoji> Downloading audio...</b>",
        "no_query": "<b><emoji document_id=5778527486270770928>❌</emoji> Please specify track name or YouTube URL</b>",
        "error": "<b><emoji document_id=5778527486270770928>❌</emoji> Error occurred while downloading. Try another query.</b>",
        "processing": "<b><emoji document_id=5877260593903177342>⚙</emoji> Processing request...</b>",
        "found": "<b><emoji document_id=5776375003280838798>✅</emoji> Found: </b><code>{}</code>\n<b><emoji document_id=5879770735999717115>👤</emoji> Author: </b><code>{}</code>",
        "sending": "<b><emoji document_id=5877540355187937244>📤</emoji> Sending track...</b>"
    }

    def __init__(self):
        self.bot_username = "@YtbAudioBot"
        self.name = self.strings["name"]

    async def extract_video_id(self, url):
        """Извлечение ID видео из разных форматов ссылок YouTube и YouTube Music"""
        # Первый метод: через urlparse для обработки всех возможных параметров
        parsed_url = urlparse(url)
        
        # Обработка youtu.be ссылок
        if 'youtu.be' in parsed_url.netloc:
            path = parsed_url.path.strip('/')
            return path
            
        # Обработка стандартных youtube.com и music.youtube.com ссылок
        if 'youtube.com' in parsed_url.netloc or 'music.youtube.com' in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            
            # Проверка параметра v для watch ссылок
            if 'v' in query_params:
                return query_params['v'][0]
                
            # Проверка для других форматов (shorts, live и т.д.)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 2:
                if path_parts[0] in ['shorts', 'live', 'embed', 'v']:
                    return path_parts[1]
        
        # Второй метод: использование регулярных выражений как резервный вариант
        patterns = [
            r'youtu\.be\/([^\/\?\&]+)',
            r'youtube\.com\/watch\?v=([^\/\?\&]+)',
            r'youtube\.com\/embed\/([^\/\?\&]+)',
            r'youtube\.com\/v\/([^\/\?\&]+)',
            r'youtube\.com\/shorts\/([^\/\?\&]+)',
            r'youtube\.com\/live\/([^\/\?\&]+)',
            r'youtube\.com\/attribution_link\?.*v%3D([^\/\?\&]+)',
            r'music\.youtube\.com\/watch\?v=([^\/\?\&]+)',
            r'music\.youtube\.com\/embed\/([^\/\?\&]+)',
            r'music\.youtube\.com\/v\/([^\/\?\&]+)',
            r'music\.youtube\.com\/shorts\/([^\/\?\&]+)',
            r'music\.youtube\.com\/live\/([^\/\?\&]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        return None

    async def search_youtube(self, query):
        """Поиск видео на YouTube и получение первой ссылки"""
        try:
            search_url = f"https://www.youtube.com/results?search_query={quote(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status != 200:
                        return None
                    html = await response.text()
            
            # Ищем видео ID в html
            video_ids = re.findall(r"watch\?v=(\S{11})", html)
            if not video_ids:
                # Пробуем альтернативный метод поиска
                alt_pattern = r'{"videoId":"(\S{11})"'
                alt_match = re.search(alt_pattern, html)
                if alt_match:
                    return f"https://www.youtube.com/watch?v={alt_match.group(1)}"
                return None
            
            return f"https://www.youtube.com/watch?v={video_ids[0]}"
        except Exception as e:
            self.logger.error(f"Error searching YouTube: {str(e)}")
            return None
    
    async def get_video_info(self, video_url):
        """Получение информации о видео через API"""
        try:
            video_id = await self.extract_video_id(video_url)
            if not video_id:
                return "Неизвестное название", "Неизвестный автор"
                
            # Используем API-эндпоинт для извлечения информации о видео
            api_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            title = data.get('title', 'Неизвестное название')
                            author = data.get('author_name', 'Неизвестный автор')
                            return title, author
                        except json.JSONDecodeError:
                            # Если ответ не в формате JSON, переходим к запасному варианту
                            pass
            
            # Запасной вариант: получаем информацию напрямую из HTML страницы
            video_page_url = f"https://www.youtube.com/watch?v={video_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(video_page_url, headers=headers) as response:
                    if response.status != 200:
                        return "Неизвестное название", "Неизвестный автор"
                    html = await response.text()
            
            # Более надежные регулярные выражения для извлечения информации
            title_patterns = [
                r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
                r'<title>([^<]+)</title>',
                r'"title":"([^"]+)"'
            ]
            
            author_patterns = [
                r'<link\s+itemprop="name"\s+content=["\']([^"\']+)["\']',
                r'<meta\s+name=["\']author["\']\s+content=["\']([^"\']+)["\']',
                r'"ownerChannelName":"([^"]+)"',
                r'"author":"([^"]+)"'
            ]
            
            title = "Неизвестное название"
            for pattern in title_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    title = match.group(1)
                    break
            
            author = "Неизвестный автор"
            for pattern in author_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    author = match.group(1)
                    break
            
            # Очищаем название от "- YouTube" если есть
            title = re.sub(r'\s*-\s*YouTube\s*$', '', title)
            
            return title, author
            
        except Exception as e:
            self.logger.error(f"Error getting video info: {str(e)}")
            return "Неизвестное название", "Неизвестный автор"

    @loader.unrestricted
    @loader.ratelimit
    async def ytbcmd(self, message):
        """[YouTube URL или название трека] - Загрузить аудио с YouTube"""
        query = utils.get_args_raw(message)
        if not query:
            return await utils.answer(message, self.strings["no_query"])
        
        status_msg = await utils.answer(message, self.strings["processing"])
        
        try:
            # Улучшенное определение YouTube URL с поддержкой YouTube Music
            is_youtube_url = re.match(r'(https?://)?(www\.)?(youtube\.com|music\.youtube\.com|youtu\.be)/.+', query)
            
            if not is_youtube_url:
                await utils.answer(status_msg, self.strings["searching"])
                youtube_url = await self.search_youtube(query)
                if not youtube_url:
                    return await utils.answer(status_msg, self.strings["error"])
            else:
                youtube_url = query
            
            # Проверяем извлечение ID видео
            video_id = await self.extract_video_id(youtube_url)
            if not video_id:
                return await utils.answer(status_msg, self.strings["error"])
                
            # Нормализуем URL для отправки боту
            normalized_url = f"https://www.youtube.com/watch?v={video_id}"
            
            title, author = await self.get_video_info(youtube_url)
            await utils.answer(status_msg, self.strings["found"].format(title, author))
            
            await utils.answer(status_msg, self.strings["downloading"])
            
            sent_messages = []  # Список для хранения ID сообщений, которые нужно удалить
            
            async with message.client.conversation(self.bot_username) as conv:
                # Отправляем запрос боту и сохраняем ID сообщения
                bot_request = await conv.send_message(normalized_url)
                sent_messages.append(bot_request)
                
                # Ждем и получаем первый ответ от бота
                try:
                    response = await conv.get_response(timeout=90)  # Увеличиваем timeout для больших файлов
                    sent_messages.append(response)
                    
                    # Проверяем есть ли медиа в сообщении
                    if response.media:
                        await utils.answer(status_msg, self.strings["sending"])
                        
                        caption = f"<emoji document_id=5891249688933305846>🎵</emoji> <b>{title}</b>\n<emoji document_id=5879770735999717115>👤</emoji> <b>{author}</b>\n\n<emoji document_id=5877465816030515018>🔗</emoji> <a href='{youtube_url}'>YouTube</a>"
                        
                        # Отправляем аудио пользователю
                        await message.client.send_file(
                            message.chat_id,
                            response.media,
                            caption=caption,
                            parse_mode='html'
                        )
                        
                        # Удаляем все сообщения в переписке с ботом
                        for msg in sent_messages:
                            try:
                                await msg.delete()
                            except Exception:
                                pass
                        
                        # Удаляем статусное сообщение
                        await status_msg.delete()
                        return
                except asyncio.TimeoutError:
                    # Если первый ответ не пришел вовремя, выходим с ошибкой
                    for msg in sent_messages:
                        try:
                            await msg.delete()
                        except Exception:
                            pass
                    return await utils.answer(status_msg, self.strings["error"])
                
                # Если в первом ответе нет медиа, ждем дополнительные сообщения
                for _ in range(5):
                    try:
                        response = await conv.get_response(timeout=30)
                        sent_messages.append(response)
                        
                        if response.media:
                            await utils.answer(status_msg, self.strings["sending"])
                            
                            caption = f"<emoji document_id=5891249688933305846>🎵</emoji> <b>{title}</b>\n<emoji document_id=5879770735999717115>👤</emoji> <b>{author}</b>\n\n<emoji document_id=5877465816030515018>🔗</emoji> <a href='{youtube_url}'>YouTube</a>"
                            
                            # Отправляем аудио пользователю
                            await message.client.send_file(
                                message.chat_id,
                                response.media,
                                caption=caption,
                                parse_mode='html'
                            )
                            
                            # Удаляем все сообщения в переписке с ботом
                            for msg in sent_messages:
                                try:
                                    await msg.delete()
                                except Exception:
                                    pass
                            
                            # Удаляем статусное сообщение
                            await status_msg.delete()
                            return
                    except asyncio.TimeoutError:
                        break
            
            # Если не удалось получить аудио, пытаемся удалить все отправленные сообщения
            for msg in sent_messages:
                try:
                    await msg.delete()
                except Exception:
                    pass
                    
            await utils.answer(status_msg, self.strings["error"])
            
        except Exception as e:
            self.logger.error(f"Error in ytbcmd: {str(e)}")
            await utils.answer(status_msg, f"{self.strings['error']}\n\n{str(e)}")
