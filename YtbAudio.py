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
                
        # Если стандартные шаблоны не сработали, пробуем через urlparse
        parsed_url = urlparse(url)
        if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
            if parsed_url.netloc == 'youtu.be':
                return parsed_url.path.lstrip('/')
            if parsed_url.path == '/watch':
                query = parse_qs(parsed_url.query)
                if 'v' in query:
                    return query['v'][0]
                    
        return None

    async def search_youtube(self, query):
        """Поиск видео на YouTube и получение первой ссылки"""
        search_url = f"https://www.youtube.com/results?search_query={quote(query)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                html = await response.text()
        
        video_ids = re.findall(r"watch\?v=(\S{11})", html)
        if not video_ids:
            return None
        
        return f"https://www.youtube.com/watch?v={video_ids[0]}"
    
    async def get_video_info(self, video_url):
        """Получение информации о видео через API"""
        try:
            video_id = await self.extract_video_id(video_url)
            if not video_id:
                return "Неизвестное название", "Неизвестный автор"
                
            # Используем API-эндпоинт для извлечения информации о видео
            api_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        title = data.get('title', 'Неизвестное название')
                        author = data.get('author_name', 'Неизвестный автор')
                        return title, author
                    
            # Если API не сработал, пробуем старый метод (запасной вариант)
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    html = await response.text()
                    
            title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            author_match = re.search(r'<link\s+itemprop="name"\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            
            if not author_match:
                author_match = re.search(r'<meta\s+name=["\']author["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            
            title = title_match.group(1) if title_match else "Неизвестное название"
            author = author_match.group(1) if author_match else "Неизвестный автор"
            
            return title, author
            
        except Exception as e:
            return f"Название трека (Ошибка: {str(e)[:30]}...)", "Неизвестный автор"

    @loader.unrestricted
    @loader.ratelimit
    async def ytbcmd(self, message):
        """[YouTube URL или название трека] - Загрузить аудио с YouTube"""
        query = utils.get_args_raw(message)
        if not query:
            return await utils.answer(message, self.strings["no_query"])
        
        status_msg = await utils.answer(message, self.strings["processing"])
        
        try:
            is_youtube_url = re.match(r'(https?://)?(www\.)?(youtube\.com|music\.youtube\.com|youtu\.be)/.+', query)
            
            if not is_youtube_url:
                await utils.answer(status_msg, self.strings["searching"])
                youtube_url = await self.search_youtube(query)
                if not youtube_url:
                    return await utils.answer(status_msg, self.strings["error"])
            else:
                youtube_url = query
            
            title, author = await self.get_video_info(youtube_url)
            await utils.answer(status_msg, self.strings["found"].format(title, author))
            
            await utils.answer(status_msg, self.strings["downloading"])
            
            sent_messages = []  # Список для хранения ID сообщений, которые нужно удалить
            
            async with message.client.conversation(self.bot_username) as conv:
                # Отправляем запрос боту и сохраняем ID сообщения
                bot_request = await conv.send_message(youtube_url)
                sent_messages.append(bot_request)
                
                # Ждем и получаем первый ответ от бота
                response = await conv.get_response(timeout=60)
                sent_messages.append(response)
                
                # Проверяем есть ли медиа в сообщении
                if response.audio or response.document or response.media:
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
                        except:
                            pass
                    
                    # Удаляем статусное сообщение
                    await status_msg.delete()
                    return
                
                # Если в первом ответе нет медиа, ждем дополнительные сообщения
                for _ in range(5):
                    try:
                        response = await conv.get_response(timeout=30)
                        sent_messages.append(response)
                        
                        if response.audio or response.document or response.media:
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
                                except:
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
                except:
                    pass
                    
            await utils.answer(status_msg, self.strings["error"])
            
        except Exception as e:
            await utils.answer(status_msg, f"{self.strings['error']}\n\n{str(e)}")
