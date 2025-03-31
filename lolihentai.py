# meta developer: @sunshinelzt

import logging
import asyncio
from .. import loader, utils
from telethon.tl.custom import Message

logger = logging.getLogger("LoliHentai")

@loader.tds
class LoliHentai(loader.Module):
    """Лучший источник лолек"""

    strings = {
        "name": "LoliHentai",
        "loading_photo": "<emoji document_id=5215327832040811010>⏳</emoji> <b>Загружаю твою няшку...</b>",
        "error_loading": (
            "<emoji document_id=5282195959215807315>❌</emoji> <b>Ошибка!</b>\n\n"
            "<emoji document_id=5796440171364749940>📌</emoji> Проверь, не заблокирован ли @ferganteusbot\n"
            "<emoji document_id=5796440171364749940>📌</emoji> Попробуй позже, возможно, бот временно недоступен"
        ),
        "send_message_with_photo": "<emoji document_id=5215327832040811010>⏳</emoji> <b>Отправляю твою няшку...</b>",
        "photo_sent": "<emoji document_id=6046253808810464426>💃</emoji> Держи свою лольку!",
    }

    def __init__(self):
        self.hidden_image = False
        self._last_status_message = None

    async def lolicmd(self, message: Message):
        """Получить случайную лольку"""
        self._last_status_message = await utils.answer(message, self.strings("loading_photo"))

        async with self._client.conversation("@ferganteusbot") as conv:
            try:
                request = await conv.send_message("/lh")
                response = await conv.get_response()

                if response.photo:
                    downloaded_photo = await response.download()

                    await utils.answer(message, self.strings("send_message_with_photo"))

                    sent_message = await message.client.send_message(
                        message.peer_id,
                        caption=self.strings("photo_sent"),
                        file=downloaded_photo,
                        reply_to=message.reply_to_msg_id,
                        blurred=self.hidden_image
                    )

                    if self._last_status_message:
                        await self._last_status_message.delete()

                await asyncio.gather(
                    request.delete(),
                    response.delete(),
                    message.delete(),
                )

            except Exception as e:
                logger.error(f"[] Ошибка при загрузке: {e}")
                await utils.answer(message, self.strings("error_loading"))

    @loader.command()
    async def toggleimagecmd(self, message: Message):
        """Переключить блюр изображения"""
        self.hidden_image = not self.hidden_image
        state = "включено" if self.hidden_image else "выключено"
        await utils.answer(message, f"Блюр изображения теперь {state}.")
