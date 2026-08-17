import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import yt_dlp


# =========================
# SOZLAMALAR
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")


logging.basicConfig(
    level=logging.INFO
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# YOUTUBE QIDIRISH
# =========================

async def search_youtube(query):

    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "ignoreerrors": True,
    }

    def search():

        try:

            with yt_dlp.YoutubeDL(options) as ydl:

                result = ydl.extract_info(
                    f"ytsearch5:{query}",
                    download=False
                )

                if not result:
                    return []

                songs = []

                for item in result.get("entries", []):

                    if not item:
                        continue

                    video_id = item.get("id")

                    if not video_id:
                        continue

                    songs.append({
                        "title": item.get(
                            "title",
                            "Noma'lum"
                        ),
                        "url": (
                            "https://www.youtube.com/watch?v="
                            + video_id
                        )
                    })

                return songs

        except Exception as error:

            logging.error(
                "YouTube xatosi: %s",
                error
            )

            return []

    return await asyncio.to_thread(search)


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start_handler(message: Message):

    await message.answer(
        "🎵 <b>Music Finder Bot</b>\n\n"
        "Qo'shiq nomini yozing.\n\n"
        "Masalan:\n"
        "Hamdam Sobirov\n"
        "Yurak\n"
        "Faded",
        parse_mode="HTML"
    )


# =========================
# QIDIRISH
# =========================

@dp.message(F.text)
async def search_handler(message: Message):

    query = message.text.strip()

    if len(query) < 2:

        await message.answer(
            "❗ Qo'shiq nomini yozing."
        )

        return

    status = await message.answer(
        "🔎 Qidirilmoqda..."
    )

    results = await search_youtube(query)

    if not results:

        await status.edit_text(
            "😔 Hech narsa topilmadi."
        )

        return

    buttons = []

    for song in results:

        title = song["title"]

        if len(title) > 45:
            title = title[:45] + "..."

        buttons.append([
            InlineKeyboardButton(
                text=f"▶️ {title}",
                url=song["url"]
            )
        ])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await status.edit_text(
        f"🎵 <b>Natijalar</b>\n\n"
        f"🔎 {query}\n\n"
        f"Kerakli qo'shiqni tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# =========================
# RENDER WEB SERVER
# =========================

async def health(request):

    return web.Response(
        text="Music Finder Bot ishlayapti!"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health
    )

    port = int(
        os.getenv(
            "PORT",
            "10000"
        )
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
        "Web server ishga tushdi: %s",
        port
    )


# =========================
# MAIN
# =========================

async def main():

    await start_web_server()

    logging.info(
        "Telegram bot ishga tushmoqda..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
