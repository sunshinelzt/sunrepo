# ⚙️ Модуль: auto_jobs_youmi.py
# ✍️ Автор: @sunshinelzt (по заказу Валентина)
# 🐒 За рофлы, код и бессонницу не судите строго

from telethon.tl.functions.messages import SendMessageRequest
from hikkatl.types import Message
from .. import loader, utils
import asyncio
import random

# Эмоджи (меняй под себя)
EMOJIS = {
    "police": "👮",
    "psych": "🧠",
    "doc": "🩺",
    "prog": "💻",
    "pilot": "✈️",
    "start": "▶️",
    "stop": "⛔",
    "tick": "✅",
    "cross": "❌"
}

# Профессии и тайминги (в секундах)
JOBS = {
    "полицейский": 300,
    "психолог": 420,
    "врач": 600,
    "программист": 900,
    "пилот": 1500
}


@loader.tds
class AutoYoumiJobsMod(loader.Module):
    """Автофарм профессий в @itsYoumi_Bot (боту хоть бы хны)"""

    strings = {
        "name": "AutoYoumiJobs",
    }

    def __init__(self):
        self.job_task = None
        self.running = False

    @loader.command()
    async def ajob(self, message: Message):
        """- <профессия> — начать фармить"""
        args = utils.get_args_raw(message).lower().strip()

        if not args or args not in JOBS:
            await message.edit(
                f"{EMOJIS['cross']} <b>Ебать, напиши норм профессию:</b><br>" +
                "<br>".join([f"• <b>{k}</b>" for k in JOBS.keys()]),
                parse_mode="HTML"
            )
            return

        if self.running:
            await message.edit(
                f"{EMOJIS['cross']} <b>Уже жрёт проц... Останови сначала!</b>",
                parse_mode="HTML"
            )
            return

        delay = JOBS[args]
        self.running = True
        await message.edit(
            f"{EMOJIS['start']} <b>Запущен фарм для профессии:</b> <i>{args}</i><br>"
            f"<b>Интервал:</b> {delay // 60} мин",
            parse_mode="HTML"
        )

        async def job_loop():
            while self.running:
                rand_delay = random.randint(10, 60)
                total_delay = delay + rand_delay
                await self._client(SendMessageRequest(
                    peer="@itsYoumi_Bot",
                    message=args.capitalize(),
                    no_webpage=True
                ))
                await asyncio.sleep(total_delay)

        self.job_task = asyncio.create_task(job_loop())

    @loader.command()
    async def sjob(self, message: Message):
        """— остановить фарм"""
        if not self.running:
            await message.edit(
                f"{EMOJIS['tick']} <b>Да ничё и не работало, бродяга.</b>",
                parse_mode="HTML"
            )
            return
        self.running = False
        self.job_task.cancel()
        self.job_task = None
        await message.edit(
            f"{EMOJIS['stop']} <b>Забил на работу. Профессия нахрен ушла.</b>",
            parse_mode="HTML"
        )
