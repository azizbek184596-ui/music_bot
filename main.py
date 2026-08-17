import asyncio
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


async def search_soundcloud(query: str, limit: int = 6):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": f"scsearch{limit}",
        "ignoreerrors": True,
    }

    def _search():
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                result = ydl.extract_info(query, download=False)
                entries = result.get("entries", [])
                songs = []
                for entry in entries:
                    if not entry:
                        continue
                    songs.append({
                        "id": entry.get("id"),
                        "title": entry.get("title", "Noma'lum"),
                        "url": entry.get("url") or entry.get("webpage_url"),
                        "duration": entry.get("duration"),
                        "uploader": entry.get("uploader") or entry.get("artist", "Noma'lum"),
                    })
                return songs
            except Exception as e:
                logging.error(f"SoundCloud qidiruv xatosi: {e}")
                return []

    return await asyncio.to_thread(_search)


async def download_audio(url: str, filename: str):
    opts = {
        "format": "bestaudio/best",
        "outtmpl": filename,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    await asyncio.to_thread(_download)


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Salom! 🎵\n\n"
        "Men <b>SoundCloud</b> dan musiqa qidiraman.\n"
        "Qo'shiq nomini yozing.",
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text)
async def search_handler(message: Message):
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("Iltimos, qo'shiq nomini yozing.")
        return

    wait_msg = await message.answer("🔍 SoundCloud dan qidirilmoqda...")

    songs = await search_soundcloud(query)

    if not songs:
        await wait_msg.edit_text("Hech narsa topilmadi 😔")
        return

    buttons = []
    for i, song in enumerate(songs):
        duration = ""
        if song.get("duration"):
            mins = song["duration"] // 60
            secs = song["duration"] % 60
            duration = f" ({mins}:{secs:02d})"
        
        title = song["title"][:50]
        buttons.append([
            InlineKeyboardButton(
                text=f"{i+1}. {title}{duration}",
                callback_data=f"sc_{song['id']}"
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await wait_msg.edit_text(
        f"<b>SoundCloud natijalari:</b> <i>{query}</i>\n\nTanlang:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("sc_"))
async def download_handler(callback: CallbackQuery):
    track_id = callback.data.split("_", 1)[1]
    url = f"https://soundcloud.com/{track_id}" if not track_id.startswith("http") else track_id

    await callback.answer("Yuklab olinmoqda...")
    await callback.message.edit_text("⏳ Yuklab olinmoqda...")

    filename = f"sc_{track_id[:20]}.mp3"

    try:
        await download_audio(url, filename)

        real_file = None
        for f in os.listdir("."):
            if f.startswith(f"sc_{track_id[:20]}") and f.endswith(".mp3"):
                real_file = f
                break

        if not real_file:
            await callback.message.edit_text("Yuklab olishda xatolik yuz berdi 😔")
            return

        audio = FSInputFile(real_file)
        await callback.message.answer_audio(audio=audio, caption="✅ Tayyor!")
        await callback.message.delete()

    except Exception as e:
        logging.error(f"Yuklash xatosi: {e}")
        await callback.message.edit_text("Yuklab olishda xatolik yuz berdi 😔")

    finally:
        for f in os.listdir("."):
            if f.startswith("sc_") and f.endswith(".mp3"):
                try:
                    os.remove(f)
                except:
                    pass


# Render uchun port ochish
async def on_startup(app):
    print("SoundCloud Music Bot ishga tushdi...")
    asyncio.create_task(dp.start_polling(bot))


async def main():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="Bot ishlayapti"))
    app.on_startup.append(on_startup)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Server {port}-portda ishga tushdi")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
