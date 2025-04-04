# requires: ShazamAPI, moviepy, youtube-search-python, beautifulsoup4, requests
import io
import tempfile
import requests
from bs4 import BeautifulSoup
from moviepy.editor import VideoFileClip
from ShazamAPI import Shazam
from urllib.parse import quote_plus
from youtubesearchpython import VideosSearch
from .. import loader, utils

@loader.tds
class ShazamMod(loader.Module):
    """Распознавание трека по аудио или видео с умным поиском ссылок"""
    strings = {
        "name": "Shazam",
        "Downloading": "📥 <b>Загружаю файл...</b>",
        "Extracting": "🎧 <b>Извлекаю аудио из видео...</b>",
        "Searching": "🔎 <b>Распознаю трек...</b>",
        "no_reply": "🎙 <b>Ответь на аудио, голосовое или видео сообщение.</b>",
        "not_found": "🚫 <b>Не удалось распознать трек.</b>",
        "track_info": (
            "✨ <b>Трек найден!</b>\n\n"
            "<b>Название:</b> <code>{}</code>\n\n"
            "{}{}{}"
        ),
        "youtube": "<b>YouTube:</b> <a href=\"{}\">Слушать</a>\n",
        "spotify": "<b>Spotify:</b> <a href=\"{}\">Слушать</a>\n",
        "soundcloud": "<b>SoundCloud:</b> <a href=\"{}\">Слушать</a>\n",
        "not_found_link": "<b>{}:</b> <i>Не найдено</i>\n"
    }

    async def get_audio_data(self, message):
        reply = await message.get_reply_message()
        if not (reply and reply.file and reply.file.mime_type):
            await utils.answer(message, self.strings["no_reply"])
            return None, None

        mime = reply.file.mime_type

        if mime.startswith("audio"):
            await utils.answer(message, self.strings["Downloading"])
            audio = io.BytesIO(await reply.download_media(bytes))
            await utils.answer(message, self.strings["Searching"])
            return audio, reply

        elif mime.startswith("video"):
            await utils.answer(message, self.strings["Downloading"])
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
                await reply.download_media(temp_video.name)
                await utils.answer(message, self.strings["Extracting"])

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                    try:
                        clip = VideoFileClip(temp_video.name).subclip(0, 15)
                        clip.audio.write_audiofile(temp_audio.name, codec="pcm_s16le", verbose=False, logger=None)
                        with open(temp_audio.name, "rb") as f:
                            audio_data = io.BytesIO(f.read())
                        await utils.answer(message, self.strings["Searching"])
                        return audio_data, reply
                    except Exception:
                        return None, None

        await utils.answer(message, self.strings["no_reply"])
        return None, None

    async def search_youtube(self, query):
        try:
            results = VideosSearch(query, limit=1)
            video = (await results.next())['result'][0]
            return video['link']
        except:
            return None

    def search_spotify(self, query):
        try:
            url = f"https://open.spotify.com/search/{quote_plus(query)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a['href']
                if "/track/" in href:
                    return f"https://open.spotify.com{href}"
        except:
            return None

    def search_soundcloud(self, query):
        try:
            url = f"https://soundcloud.com/search?q={quote_plus(query)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a['href']
                if href.startswith("/") and "/sets/" not in href:
                    return f"https://soundcloud.com{href}"
        except:
            return None

    @loader.command(ru_doc="Ответь на аудио, голосовое или видео — я распознаю трек и найду ссылки")
    async def sh(self, message):
        """Распознаёт трек и ищет первые совпадения на YouTube, Spotify, SoundCloud"""
        audio_data, reply = await self.get_audio_data(message)
        if not audio_data:
            return

        try:
            shazam = Shazam(audio_data.read())
            recog = next(shazam.recognizeSong())[1]["track"]

            title = recog.get("share", {}).get("subject", "Без названия")
            image = recog.get("images", {}).get("background")

            yt_link = await self.search_youtube(title) or self.strings["not_found_link"].format("YouTube")
            sp_link = self.search_spotify(title) or self.strings["not_found_link"].format("Spotify")
            sc_link = self.search_soundcloud(title) or self.strings["not_found_link"].format("SoundCloud")

            yt_str = self.strings["youtube"].format(yt_link) if yt_link.startswith("http") else yt_link
            sp_str = self.strings["spotify"].format(sp_link) if sp_link.startswith("http") else sp_link
            sc_str = self.strings["soundcloud"].format(sc_link) if sc_link.startswith("http") else sc_link

            caption = self.strings["track_info"].format(
                utils.escape_html(title),
                yt_str, sp_str, sc_str
            )

            await self.client.send_file(
                message.peer_id,
                file=image if image else None,
                caption=caption,
                reply_to=reply.id,
                parse_mode="html"
            )
            await message.delete()

        except Exception:
            await utils.answer(message, self.strings["not_found"])
