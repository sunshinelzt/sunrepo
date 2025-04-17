from .. import loader, utils
import os
import re

__version__ = (1, 4, 8, 8)
# meta developer: @sunshinelzt
# о боже, какой же саншайн крутой, все маленькие девочки скачут на его члене

@loader.tds
class GPMToolMod(loader.Module):
    """Модуль позволяет пересылать сообщение из канала, где это запрещено."""

    strings = {
        "name": "GPMTool",
        "no_args": "<emoji document_id=5116151848855667552>🚫</emoji> <b>Укажите ссылку правильно.</b>\n\n<blockquote>Примеры:\n.gpm <a href='https://t.me/channel/9'>https://t.me/channel/9</a>\n.gpm <a href='https://t.me/c/1234567890/123'>https://t.me/c/1234567890/123</a></blockquote>",
        "invalid_args": "<emoji document_id=5116151848855667552>🚫</emoji><b> Неверный формат ссылки.</b>",
        "msg_not_found": "<emoji document_id=5116151848855667552>🚫</emoji><b> Сообщение не найдено.</b>",
        "no_premium": "<emoji document_id=5121063440311386962>👎</emoji><b> У вас нету Telegram Premium. </b>\n\n<blockquote>Сообщение будет отправлено без премиум эмоджи.</blockquote>",
        "loading": "<emoji document_id=5434105584834067115>🤑</emoji><b> Загрузка...</b>"
    }

    async def client_ready(self, client, db):
        self.client = client

    @loader.command()
    async def gpm(self, message):
        """<ссылка на сообщение> Переслать сообщения из канала, где запрещено."""
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, self.strings["no_args"])
            return
        
        # Обработка разных форматов ссылок
        try:
            # Проверка на корректную ссылку Telegram
            if not args.startswith('https://t.me/'):
                await utils.answer(message, self.strings["invalid_args"])
                return
            
            # Обработка приватных каналов (https://t.me/c/ID/число)
            if '/c/' in args:
                match = re.search(r'https://t\.me/c/(\d+)/(\d+)', args)
                if match:
                    channel_id = int('-100' + match.group(1))
                    msg_id = int(match.group(2))
                else:
                    await utils.answer(message, self.strings["invalid_args"])
                    return
            # Обработка публичных каналов (https://t.me/канал/число)
            else:
                match = re.search(r'https://t\.me/([^/]+)/(\d+)', args)
                if match:
                    channel = match.group(1)
                    msg_id = int(match.group(2))
                else:
                    await utils.answer(message, self.strings["invalid_args"])
                    return
        except ValueError:
            await utils.answer(message, self.strings["invalid_args"])
            return

        await utils.answer(message, self.strings["loading"])
        
        me = await self.client.get_me()
        has_premium = getattr(me, 'premium', False)

        try:
            # Получение сообщения по ID или имени канала
            if '/c/' in args:
                copied_message = await self.client.get_messages(channel_id, ids=msg_id)
            else:
                copied_message = await self.client.get_messages(channel, ids=msg_id)
        except Exception:
            await utils.answer(message, self.strings["msg_not_found"])
            return
        
        if not copied_message:
            await utils.answer(message, self.strings["msg_not_found"])
            return

        media = None
        caption = copied_message.message
        file_path = None

        if copied_message.media:
            file_path = await copied_message.download_media()
            
            if hasattr(copied_message.media, 'photo'):
                media = 'photo'
            elif hasattr(copied_message.media, 'document'):
                media = 'document'
            elif hasattr(copied_message.media, 'audio'):
                media = 'audio'
            elif hasattr(copied_message.media, 'video'):
                media = 'video'
            elif hasattr(copied_message.media, 'voice'):
                media = 'voice'
            elif hasattr(copied_message.media, 'video_note'):
                media = 'video_note'
            elif hasattr(copied_message.media, 'sticker'):
                media = 'sticker'

        try:
            if media:
                if media == 'photo':
                    await self.client.send_file(
                        message.chat_id,
                        file_path,
                        caption=caption,
                        parse_mode='html',
                        formatting_entities=copied_message.entities
                    )
                else:
                    await self.client.send_file(
                        message.chat_id,
                        file_path,
                        caption=caption,
                        parse_mode='html',
                        formatting_entities=copied_message.entities,
                        voice_note=(media == 'voice'),
                        video_note=(media == 'video_note')
                    )
                
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                await message.delete()
            else:
                await utils.answer(
                    message,
                    copied_message.message,
                    parse_mode='html',
                    formatting_entities=copied_message.entities
                )
                
            if not has_premium and message.chat_id != "me":
                await self.client.send_message(message.chat_id, self.strings["no_premium"])
        except Exception as e:
            await utils.answer(message, f"<emoji document_id=5116151848855667552>🚫</emoji><b> Ошибка при отправке: {str(e)}</b>")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
