# meta dev: @sunshinelzt

import logging
import asyncio
from .. import loader, utils
from telethon.tl.custom import Message

logger = logging.getLogger("LoliHentai")

RESPONSE_TIMEOUT = 10


@loader.tds
class Photo(loader.Module):
    """Лучший источник лолек"""

    strings = {
        "name": "LoliHentai",
        "loading": (
            "<emoji document_id=5215327832040811010>⏳</emoji>"
            " <b>Загружаю твою лольку...</b>"
        ),
        "no_photo": (
            "<emoji document_id=5282195959215807315>❌</emoji>"
            " <b>Бот не вернул лольку.</b> Попробуй позже."
        ),
        "error": (
            "<emoji document_id=5282195959215807315>❌</emoji> <b>Ошибка!</b>\n\n"
            "<emoji document_id=5796440171364749940>📌</emoji>"
            " Проверь, не заблокирован ли @ferganteusbot\n"
            "<emoji document_id=5796440171364749940>📌</emoji>"
            " Попробуй позже, возможно бот временно недоступен"
        ),
        "timeout": (
            "<emoji document_id=5282195959215807315>❌</emoji>"
            " <b>Таймаут!</b> Бот не ответил вовремя."
        ),
    }

    async def lolicmd(self, message: Message):
        """Получить случайную лольку"""
        status = await utils.answer(message, self.strings("loading"))

        request = None
        response = None

        try:
            async with self._client.conversation("@ferganteusbot") as conv:
                request = await conv.send_message("/lh")
                response = await asyncio.wait_for(
                    conv.get_response(), timeout=RESPONSE_TIMEOUT
                )

                if not response.photo:
                    await utils.answer(status, self.strings("no_photo"))
                    return

                photo_bytes = await response.download_media(file=bytes)

                await message.client.send_file(
                    message.peer_id,
                    photo_bytes,
                    reply_to=message.reply_to_msg_id,
                )

        except asyncio.TimeoutError:
            logger.warning("[LoliHentai] Таймаут ожидания ответа от бота")
            await utils.answer(status, self.strings("timeout"))
            return

        except Exception as e:
            logger.error("[LoliHentai] Ошибка: %s", e, exc_info=True)
            await utils.answer(status, self.strings("error"))
            return

        finally:
            to_delete = [msg for msg in (request, response, message, status) if msg]
            if to_delete:
                await asyncio.gather(
                    *(msg.delete() for msg in to_delete), return_exceptions=True
                )
