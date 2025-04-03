# meta developer: @sunshinelzt

import re
import logging
import asyncio
import random
import cloudscraper
from datetime import datetime, timedelta
from urllib.parse import unquote

from telethon import events
from telethon.tl.functions.messages import ImportChatInviteRequest, RequestAppWebViewRequest
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.types import (
    KeyboardButtonUrl, 
    KeyboardButtonCallback,
    InputBotAppShortName, 
    InputChannel,
    Message
)
from telethon import errors

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class UltimateGiveawayMod(loader.Module):
    """
    Универсальный модуль для автоматического участия в розыгрышах
    от @GiveShareBot с гибкими настройками
    и функцией автоматического выхода из каналов.
    """

    strings = {
        "name": "UltimateGiveaway",
        
        # Общие строки
        "enabled": "✅ Автоматическое участие в розыгрышах включено",
        "disabled": "❌ Автоматическое участие в розыгрышах отключено",
        "already_enabled": "❗️ Автоматическое участие в розыгрышах уже включено",
        "already_disabled": "❗️ Автоматическое участие в розыгрышах уже отключено",
        
        # GiveShareBot строки
        "giveshare_enabled": "✅ Автоматическое участие в GiveShare розыгрышах включено",
        "giveshare_disabled": "❌ Автоматическое участие в GiveShare розыгрышах отключено",
        "processed_cleared": "🗑 Список обработанных розыгрышей очищен",
        
        # GiveawayBot строки
        "giveaway_enabled": "✅ Автоматическое участие в Giveaway розыгрышах включено",
        "giveaway_disabled": "❌ Автоматическое участие в Giveaway розыгрышах отключено",
        "delay_set": "⏱ Установлены задержки: {}",
        
        # Автовыход строки
        "autoleave_enabled": "🚪 Автоматический выход из каналов включен",
        "autoleave_disabled": "🚫 Автоматический выход из каналов отключен",
        "autoleave_delay_set": "⏱ Установлена задержка автовыхода: {} часов",
        "left_channel": "👋 Вышел из канала: {}",
        "channels_scheduled": "📅 Запланирован выход из {} каналов через {} часов",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            # Общие настройки
            loader.ConfigValue(
                "logs_username",
                "",
                "Имя пользователя канала/чата для логов (если хотите сохранять логи в избранном, укажите 'me'; без @)",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            
            # GiveShareBot настройки
            loader.ConfigValue(
                "giveshare_enabled",
                True,
                "Включить автоматическое участие в GiveShare розыгрышах",
                validator=loader.validators.Boolean()
            ),
            
            # GiveawayBot настройки
            loader.ConfigValue(
                "giveaway_bot_id", 
                1618805558, 
                "ID бота @giveawaybot",
                validator=loader.validators.Integer()
            ),
            loader.ConfigValue(
                "giveaway_enabled",
                True,
                "Включить автоматическое участие в Giveaway розыгрышах",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "delays", 
                [10, 20, 30], 
                "Список задержек перед нажатием в минутах (будет выбрана случайная)",
                validator=loader.validators.Series(loader.validators.Integer())
            ),
            
            # Настройки автовыхода
            loader.ConfigValue(
                "autoleave_enabled",
                True,
                "Включить автоматический выход из каналов после розыгрыша",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "autoleave_delay",
                24,
                "Задержка перед выходом из каналов в часах",
                validator=loader.validators.Integer(minimum=1)
            )
        )
        
        # Инициализация переменных
        self.client = None
        self.db = None
        self.scraper = cloudscraper.create_scraper()
        
        # GiveShare переменные
        self.processed_codes = set()
        self.processed_ids = set()
        
        # Отслеживание каналов для автовыхода
        self.pending_channels = {}  # {channel_id: exit_time}

    async def client_ready(self, client, db):
        """Инициализация при загрузке модуля"""
        self.client = client
        self.db = db
        
        # Загружаем сохраненные данные из базы данных
        self._load_saved_data()
        
        # Регистрируем обработчики событий
        self.client.add_event_handler(self.giveshare_handler, events.NewMessage)
        self.client.add_event_handler(self.giveshare_handler, events.MessageEdited)
        
        # Запускаем проверку выхода из каналов
        asyncio.create_task(self._autoleave_checker())

    def _load_saved_data(self):
        """Загружает сохраненные данные из базы данных"""
        # Загружаем сохраненные ID розыгрышей
        saved_ids = self.db.get("UltimateGiveaway", "processed_ids", [])
        self.processed_ids = set(saved_ids)
        
        # Загружаем сохраненные коды
        saved_codes = self.db.get("UltimateGiveaway", "processed_codes", [])
        self.processed_codes = set(saved_codes)
        
        # Загружаем каналы, ожидающие выхода
        self.pending_channels = self.db.get("UltimateGiveaway", "pending_channels", {})

    async def _autoleave_checker(self):
        """Периодически проверяет каналы для автоматического выхода"""
        while True:
            try:
                now = datetime.now()
                channels_to_leave = []
                
                # Проверяем, какие каналы нужно покинуть
                for channel_id, exit_time in list(self.pending_channels.items()):
                    exit_datetime = datetime.fromisoformat(exit_time)
                    if now >= exit_datetime:
                        channels_to_leave.append(channel_id)
                        del self.pending_channels[channel_id]
                
                # Выходим из каналов
                for channel_id in channels_to_leave:
                    try:
                        channel = await self.client.get_entity(int(channel_id))
                        await self.client(LeaveChannelRequest(channel))
                        await self.log(f"🚪 Автоматически покинул канал: {channel.title}")
                        await asyncio.sleep(1)  # Небольшая пауза между выходами
                    except Exception as e:
                        logger.error(f"Ошибка при выходе из канала {channel_id}: {e}")
                
                # Сохраняем обновленный список ожидающих каналов
                if channels_to_leave:
                    self.db.set("UltimateGiveaway", "pending_channels", self.pending_channels)
                
                # Проверяем каждые 5 минут
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Ошибка в _autoleave_checker: {e}")
                await asyncio.sleep(60)

    async def log(self, message):
        """Отправляет сообщение в логи"""
        if self.config["logs_username"]:
            await self.client.send_message(self.config["logs_username"], message, link_preview=False)

    async def get_init_data(self):
        """Получает данные инициализации для GiveShareBot"""
        bot = await self.client.get_input_entity(1618805558)
        app = InputBotAppShortName(bot_id=bot, short_name="app")
        web_view = await self.client(RequestAppWebViewRequest(peer='me', app=app, platform='android'))
        auth_url = web_view.url
        init_data = unquote(auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
        return init_data

    async def subscribe_to_channel(self, channel_link):
        """Подписывается на канал и добавляет его в список для автовыхода"""
        try:
            # Подписываемся на канал
            if '+' in channel_link:
                invite_code = channel_link.split('+')[1]
                try:
                    updates = await self.client(ImportChatInviteRequest(invite_code))
                    if hasattr(updates, "chats") and updates.chats:
                        channel = updates.chats[0]
                        channel_id = str(channel.id)
                        channel_title = channel.title
                    else:
                        return
                except errors.rpcerrorlist.UserAlreadyParticipantError:
                    # Уже подписан, нужно получить ID канала
                    try:
                        channel = await self.client.get_entity(channel_link)
                        channel_id = str(channel.id)
                        channel_title = channel.title
                    except Exception:
                        return
                except Exception as e:
                    await self.log(f"🚫 Ошибка при подписке на канал {channel_link}: {e}")
                    return
            else:
                try:
                    channel = await self.client.get_entity(channel_link)
                    channel_id = str(channel.id)
                    channel_title = channel.title
                except Exception as e:
                    await self.log(f"🚫 Ошибка при получении информации о канале {channel_link}: {e}")
                    return
            
            # Если автовыход включен, добавляем канал в список для выхода
            if self.config["autoleave_enabled"]:
                exit_time = datetime.now() + timedelta(hours=self.config["autoleave_delay"])
                self.pending_channels[channel_id] = exit_time.isoformat()
                self.db.set("UltimateGiveaway", "pending_channels", self.pending_channels)
                
                logger.info(f"Запланирован выход из канала {channel_title} через {self.config['autoleave_delay']} часов")
                
            return channel_title
        except Exception as e:
            await self.log(f"🚫 Ошибка при подписке/планировании выхода из канала {channel_link}: {e}")
            return None

    async def giveshare_handler(self, event):
        """Обрабатывает события GiveShare розыгрышей"""
        if not self.config["giveshare_enabled"]:
            return

        message_text = event.message.message
        url_pattern = r'https?://t\.me/GiveShareBot/app\?startapp=([A-Za-z0-9]+)'
        codes_in_text = re.findall(url_pattern, message_text)

        # Проверяем кнопки
        if event.message.reply_markup:
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    if isinstance(button, KeyboardButtonUrl) and button.url:
                        code_match = re.match(url_pattern, button.url)
                        if code_match:
                            code = code_match.group(1)
                            if code not in self.processed_codes:
                                await self.participate_in_giveshare(code)
                            return

        # Проверяем текст
        if codes_in_text:
            for code in codes_in_text:
                if code not in self.processed_codes:
                    await self.participate_in_giveshare(code)

    async def participate_in_giveshare(self, code):
        """Участвует в GiveShare розыгрыше"""
        giveaway_url = f"https://t.me/GiveShareBot/app?startapp={code}"

        try:
            init_data = await self.get_init_data()
            
            # Запрашиваем данные о розыгрыше
            response = self.scraper.post(
                'https://api.giveshare.ru/index',
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/plain, */*'
                },
                json={
                    "initData": init_data,
                    "param": code
                }
            )
            
            raffle_data = response.json()
            
            if 'raffle' in raffle_data:
                raffle = raffle_data['raffle']
                
                # Проверяем, не участвовали ли мы уже в этом розыгрыше
                if raffle['id'] in self.processed_ids:
                    return
                
                # Добавляем ID розыгрыша в список обработанных и сохраняем в базу данных
                self.processed_ids.add(raffle['id'])
                self.db.set("UltimateGiveaway", "processed_ids", list(self.processed_ids))
                
                subscribed_channels = []
                
                # Формируем сообщение лога
                log_info = (
                    f"⚡️ <b>Участвую в новом <a href='{giveaway_url}'>GiveShare розыгрыше</a>!</b>\n\n"
                    f"💭 <b>Название:</b> <code>{raffle['title']}</code>\n"
                    f"ℹ️ <b>Текущее кол-во участников:</b> <code>{raffle['members_count']}</code>\n"
                    f"🔜 <b>Дата окончания:</b> <code>{raffle['date_end']}</code>\n\n"
                    f"🖥 <i>Подписался на данные каналы для участия в розыгрыше:</i>\n"
                )
                
                # Подписываемся на каналы
                for channel in raffle['channels']:
                    channel_link = channel['link']
                    channel_name = channel['name']
                    channel_title = await self.subscribe_to_channel(channel_link)
                    log_info += f'• <b><a href="{channel_link}">{channel_name}</a></b>\n'
                    if channel_title:
                        subscribed_channels.append(channel_title)
                
                # Регистрируем участие
                self.scraper.post(
                    'https://api.giveshare.ru/member/create',
                    headers={'Content-Type': 'application/json'},
                    json={
                        "initData": init_data,
                        "param": f"{code}",
                        "token": ""
                    }
                )

                # Проверяем участие
                self.scraper.post(
                    'https://api.giveshare.ru/member/check',
                    headers={'Content-Type': 'application/json'},
                    json={
                        "initData": init_data,
                        "raffle": raffle['id']
                    }
                )

                # Добавляем код в список обработанных и сохраняем в базу данных
                self.processed_codes.add(code)
                self.db.set("UltimateGiveaway", "processed_codes", list(self.processed_codes))
                
                # Добавляем информацию о запланированном выходе, если включен автовыход
                if self.config["autoleave_enabled"] and subscribed_channels:
                    log_info += f"\n🚪 <i>Запланирован автоматический выход из каналов через {self.config['autoleave_delay']} часов</i>"
                
                await self.log(log_info)
            else:
                return
        except Exception as e:
            await self.log(f"🚫 <b>Произошла ошибка при участии в розыгрыше</b>: {e}")

    @loader.watcher(only_messages=True)
    async def giveaway_handler(self, message: Message):
        """Отслеживает сообщения от @giveawaybot"""
        if not self.config["giveaway_enabled"]:
            return

        if not hasattr(message, "sender_id") or message.sender_id != self.config["giveaway_bot_id"]:
            return

        if not hasattr(message, "reply_markup") or not message.reply_markup:
            return

        # Ищем кнопку "Посмотреть розыгрыш"
        found_button = None

        for row in message.reply_markup.rows:
            for button in row.buttons:
                if not isinstance(button, KeyboardButtonCallback):
                    continue

                if button.text == "Посмотреть розыгрыш":
                    found_button = button
                    break

            if found_button:
                break

        if not found_button:
            return

        # Выбираем случайную задержку из списка
        delay_minutes = random.choice(self.config["delays"])
        
        # Вычисляем текущее время и время нажатия
        current_time = datetime.now()
        click_time = current_time + timedelta(minutes=delay_minutes)
        
        logger.info(
            f"Запланировано нажатие: текущее время {current_time.strftime('%H:%M:%S')}, "
            f"будет нажато в {click_time.strftime('%H:%M:%S')} (задержка {delay_minutes} минут)"
        )
        
        # Конвертируем минуты в секунды для asyncio.sleep
        delay_seconds = delay_minutes * 60
        
        await asyncio.sleep(delay_seconds)

        try:
            await message.click(data=found_button.data)
            logger.info(f"Кнопка нажата после задержки {delay_minutes} минут")
        except Exception as e:
            logger.error(f"Ошибка при нажатии на кнопку: {e}")

    @loader.command(ru_doc="Включить/выключить автоматическое участие в розыгрышах")
    async def ultgive(self, message: Message):
        """Включает/выключает автоматическое участие во всех розыгрышах"""
        enabled = not self.config["giveshare_enabled"] and not self.config["giveaway_enabled"]
        self.config["giveshare_enabled"] = enabled
        self.config["giveaway_enabled"] = enabled
        
        await utils.answer(
            message, 
            self.strings["enabled"] if enabled else self.strings["disabled"]
        )

    @loader.command(ru_doc="Включить/выключить автоматическое участие в GiveShare розыгрышах")
    async def gsharetoggle(self, message: Message):
        """Включает/выключает автоматическое участие в GiveShare розыгрышах"""
        self.config["giveshare_enabled"] = not self.config["giveshare_enabled"]
        
        await utils.answer(
            message, 
            self.strings["giveshare_enabled"] if self.config["giveshare_enabled"] else self.strings["giveshare_disabled"]
        )
    
    @loader.command(ru_doc="Включить/выключить автоматическое участие в Giveaway розыгрышах")
    async def giveawaytoggle(self, message: Message):
        """Включает/выключает автоматическое участие в Giveaway розыгрышах"""
        self.config["giveaway_enabled"] = not self.config["giveaway_enabled"]
        
        await utils.answer(
            message, 
            self.strings["giveaway_enabled"] if self.config["giveaway_enabled"] else self.strings["giveaway_disabled"]
        )
        
    @loader.command(ru_doc="Очистить список обработанных розыгрышей")
    async def cleargive(self, message: Message):
        """Очищает список обработанных розыгрышей"""
        self.processed_ids = set()
        self.processed_codes = set()
        self.db.set("UltimateGiveaway", "processed_ids", [])
        self.db.set("UltimateGiveaway", "processed_codes", [])
        await utils.answer(message, self.strings["processed_cleared"])

    @loader.command(ru_doc="Установить задержки в минутах (через пробел)")
    async def setdelay(self, message: Message):
        """Устанавливает задержки в минутах перед участием в Giveaway розыгрышах (через пробел)"""
        args = utils.get_args(message)
        if not args:
            await utils.answer(
                message, 
                f"Текущие задержки: {', '.join(map(str, self.config['delays']))} минут"
            )
            return

        try:
            delays = [int(delay) for delay in args]
            self.config["delays"] = delays
            await utils.answer(
                message, 
                self.strings["delay_set"].format(', '.join(map(str, delays)) + " минут")
            )
        except ValueError:
            await utils.answer(message, "❌ Ошибка: введите числа через пробел")

    @loader.command(ru_doc="Включить/выключить автоматический выход из каналов")
    async def autoleave(self, message: Message):
        """Включает/выключает автоматический выход из каналов после розыгрыша"""
        self.config["autoleave_enabled"] = not self.config["autoleave_enabled"]
        
        await utils.answer(
            message, 
            self.strings["autoleave_enabled"] if self.config["autoleave_enabled"] else self.strings["autoleave_disabled"]
        )

    @loader.command(ru_doc="Установить задержку автовыхода в часах")
    async def setleavedelay(self, message: Message):
        """Устанавливает задержку в часах перед автоматическим выходом из каналов"""
        args = utils.get_args(message)
        if not args:
            await utils.answer(
                message, 
                f"Текущая задержка автовыхода: {self.config['autoleave_delay']} часов"
            )
            return

        try:
            delay = int(args[0])
            if delay < 1:
                await utils.answer(message, "❌ Задержка должна быть не менее 1 часа")
                return
                
            self.config["autoleave_delay"] = delay
            await utils.answer(
                message, 
                self.strings["autoleave_delay_set"].format(delay)
            )
        except ValueError:
            await utils.answer(message, "❌ Ошибка: введите число часов")
            
    @loader.command(ru_doc="Показать список каналов для автовыхода")
    async def leavelist(self, message: Message):
        """Показывает список каналов, запланированных для автоматического выхода"""
        if not self.pending_channels:
            await utils.answer(message, "🚫 Нет запланированных каналов для выхода")
            return
            
        now = datetime.now()
        channels_info = []
        
        for channel_id, exit_time_str in self.pending_channels.items():
            exit_time = datetime.fromisoformat(exit_time_str)
            remaining = exit_time - now
            hours = int(remaining.total_seconds() / 3600)
            minutes = int((remaining.total_seconds() % 3600) / 60)
            
            try:
                channel = await self.client.get_entity(int(channel_id))
                channel_title = channel.title
                channel_info = f"• <b>{channel_title}</b> - через {hours} ч. {minutes} мин."
                channels_info.append(channel_info)
            except Exception:
                channels_info.append(f"• <b>ID: {channel_id}</b> - через {hours} ч. {minutes} мин.")
        
        message_text = f"📋 <b>Запланированный выход из каналов:</b>\n\n" + "\n".join(channels_info)
        await utils.answer(message, message_text)
        
    @loader.command(ru_doc="Принудительно выйти из всех каналов в списке автовыхода")
    async def forceleave(self, message: Message):
        """Принудительно выходит из всех каналов в списке автовыхода"""
        if not self.pending_channels:
            await utils.answer(message, "🚫 Нет запланированных каналов для выхода")
            return
            
        total_channels = len(self.pending_channels)
        success_count = 0
        
        for channel_id in list(self.pending_channels.keys()):
            try:
                channel = await self.client.get_entity(int(channel_id))
                await self.client(LeaveChannelRequest(channel))
                await self.log(f"🚪 Принудительно покинул канал: {channel.title}")
                del self.pending_channels[channel_id]
                success_count += 1
                await asyncio.sleep(1)  # Небольшая пауза между выходами
            except Exception as e:
                logger.error(f"Ошибка при принудительном выходе из канала {channel_id}: {e}")
        
        # Сохраняем обновленный список
        self.db.set("UltimateGiveaway", "pending_channels", self.pending_channels)
        
        await utils.answer(
            message, 
            f"✅ Успешно покинул {success_count} из {total_channels} каналов"
        )
