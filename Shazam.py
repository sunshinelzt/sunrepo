import io, tempfile, requests
from moviepy.editor import VideoFileClip
from youtubesearchpython import VideosSearch
from bs4 import BeautifulSoup
from ShazamAPI import Shazam
from urllib.parse import quote_plus
from .. import loader, utils

@loader.tds
class ShazamMod(loader.Module):
    """Shazam — Распознаёт трек с голосового, аудио или видео"""
    strings = {
        "name": "Shazam",
        "Downloading": "📥 Загружаю...",
        "Extracting": "🎧 Извлекаю звук...",
        "Searching": "🔎 Распознаю...",
        "no_reply": "Ответь на аудио, голосовое или видео.",
        "not_found": "🚫 Не удалось распознать.",
        "track_info": (
            "✨ <b>Трек найден:</b> <code>{}</code>\n\n"
            "<b>YouTube:</b> <a href=\"{}\">Слушать</a>\n"
            "<b>Spotify:</b> <a href=\"{}\">Слушать</a>\n"
            "<b>SoundCloud:</b> <a href=\"{}\">Слушать</a>"
        )
    }

    async def get_audio(self, reply, message):
        mime = reply.file.mime_type
        await utils.answer(message, self.strings["Downloading"])
        if mime.startswith("audio"):
            return io.BytesIO(await reply.download_media(bytes))
        elif mime.startswith("video"):
            with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video, tempfile.NamedTemporaryFile(suffix=".wav") as tmp_audio:
                await reply.download_media(tmp_video.name)
                await utils.answer(message, self.strings["Extracting"])
                VideoFileClip(tmp_video.name).subclip(0, 15).audio.write_audiofile(tmp_audio.name, codec="pcm_s16le", verbose=False, logger=None)
                return io.BytesIO(open(tmp_audio.name, "rb").read())
        return None

    async def search_youtube(self, query):
        try:
            return (await VideosSearch(query, 1).next())["result"][0]["link"]
        except:
            return "https://youtube.com"

    def search_spotify(self, query):
        try:
            r = requests.get(f"https://open.spotify.com/search/{quote_plus(query)}", headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                if "/track/" in a["href"]:
                    return "https://open.spotify.com" + a["href"]
        except:
            pass
        return "https://open.spotify.com"

    def search_soundcloud(self, query):
        try:
            r = requests.get(f"https://soundcloud.com/search?q={quote_plus(query)}", headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                if a["href"].startswith("/") and "/sets/" not in a["href"]:
                    return "https://soundcloud.com" + a["href"]
        except:
            pass
        return "https://soundcloud.com"

    @loader.command()
    async def sh(self, message):
        reply = await message.get_reply_message()
        if not reply or not reply.file:
            return await utils.answer(message, self.strings["no_reply"])

        audio = await self.get_audio(reply, message)
        if not audio:
            return await utils.answer(message, self.strings["no_reply"])

        await utils.answer(message, self.strings["Searching"])
        try:
            shazam = Shazam(audio.read())
            track = next(shazam.recognizeSong())[1]["track"]
            title = track.get("share", {}).get("subject", "Неизвестно")

            yt = await self.search_youtube(title)
            sp = self.search_spotify(title)
            sc = self.search_soundcloud(title)

            await utils.answer(message, self.strings["track_info"].format(title, yt, sp, sc))
        except:
            await utils.answer(message, self.strings["not_found"])
