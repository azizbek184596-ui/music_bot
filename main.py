import asyncio
import os
import logging
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

# yt-dlp sozlamalari
YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "default_search": "ytsearch5",
    "extract_flat": "in_playlist",
    "geo_bypass": True,
    "socket_timeout": 20,
}


async def search_songs(query: str, limit: int = 5):
    """YouTube dan qidiruv"""
    opts = YDL_OPTS.copy()
    opts["default_search"] = f"ytsearch{limit}"

    def _search():
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                result = ydl.extract_info(query, download=False)
                entries = result.get("entries", [])
                songs = []
                for entry in entries:
                    if entry:
                        songs.append({
                            "id": entry.get("id"),
                            "title": entry.get("title", "Noma'lum"),
                            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                            "duration": entry.get("duration"),
                            "uploader": entry.get("uploader") or entry.get("channel", "Noma'lum")
                        })
                return songs
            except Exception as e:
                logging.error(f"Qidiruv xatosi: {e}")
                return []

    return await asyncio.to_thread(_search)


async def download_audio(url: str, filename: str):
    """Audioni yuklab olish"""
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
        "geo_bypass": True,
    }

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    await asyncio.to_thread(_download)


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Salom! 🎵\n\n"
        "Menga qo'shiq nomini yozing, men topib beraman.\n"
        "Masalan: <b>Hamdam sobirov</b>",
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text)
async def search_handler(message: Message):
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("Iltimos, qo'shiq nomini to'liqroq yozing.")
        return

    wait_msg = await message.answer("🔍 Qidirilmoqda...")

    songs = await search_songs(query)

    if not songs:
        await wait_msg.edit_text("Hech narsa topilmadi 😔")
        return

    # Tugmalar yaratish
    buttons = []
    for i, song in enumerate(songs):
        duration = f"{song['duration'] // 60}:{song['duration'] % 60:02d}" if song['duration'] else "—"
        text = f"{i+1}. {song['title'][:45]} ({duration})"
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"song_{song['id']}"
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await wait_msg.edit_text(
        f"<b>Qidiruv natijalari:</b> <i>{query}</i>\n\nTanlang:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("song_"))
async def download_handler(callback: CallbackQuery):
    video_id = callback.data.split("_")[1]
    url = f"https://www.youtube.com/watch?v={video_id}"

    await callback.answer("Yuklab olinmoqda...")
    await callback.message.edit_text("⏳ Yuklab olinmoqda, biroz kuting...")

    filename = f"temp_{video_id}.mp3"

    try:
        await download_audio(url, filename)

        # Fayl mavjudligini tekshirish
        if not os.path.exists(filename):
            # Ba'zan .mp3 o'rniga boshqa nom bilan saqlanadi
            for f in os.listdir("."):
                if f.startswith(f"temp_{video_id}") and f.endswith(".mp3"):
                    filename = f
                    break

        audio = FSInputFile(filename)
        await callback.message.answer_audio(
            audio=audio,
            caption="✅ Tayyor!"
        )
        await callback.message.delete()

    except Exception as e:
        logging.error(f"Yuklash xatosi: {e}")
        await callback.message.edit_text("Yuklab olishda xatolik yuz berdi 😔")

    finally:
        # Vaqtinchalik faylni o'chirish
        if os.path.exists(filename):
            os.remove(filename)


async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
