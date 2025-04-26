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
import random
import time
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
        "analyzing": "<b><emoji document_id=5341715473882955310>⚙️</emoji> <i>Анализ видео...</i></b>",
        "service_error": "<b><emoji document_id=5210952531676504517>❌</emoji> <i>Сервис</i> <code>{}</code> <i>не смог обработать запрос. Пробую другой сервис...</i></b>",
        "config_service": "Сервис для скачивания (savefrom, y2down, notube, auto)",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "service", "auto", lambda: self.strings["config_service"],
        )
    
    async def client_ready(self, client, db):
        """Вызывается при готовности клиента"""
        self.client = client
        self.db = db
        self.session = aiohttp.ClientSession()
        # Добавляем случайные User-Agent для обхода блокировок
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"
        ]
    
    async def on_unload(self):
        """Вызывается при выгрузке модуля"""
        await self.session.close()
    
    def _get_random_user_agent(self):
        """Возвращает случайный User-Agent из списка"""
        return random.choice(self.user_agents)
    
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
        result = None
        
        try:
            # Определяем порядок попытки сервисов
            services_to_try = []
            if service == "auto":
                # Пробуем все сервисы в определенном порядке
                services_to_try = ["savefrom", "y2down", "notube"]
            else:
                # Сначала пробуем выбранный сервис, затем остальные
                services_to_try = [service]
                for s in ["savefrom", "y2down", "notube"]:
                    if s != service:
                        services_to_try.append(s)
            
            # Поочередно пробуем каждый сервис
            for current_service in services_to_try:
                try:
                    await utils.answer(status_message, f"<b><emoji document_id=5341715473882955310>⚙️</emoji> <i>Загрузка через {current_service}...</i></b>")
                    
                    if current_service == "savefrom":
                        result = await self._download_via_savefrom(video_id, video_url, status_message)
                    elif current_service == "y2down":
                        result = await self._download_via_y2down(video_id, video_url, status_message)
                    elif current_service == "notube":
                        result = await self._download_via_notube(video_id, video_url, status_message)
                    
                    if result:
                        # Если сервис успешно скачал файл, останавливаем цикл
                        break
                    else:
                        # Если сервис не смог скачать, сообщаем и пробуем следующий
                        await utils.answer(status_message, self.strings["service_error"].format(current_service))
                except Exception as e:
                    logger.error(f"Ошибка при загрузке с {current_service}: {e}")
                    await utils.answer(status_message, self.strings["service_error"].format(current_service))
                    # Немного подождем перед следующей попыткой
                    await asyncio.sleep(1)
            
            if not result:
                await utils.answer(status_message, self.strings["error"].format("Ни один из сервисов не смог скачать трек"))
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
            search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            
            headers = {
                "User-Agent": self._get_random_user_agent(),
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
            logger.error(f"Ошибка поиска на YouTube: {e}")
            return None
    
    async def _download_via_savefrom(self, video_id, video_url, status_message):
        """Скачивание через сервис savefrom.net"""
        try:
            await utils.answer(status_message, self.strings["analyzing"])
            
            api_url = "https://ssyoutube.com/api/convert"
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://ssyoutube.com",
                "Referer": "https://ssyoutube.com/",
            }
            
            data = {
                "url": video_url
            }
            
            async with self.session.post(api_url, headers=headers, json=data) as response:
                if response.status != 200:
                    return None
                
                result = await response.json()
                if not result or "url" not in result:
                    return None
                
                # Получаем информацию о видео
                title = result.get("meta", {}).get("title", "Unknown")
                duration_seconds = result.get("meta", {}).get("duration")
                duration = self._format_duration(duration_seconds)
                
                # Извлекаем имя артиста
                artist = "Unknown"
                if " - " in title:
                    parts = title.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip() if len(parts) > 1 else title
                
                # Ищем аудио форматы (отсортированные по качеству)
                audio_formats = []
                for item in result.get("url", []):
                    if item.get("audio") and not item.get("video"):
                        audio_formats.append(item)
                
                if not audio_formats:
                    return None
                
                # Сортируем по качеству и выбираем лучшее
                audio_formats.sort(key=lambda x: int(x.get("quality", "").replace("kbps", "").strip()) if x.get("quality") else 0, reverse=True)
                best_format = audio_formats[0]
                download_url = best_format.get("url")
                
                if not download_url:
                    return None
                
                # Скачиваем файл
                await utils.answer(status_message, self.strings["downloading"])
                
                file_name = f"{title} - {artist}.mp3"
                # Заменяем недопустимые символы в имени файла
                file_name = re.sub(r'[\\/*?:"<>|]', "", file_name)
                temp_dir = os.path.join("downloads", "ytmusic")
                os.makedirs(temp_dir, exist_ok=True)
                file_path = os.path.join(temp_dir, file_name)
                
                download_headers = {
                    "User-Agent": self._get_random_user_agent(),
                    "Referer": "https://ssyoutube.com/",
                }
                
                async with self.session.get(download_url, headers=download_headers) as file_response:
                    if file_response.status != 200:
                        return None
                    
                    with open(file_path, 'wb') as f:
                        f.write(await file_response.read())
                
                return file_path, title, artist, duration
        except Exception as e:
            logger.error(f"Ошибка скачивания через savefrom: {e}")
            return None
    
    async def _download_via_y2down(self, video_id, video_url, status_message):
        """Скачивание через сервис y2down.cc"""
        try:
            await utils.answer(status_message, self.strings["analyzing"])
            
            # Сначала получаем токен
            init_url = "https://y2down.cc/"
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            # Делаем первый запрос для получения cookie и CSRF токена
            async with self.session.get(init_url, headers=headers) as init_response:
                if init_response.status != 200:
                    return None
                
                html = await init_response.text()
                
                # Ищем CSRF токен в HTML
                csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
                if not csrf_match:
                    return None
                
                csrf_token = csrf_match.group(1)
                
                # Сохраняем cookies из первого запроса
                cookies = init_response.cookies
            
            # Делаем запрос на анализ видео
            api_url = "https://y2down.cc/analyze"
            api_headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRF-TOKEN": csrf_token,
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://y2down.cc",
                "Referer": "https://y2down.cc/",
            }
            
            data = {
                "url": video_url
            }
            
            async with self.session.post(api_url, headers=api_headers, data=data, cookies=cookies) as response:
                if response.status != 200:
                    return None
                
                try:
                    result = await response.json()
                except:
                    return None
                
                if not result or "status" not in result or result["status"] != "success":
                    return None
                
                data = result.get("data", {})
                
                # Получаем информацию о видео
                title = data.get("title", "Unknown")
                video_data = data.get("video", {})
                duration_text = video_data.get("duration", "0:00")
                
                # Извлекаем имя артиста
                artist = "Unknown"
                if " - " in title:
                    parts = title.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip() if len(parts) > 1 else title
                
                # Ищем аудио форматы
                audio_formats = data.get("audio", [])
                if not audio_formats:
                    return None
                
                # Находим формат mp3 с наилучшим качеством
                best_format = None
                for format in audio_formats:
                    if format.get("ext") == "mp3":
                        if not best_format or int(format.get("quality", "0").replace("kbps", "")) > int(best_format.get("quality", "0").replace("kbps", "")):
                            best_format = format
                
                if not best_format:
                    # Если mp3 не найден, берем любой первый аудио формат
                    best_format = audio_formats[0]
                
                download_url = best_format.get("url")
                
                if not download_url:
                    return None
                
                # Скачиваем файл
                await utils.answer(status_message, self.strings["downloading"])
                
                file_name = f"{title} - {artist}.mp3"
                # Заменяем недопустимые символы в имени файла
                file_name = re.sub(r'[\\/*?:"<>|]', "", file_name)
                temp_dir = os.path.join("downloads", "ytmusic")
                os.makedirs(temp_dir, exist_ok=True)
                file_path = os.path.join(temp_dir, file_name)
                
                download_headers = {
                    "User-Agent": self._get_random_user_agent(),
                    "Referer": "https://y2down.cc/",
                }
                
                async with self.session.get(download_url, headers=download_headers) as file_response:
                    if file_response.status != 200:
                        return None
                    
                    with open(file_path, 'wb') as f:
                        f.write(await file_response.read())
                
                return file_path, title, artist, duration_text
        except Exception as e:
            logger.error(f"Ошибка скачивания через y2down: {e}")
            return None
    
    async def _download_via_notube(self, video_id, video_url, status_message):
        """Скачивание через сервис notube.net"""
        try:
            await utils.answer(status_message, self.strings["analyzing"])
            
            # Первый запрос для получения токена и куки
            init_url = "https://notube.net/ru/youtube-app-v36"
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            async with self.session.get(init_url, headers=headers) as init_response:
                if init_response.status != 200:
                    return None
                
                html = await init_response.text()
                
                # Ищем токен в HTML
                token_match = re.search(r'var\s+token\s*=\s*["\']([^"\']+)["\']', html)
                if not token_match:
                    return None
                
                token = token_match.group(1)
                
                # Сохраняем cookies
                cookies = init_response.cookies
            
            # Запрос на анализ видео
            api_url = "https://notube.net/api/v1/analyze"
            api_headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://notube.net",
                "Referer": "https://notube.net/ru/youtube-app-v36",
                "X-Requested-With": "XMLHttpRequest",
            }
            
            api_data = {
                "url": video_url,
                "token": token,
                "lang": "ru"
            }
            
            # Генерируем уникальный идентификатор для отслеживания задачи
            task_id = f"{int(time.time())}{random.randint(1000, 9999)}"
            
            async with self.session.post(api_url, headers=api_headers, json=api_data, cookies=cookies) as response:
                if response.status != 200:
                    return None
                
                try:
                    result = await response.json()
                except:
                    return None
                
                if not result or "data" not in result:
                    return None
                
                data = result.get("data", {})
                
                # Получаем информацию о видео
                title = data.get("title", "Unknown")
                duration_seconds = data.get("duration", 0)
                duration = self._format_duration(duration_seconds)
                
                # Извлекаем имя артиста
                artist = "Unknown"
                if " - " in title:
                    parts = title.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip() if len(parts) > 1 else title
                
                # Ищем аудио форматы
                formats = data.get("formats", [])
                audio_formats = [f for f in formats if f.get("type") == "audio" and "mp3" in f.get("format", "").lower()]
                
                if not audio_formats:
                    return None
                
                # Сортируем по качеству
                audio_formats.sort(key=lambda x: int(re.search(r'(\d+)\s*kbps', x.get("format", "0 kbps")).group(1)) if re.search(r'(\d+)\s*kbps', x.get("format", "0 kbps")) else 0, reverse=True)
                
                best_format = audio_formats[0]
                format_id = best_format.get("id")
                
                if not format_id:
                    return None
                
                # Запрос на конвертацию
                convert_url = "https://notube.net/api/v1/convert"
                convert_data = {
                    "id": data.get("id"),
                    "format": format_id,
                    "taskId": task_id,
                    "title": title,
                    "token": token
                }
                
                async with self.session.post(convert_url, headers=api_headers, json=convert_data, cookies=cookies) as convert_response:
                    if convert_response.status != 200:
                        return None
                    
                    try:
                        convert_result = await convert_response.json()
                    except:
                        return None
                    
                    if not convert_result or "data" not in convert_result:
                        return None
                    
                    convert_data = convert_result.get("data", {})
                    download_url = convert_data.get("url")
                    
                    if not download_url:
                        # Если URL нет сразу, пробуем проверить статус конвертации
                        await utils.answer(status_message, "<b><emoji document_id=5341715473882955310>⚙️</emoji> <i>Ожидание конвертации...</i></b>")
                        
                        status_url = f"https://notube.net/api/v1/task/{task_id}/status"
                        
                        # Пробуем до 10 раз с интервалом в 3 секунды
                        for _ in range(10):
                            await asyncio.sleep(3)
                            
                            async with self.session.get(status_url, headers=api_headers, cookies=cookies) as status_response:
                                if status_response.status != 200:
                                    continue
                                
                                try:
                                    status_result = await status_response.json()
                                    if status_result.get("data", {}).get("status") == "processed":
                                        # Получаем готовую ссылку
                                        download_url = status_result.get("data", {}).get("url")
                                        if download_url:
                                            break
                                except:
                                    continue
                    
                    if not download_url:
                        return None
                    
                    # Скачиваем файл
                    await utils.answer(status_message, self.strings["downloading"])
                    
                    file_name = f"{title} - {artist}.mp3"
                    # Заменяем недопустимые символы в имени файла
                    file_name = re.sub(r'[\\/*?:"<>|]', "", file_name)
                    temp_dir = os.path.join("downloads", "ytmusic")
                    os.makedirs(temp_dir, exist_ok=True)
                    file_path = os.path.join(temp_dir, file_name)
                    
                    download_headers = {
                        "User-Agent": self._get_random_user_agent(),
                        "Referer": "https://notube.net/",
                    }
                    
                    async with self.session.get(download_url, headers=download_headers) as file_response:
                        if file_response.status != 200:
                            return None
                        
                        with open(file_path, 'wb') as f:
                            f.write(await file_response.read())
                    
                    return file_path, title, artist, duration
        except Exception as e:
            logger.error(f"Ошибка скачивания через notube: {e}")
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
