# meta developer: @sunshinelzt
# meta pic: https://img.icons8.com/color/48/000000/youtube-music.png
# scope: hikka_only
# scope: hikka_min 1.0.0

import os
import re
import json
import asyncio
import aiohttp
import logging
import tempfile
from urllib.parse import urlparse, parse_qs, quote_plus

from telethon import events
from telethon.tl.types import DocumentAttributeAudio

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class YTMusicDLMod(loader.Module):
    """Модуль для скачивания музыки с YouTube"""
    
    strings = {
        "name": "YTMusicDL",
        "downloading": "<b><emoji document_id=5463107823946717464>🎵</emoji> <i>Скачиваю трек...</i></b>",
        "searching": "<b><emoji document_id=5231012545799666522>🔍</emoji> <i>Ищу</i> <code>{}</code> <i>на YouTube...</i></b>",
        "uploading": "<b><emoji document_id=5445355530111437729>📤</emoji> <i>Загружаю трек...</i></b>",
        "success": "<b><emoji document_id=5776375003280838798>✅</emoji> <i>Трек успешно загружен!</i></b>\n\n<b><emoji document_id=5891249688933305846>🎵</emoji> Название:</b> <code>{}</code>\n<b><emoji document_id=5879770735999717115>👤</emoji> Исполнитель:</b> <code>{}</code>\n<b><emoji document_id=5936170807716745162>🎛</emoji> Длительность:</b> <code>{}</code>",
        "error": "<b><emoji document_id=5210952531676504517>❌</emoji> <i>Произошла ошибка при скачивании:</i></b>\n\n<code>{}</code>",
        "no_results": "<b><emoji document_id=5210952531676504517>❌</emoji> <i>По запросу</i> <code>{}</code> <i>ничего не найдено</i></b>",
        "processing": "<b><emoji document_id=5341715473882955310>⚙️</emoji> <i>Обработка...</i></b>",
        "starting": "<b><emoji document_id=5188481279963715781>🚀</emoji> <i>Начинаю загрузку...</i></b>",
        "config_service": "Сервис для скачивания (y2mate, ytmp3)",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "service", "y2mate", lambda: self.strings["config_service"],
        )
    
    async def client_ready(self, client, db):
        """Вызывается при готовности клиента"""
        self.client = client
        self.db = db
        self.session = aiohttp.ClientSession()
    
    async def on_unload(self):
        """Вызывается при выгрузке модуля"""
        await self.session.close()
    
    @loader.owner
    @loader.command(ru_doc="[ссылка или название] - Скачать музыку с YouTube")
    async def yt(self, message):
        """[ссылка или название] - Скачать музыку с YouTube"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Укажите ссылку на видео или название трека")
            return
        
        status_message = await utils.answer(message, self.strings["starting"])
        
        youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?([^\s&]+)"
        youtube_music_regex = r"(?:https?:\/\/)?(?:www\.)?music\.youtube\.com\/watch\?v=([^\s&]+)"
        
        youtube_match = re.match(youtube_regex, args)
        youtube_music_match = re.match(youtube_music_regex, args)
        
        if youtube_match or youtube_music_match:
            video_url = args
            # Извлекаем ID видео
            if youtube_match:
                video_id = youtube_match.group(1)
            else:
                video_id = youtube_music_match.group(1)
            
            # Проверяем наличие параметров в URL и удаляем их
            if '?' in video_id:
                video_id = video_id.split('?')[0]

            await utils.answer(status_message, self.strings["downloading"])
        else:
            await utils.answer(status_message, self.strings["searching"].format(args))
            # Поиск видео по названию
            video_id = await self._search_youtube(args)
            if not video_id:
                await utils.answer(status_message, self.strings["no_results"].format(args))
                return
            video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        await utils.answer(status_message, self.strings["processing"])
        
        service = self.config["service"].lower()
        
        try:
            if service == "y2mate":
                result = await self._download_via_y2mate(video_id, status_message)
            elif service == "ytmp3":
                result = await self._download_via_ytmp3(video_id, status_message)
            else:
                # По умолчанию используем y2mate
                result = await self._download_via_y2mate(video_id, status_message)
            
            if not result:
                await utils.answer(status_message, self.strings["error"].format("Не удалось скачать трек"))
                return
            
            file_path, title, artist, duration = result
            
            await utils.answer(status_message, self.strings["uploading"])
            
            await self.client.send_file(
                message.chat_id,
                file_path,
                caption=self.strings["success"].format(title, artist, duration),
                reply_to=message.reply_to_msg_id if message.reply_to_msg_id else None,
                attributes=[
                    DocumentAttributeAudio(
                        duration=self._parse_duration(duration),
                        title=title,
                        performer=artist,
                    )
                ],
            )
            
            # Удаляем временный файл и сообщение о загрузке
            if os.path.exists(file_path):
                os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            await utils.answer(status_message, self.strings["error"].format(str(e)))
            return
    
    async def _search_youtube(self, query):
        """Поиск видео на YouTube по названию"""
        try:
            # Используем API поиска YouTube через rapidapi.com
            url = "https://youtube-search-results.p.rapidapi.com/youtube-search/"
            headers = {
                "X-RapidAPI-Key": "97dfc61813mshbbc2e7e25948efcp10fcc0jsn1ba92610f3e5",  # Бесплатный ключ для примера
                "X-RapidAPI-Host": "youtube-search-results.p.rapidapi.com"
            }
            params = {"q": query}
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    # Альтернативный метод, если API не работает
                    return await self._search_youtube_alternative(query)
                
                data = await response.json()
                if "videos" in data and data["videos"]:
                    return data["videos"][0]["id"]
                return None
        except:
            # Если что-то пошло не так, используем альтернативный метод
            return await self._search_youtube_alternative(query)
    
    async def _search_youtube_alternative(self, query):
        """Альтернативный метод поиска видео на YouTube"""
        try:
            search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            async with self.session.get(search_url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                
                # Ищем ID видео в HTML
                video_ids = re.findall(r"watch\?v=(\S{11})", html)
                if video_ids:
                    return video_ids[0]
                return None
        except Exception as e:
            logger.error(f"Ошибка альтернативного поиска: {e}")
            return None
    
    async def _download_via_y2mate(self, video_id, status_message):
        """Скачивание через сервис y2mate.com"""
        try:
            # Шаг 1: Анализ видео
            analyze_url = "https://www.y2mate.com/mates/analyzeV2/ajax"
            analyze_data = {
                "k_query": f"https://www.youtube.com/watch?v={video_id}",
                "k_page": "home",
                "hl": "en",
                "q_auto": 0
            }
            
            await utils.answer(status_message, "<b><emoji document_id=5341715473882955310>⚙️</emoji> <i>Анализ видео...</i></b>")
            
            async with self.session.post(analyze_url, data=analyze_data) as response:
                if response.status != 200:
                    return None
                
                analyze_result = await response.json()
                if not analyze_result.get("status") == "ok":
                    return None
                
                title = analyze_result.get("page", {}).get("title", "Unknown")
                vid = analyze_result.get("vid", "")
                
                if not vid:
                    return None
                
                # Получаем информацию об авторе
                artist = analyze_result.get("page", {}).get("a", "Unknown")
                
                # Получаем длительность
                duration_seconds = analyze_result.get("page", {}).get("t", 0)
                duration = self._format_duration(duration_seconds)
                
                # Шаг 2: Преобразуем видео в mp3
                await utils.answer(status_message, self.strings["downloading"])
                
                convert_url = "https://www.y2mate.com/mates/convertV2/index"
                
                # Находим ID формата MP3 320kbps или лучшего доступного
                mp3_formats = []
                for item in analyze_result.get("links", {}).get("mp3", []):
                    if item.get("f") == "mp3":
                        mp3_formats.append(item)
                
                if not mp3_formats:
                    return None
                
                # Сортируем по качеству и выбираем лучшее
                mp3_formats.sort(key=lambda x: int(x.get("q", "").replace("kbps", "")), reverse=True)
                best_format = mp3_formats[0]
                k = best_format.get("k", "")
                
                convert_data = {
                    "vid": vid,
                    "k": k
                }
                
                async with self.session.post(convert_url, data=convert_data) as convert_response:
                    if convert_response.status != 200:
                        return None
                    
                    convert_result = await convert_response.json()
                    if not convert_result.get("status") == "ok":
                        return None
                    
                    download_url = convert_result.get("dlink", "")
                    if not download_url:
                        return None
                    
                    # Шаг 3: Скачиваем файл
                    file_name = f"{title}.mp3"
                    temp_dir = os.path.join("downloads", "ytmusic")
                    os.makedirs(temp_dir, exist_ok=True)
                    file_path = os.path.join(temp_dir, file_name)
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                        "Referer": "https://www.y2mate.com/",
                    }
                    
                    async with self.session.get(download_url, headers=headers) as file_response:
                        if file_response.status != 200:
                            return None
                        
                        with open(file_path, 'wb') as f:
                            f.write(await file_response.read())
                    
                    return file_path, title, artist, duration
        except Exception as e:
            logger.error(f"Ошибка скачивания через y2mate: {e}")
            return None
    
    async def _download_via_ytmp3(self, video_id, status_message):
        """Скачивание через сервис ytmp3.cc"""
        try:
            # API URL
            api_url = "https://ytmp3.cc/uu/api/"
            params = {
                "id": video_id,
                "format": "mp3"
            }
            
            await utils.answer(status_message, "<b><emoji document_id=5341715473882955310>⚙️</emoji> <i>Подготовка к скачиванию...</i></b>")
            
            # Подготовка скачивания
            async with self.session.get(api_url, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if data.get("status") != "success":
                    return None
                
                title = data.get("title", "Unknown")
                download_url = data.get("download_url")
                duration = data.get("duration", "Unknown")
                
                if not download_url:
                    return None
                
                # Скачиваем файл
                await utils.answer(status_message, self.strings["downloading"])
                
                file_name = f"{title}.mp3"
                temp_dir = os.path.join("downloads", "ytmusic")
                os.makedirs(temp_dir, exist_ok=True)
                file_path = os.path.join(temp_dir, file_name)
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                }
                
                # Извлекаем имя артиста из названия (если возможно)
                artist = "Unknown"
                if " - " in title:
                    artist, title = title.split(" - ", 1)
                
                async with self.session.get(download_url, headers=headers) as file_response:
                    if file_response.status != 200:
                        return None
                    
                    with open(file_path, 'wb') as f:
                        f.write(await file_response.read())
                
                return file_path, title, artist, duration
        except Exception as e:
            logger.error(f"Ошибка скачивания через ytmp3: {e}")
            return None
    
    def _format_duration(self, seconds):
        """Форматирует продолжительность из секунд в строку"""
        if not seconds:
            return "Неизвестно"
        
        try:
            seconds = int(seconds)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        except:
            return "Неизвестно"
    
    def _parse_duration(self, duration_str):
        """Преобразует строку продолжительности в секунды"""
        if duration_str == "Неизвестно":
            return 0
        
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0
        except:
            return 0
