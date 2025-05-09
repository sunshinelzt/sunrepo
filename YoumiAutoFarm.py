# meta developer: @sunshinelzt

from telethon.tl.functions.messages import SendMessageRequest
from hikkatl.types import Message
from .. import loader, utils
import asyncio
import random

# Эмоджи (меняй под себя)
EMOJIS = {
    "police": "<emoji document_id=6046437075064985000>👮</emoji>",
    "psych": "<emoji document_id=6046439609095689718>🤩</emoji>",
    "doc": "<emoji document_id=6046335370239416531>🌟</emoji>",
    "prog": "<emoji document_id=6046362462893118557>🤩</emoji>",
    "pilot": "<emoji document_id=6046513791770825256>🌟</emoji>",
    "start": "<emoji document_id=6046410905829251121>💥</emoji>",
    "stop": "<emoji document_id=6046217396077728534>😡</emoji>",
    "tick": "<emoji document_id=6044327262575141199>🌟</emoji>",
    "cross": "<emoji document_id=6046437019230409156>🤩</emoji>"
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
    """Автофарм работы в @itsYoumi_Bot"""

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
            f"\n<b>Интервал:</b> {delay // 60} мин",
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
                f"{EMOJIS['tick']} <b>Да ничё и не работало, малой.</b>",
                parse_mode="HTML"
            )
            return
        self.running = False
        self.job_task.cancel()
        self.job_task = None
        await message.edit(
            f"{EMOJIS['stop']} <b>Нахуй работу.</b>",
            parse_mode="HTML"
        )
