import os
import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message


logging.basicConfig(level=logging.INFO)


# =========================
# TOKEN
# =========================

TOKEN = os.environ.get("BOT_TOKEN", "").strip()

if not TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

# Tokenni to'liq ko'rsatmaymiz
print("TOKEN LENGTH:", len(TOKEN))
print("TOKEN PREFIX:", TOKEN[:10])


# =========================
# BOT
# =========================

bot = Bot(token=TOKEN)
dp = Dispatcher()


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "✅ Bot ishlayapti!\n\n"
        "Salom! 🎵\n"
        "Menga qo'shiq nomini yuboring."
    )


# =========================
# WEB SERVER
# =========================

async def health(request):
    return web.Response(
        text="Music Finder Bot ishlayapti!"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get("/", health)

    port = int(
        os.environ.get("PORT", "10000")
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    logging.info(
        "WEB SERVER ISHLADI: %s",
        port
    )


# =========================
# MAIN
# =========================

async def main():

    await start_web_server()

    logging.info(
        "TELEGRAM BOT ISHGA TUSHMOQDA..."
    )

    # Webhookni o'chirmaymiz.
    # Hozir faqat tokenni diagnostika qilamiz.

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
