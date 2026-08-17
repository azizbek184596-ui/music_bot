import asyncio
import logging
import os
import uuid

from aiohttp import web

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    FSInputFile,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ_BU_YERGA")
PORT = int(os.getenv("PORT", "8080"))
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("music_bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

search_cache: dict[str, dict] = {}


def search_youtube(query: str, limit: int = 5) -> list[dict]:
    ydl_opts = {
        "quiet": True,
        "default_search": f"ytsearch{limit}",
        "noplaylist": True,
        "extract_flat": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        entries = info.get("entries", []) if info else []

    results = []
    for entry in entries:
        results.append(
            {
                "id": entry.get("id"),
                "title": entry.get("title"),
                "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                "duration": entry.get("duration"),
                "uploader": entry.get("uploader") or entry.get("channel"),
            }
        )
    return results


def download_audio(url: str, out_path: str) -> str:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_path,
        "quiet": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return out_path + ".mp3"


def format_duration(seconds) -> str:
    if not seconds:
        return "?"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Salom, {message.from_user.full_name}! 🎵\n\n"
        "Menga qo'shiq nomini yozing, men uni YouTube'dan topib, "
        "audio (mp3) formatda yuboraman.\n\n"
        "Masalan: Imagine Dragons Believer"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📌 Foydalanish:\n"
        "1. Qo'shiq nomini yozing\n"
        "2. Ro'yxatdan raqamni tanlang (masalan: 1)\n"
        "3. Bot audio faylni yuboradi\n\n"
        "Inline rejim: istalgan chatda @bot_username qo'shiq_nomi deb yozing"
    )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message):
    query = message.text.strip()
    if query.isdigit():
        await handle_choice(message)
        return

    status_msg = await message.answer(f"🔍 Qidirilmoqda: {query} ...")

    try:
        results = await asyncio.to_thread(search_youtube, query)
    except Exception:
        log.exception("Qidiruvda xatolik")
        await status_msg.edit_text("Xatolik yuz berdi, qayta urinib ko'ring.")
        return

    if not results:
        await status_msg.edit_text("Hech narsa topilmadi 😕")
        return

    search_cache[str(message.from_user.id)] = {"results": results}

    text_lines = ["🎶 Natijalar topildi:\n"]
    for i, r in enumerate(results, start=1):
        text_lines.append(f"{i}. {r['title']} — {format_duration(r['duration'])}")
    text_lines.append("\nYuklab olish uchun raqamni yuboring, masalan: 1")

    await status_msg.edit_text("\n".join(text_lines))


async def handle_choice(message: Message):
    user_id = str(message.from_user.id)
    cache = search_cache.get(user_id)

    if not cache:
        await message.answer("Avval biror qo'shiq nomini yozib qidiring.")
        return

    idx = int(message.text) - 1
    results = cache["results"]

    if idx < 0 or idx >= len(results):
        await message.answer("Noto'g'ri raqam.")
        return

    track = results[idx]
    status_msg = await message.answer(f"⬇️ Yuklanmoqda: {track['title']} ...")

    out_path = os.path.join(DOWNLOAD_DIR, str(uuid.uuid4()))
    mp3_path = out_path + ".mp3"
    try:
        await asyncio.to_thread(download_audio, track["url"], out_path)
        audio_file = FSInputFile(mp3_path, filename=f"{track['title']}.mp3")
        await message.answer_audio(audio_file, title=track["title"], performer=track.get("uploader"))
        await status_msg.delete()
    except Exception:
        log.exception("Yuklashda xatolik")
        await status_msg.edit_text("Yuklashda xatolik yuz berdi, qayta urinib ko'ring.")
    finally:
        if os.path.exists(mp3_path):
            os.remove(mp3_path)


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        return

    try:
        results = await asyncio.to_thread(search_youtube, query, 8)
    except Exception:
        log.exception("Inline qidiruvda xatolik")
        results = []

    items = []
    for r in results:
        items.append(
            InlineQueryResultArticle(
                id=r["id"],
                title=r["title"],
                description=f"{r.get('uploader', '')} • {format_duration(r['duration'])}",
                input_message_content=InputTextMessageContent(
                    message_text=f"🎵 {r['title']}\n{r['url']}"
                ),
            )
        )

    await inline_query.answer(items, cache_time=10)


async def health_check(request):
    return web.Response(text="Bot ishlayapti ✅")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"Health-check server {PORT}-portda ishga tushdi")


async def run_bot_forever():
    while True:
        try:
            log.info("Bot polling boshlandi...")
            await dp.start_polling(bot, handle_signals=False)
        except Exception:
            log.exception("Bot yiqildi, 5 soniyadan keyin qayta ishga tushadi...")
            await asyncio.sleep(5)


async def main():
    await start_web_server()
    await run_bot_forever()


if __name__ == "__main__":
    asyncio.run(main())
