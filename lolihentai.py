# meta developer: @sunshinelzt

import logging
import asyncio
from .. import loader, utils
from telethon.tl.custom import Message

logger = logging.getLogger("LoliHentai")

@loader.tds
class LoliHentai(loader.Module):
    """Лучший источник лоли"""

    strings = {
        "name": "LoliHentai",
        "loading_photo": "<emoji document_id=5215327832040811010>⏳</emoji> <b>Загружаю твою лолю...</b>",
        "error_loading": (
            "<emoji document_id=5282195959215807315>❌</emoji> <b>Ошибка!</b>\n\n"
            "<emoji document_id=5796440171364749940>📌</emoji> <b>Проверь, не заблокирован ли @ferganteusbot</b)\n"
            "<emoji document_id=5796440171364749940>📌</emoji> <b>Попробуй позже, возможно, бот временно недоступен</b>"
        ),
    }

    async def lolicmd(self, message: Message):
        """Получить случайное лоли-фото"""
        status = await utils.answer(message, self.strings("loading_photo"))

        async with self._client.conversation("@ferganteusbot") as conv:
            try:
                request = await conv.send_message("/lh")
                response = await conv.get_response()

                if response.photo:
                    await message.client.send_file(
                        message.peer_id,
                        response.photo,
                        caption="<emoji document_id=5339156929656582222>✨</emoji> <b>Вот твоя лоля!</b>",
                        reply_to=message.reply_to_msg_id,
                    )

                await asyncio.gather(
                    request.delete(),
                    response.delete(),
                    message.delete(),
                    status.delete()
                )

            except Exception as e:
                logger.error(f"[LoliHentai] Ошибка: {e}")
                await utils.answer(message, self.strings("error_loading"))
