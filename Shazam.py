# requires: ShazamAPI, moviepy

import io
import tempfile
from moviepy.editor import VideoFileClip
from ShazamAPI import Shazam
from urllib.parse import quote_plus
from .. import loader, utils

@loader.tds
class ShazamMod(loader.Module):
    """Распознавание трека по аудио или видео через Shazam"""
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

    @loader.command(ru_doc="Ответь на аудио, голосовое или видео — я распознаю трек")
    async def sh(self, message):
        """Распознаёт трек по аудио/видео сообщению"""
        audio_data, reply = await self.get_audio_data(message)
        if not audio_data:
            return

        try:
            shazam = Shazam(audio_data.read())
            recog = next(shazam.recognizeSong())[1]["track"]

            title = recog.get("share", {}).get("subject", "Без названия")
            image = recog.get("images", {}).get("background")

            # Получение ссылок от Shazam
            hub = recog.get("hub", {})
            providers = hub.get("providers", [])
            options = hub.get("options", [])

            yt_link = next((p.get("actions", [{}])[0].get("uri") for p in providers if p.get("type") == "youtube"), None)
            sp_link = next((p.get("actions", [{}])[0].get("uri") for p in providers if p.get("type") == "spotify"), None)
            sc_link = next((o.get("actions", [{}])[0].get("uri") for o in options if o.get("caption", "").lower() == "soundcloud"), None)

            # Поиск вручную, если Shazam не дал ссылку
            query = quote_plus(title)
            if not yt_link:
                yt_link = f"https://www.youtube.com/results?search_query={query}"
            if not sp_link:
                sp_link = f"https://open.spotify.com/search/{query}"
            if not sc_link:
                sc_link = f"https://soundcloud.com/search?q={query}"

            # Финальные строки
            yt_str = self.strings["youtube"].format(yt_link)
            sp_str = self.strings["spotify"].format(sp_link)
            sc_str = self.strings["soundcloud"].format(sc_link)

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
