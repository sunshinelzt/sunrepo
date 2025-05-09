# meta developer: @sunshinelzt

import random
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import types

from .. import loader, utils

logger = logging.getLogger(__name__)

EMOJI_POLICE = "<emoji document_id=6046437075064985000>👮</emoji>"
EMOJI_PSYCHO = "<emoji document_id=5397681122542893003>🤖</emoji>"
EMOJI_DOCTOR = "<emoji document_id=6046335370239416531>🌟</emoji>"
EMOJI_PROGRAMMER = "<emoji document_id=5855239622266720596>👨‍💻</emoji>"
EMOJI_PILOT = "<emoji document_id=5231313240755030628>✈️</emoji>"
EMOJI_STOP = "<emoji document_id=6046437019230409156>🤩</emoji>"
EMOJI_STATUS = "<emoji document_id=6046362462893118557>🤩</emoji>"

class YoumiAutoFarmMod(loader.Module):
    """Автофарм для бота @itsYoumi_Bot"""
    
    strings = {
        "name": "YoumiAutoFarm",
        "job_started": "<b>{} Ебашим автофарм {}! Погнали нахуй!</b>",
        "job_stopped": "<b>{} Автофарм остановлен нахуй!</b>",
        "job_status": "<b>{} Че там по автофарму:</b>\n{}\n<i>Последнее действие: {}</i>",
        "no_active_jobs": "<b>Нихуя не запущено, ленивая жопа!</b>",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "RANDOM_MIN", 10, "Минимальная случайная задержка (секунды)",
            "RANDOM_MAX", 60, "Максимальная случайная задержка (секунды)",
            "BOT_USERNAME", "itsYoumi_Bot", "Юзернейм целевого бота",
        )
        self.jobs = {}
        self.last_action_time = None
        self.name = self.strings["name"]
    
    async def client_ready(self, client, db):
        self._db = db
        self._client = client
        self._me = await client.get_me()

    async def _send_message_to_bot(self, message):
        """Отправляет сообщение боту с имитацией человека"""
        try:
            delay = random.randint(self.config["random_min"], self.config["random_max"])
            await asyncio.sleep(delay)
            
            self.last_action_time = datetime.now().strftime("%H:%M:%S")
            
            await self._client.send_message(self.config["bot_username"], message)
            logger.info(f"Сообщение '{message}' отправлено боту @{self.config['bot_username']}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")

    async def _job_worker(self, job_name, job_message, interval_minutes):
        """Основной воркер для автофарма"""
        try:
            while job_name in self.jobs:
                await self._send_message_to_bot(job_message)
                
                random_error = random.randint(10, 60)
                
                total_wait = (interval_minutes * 60) + random_error
                
                await asyncio.sleep(total_wait)
                
        except asyncio.CancelledError:
            logger.info(f"Задача {job_name} отменена")
            pass
        except Exception as e:
            logger.error(f"Ошибка в работе автофарма {job_name}: {e}")

    async def _start_job(self, message, job_name, job_message, emoji, interval_minutes):
        """Запускает новую задачу автофарма"""
        if job_name in self.jobs:
            self.jobs[job_name].cancel()
            
        task = asyncio.create_task(self._job_worker(job_name, job_message, interval_minutes))
        self.jobs[job_name] = task
        
        await utils.answer(
            message, 
            self.strings["job_started"].format(emoji, job_name)
        )

    async def ym_pcmd(self, message):
        """Запускает автофарм полицейского"""
        await self._start_job(message, "Полицейский", "Полицейский", EMOJI_POLICE, 5)

    async def ym_psycmd(self, message):
        """Запускает автофарм психолога"""
        await self._start_job(message, "Психолог", "Психолог", EMOJI_PSYCHO, 7)

    async def ym_doccmd(self, message):
        """Запускает автофарм врача"""
        await self._start_job(message, "Врач", "Врач", EMOJI_DOCTOR, 10)

    async def ym_devcmd(self, message):
        """Запускает автофарм программиста"""
        await self._start_job(message, "Программист", "Программист", EMOJI_PROGRAMMER, 15)

    async def ym_pilcmd(self, message):
        """Запускает автофарм пилота"""
        await self._start_job(message, "Пилот", "Пилот", EMOJI_PILOT, 25)

    async def ym_stopcmd(self, message):
        """Останавливает все задачи автофарма"""
        for job_name, task in self.jobs.items():
            task.cancel()
        
        self.jobs.clear()
        
        await utils.answer(message, self.strings["job_stopped"].format(EMOJI_STOP))

    async def ym_statcmd(self, message):
        """Показывает статус автофарма"""
        if not self.jobs:
            await utils.answer(message, self.strings["no_active_jobs"])
            return
            
        status_text = ""
        for job_name in self.jobs:
            status_text += f"<emoji document_id=5436402945660838021>🔁</emoji> <b>{job_name}</b> работает\n"
            
        last_action = self.last_action_time if self.last_action_time else "Нет действий"
        await utils.answer(
            message, 
            self.strings["job_status"].format(EMOJI_STATUS, status_text, last_action)
        )
