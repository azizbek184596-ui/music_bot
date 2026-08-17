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


async def search_youtube(query: str, limit: int = 5):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": f"ytsearch{limit}",
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
                        "source": "YouTube",
                        "id": entry.get("id"),
                        "title": entry.get("title", "Noma'lum"),
                        "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                        "duration": entry.get("duration"),
                        "uploader": entry.get("uploader") or entry.get("channel", "Noma'lum"),
                    })
                return songs
            except Exception as e:
                logging.error(f"YouTube xato: {e}")
                return []

    return await asyncio.to_thread(_search)


async def search_soundcloud(query: str, limit: int = 4):
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
                        "source": "SoundCloud",
                        "id": entry.get("id"),
                        "title": entry.get("title", "Noma'lum"),
                        "url": entry.get("url") or entry.get("webpage_url"),
                        "duration": entry.get("duration"),
                        "uploader": entry.get("uploader") or entry.get("artist", "Noma'lum"),
                    })
                return songs
            except Exception as e:
                logging.error(f"SoundCloud xato: {e}")
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
        "Men <b>YouTube</b> va <b>SoundCloud</b> dan musiqa qidiraman.\n"
        "Qo'shiq nomini yozing.\n\n"
        "Masalan: <code>Hamdam sobirov</code>",
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text)
async def search_handler(message: Message):
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("Iltimos, qo'shiq nomini yozing.")
        return

    wait_msg = await message.answer("🔍 Qidirilmoqda (YouTube + SoundCloud)...")

    # Parallel qidiruv
    yt_task = search_youtube(query)
    sc_task = search_soundcloud(query)
    yt_results, sc_results = await asyncio.gather(yt_task, sc_task)

    songs = yt_results + sc_results

    if not songs:
        await wait_msg.edit_text("Hech narsa topilmadi 😔")
        return

    buttons = []
    for i, song in enumerate(songs[:8]):  # maksimal 8 ta
        duration = ""
        if song.get("duration"):
            mins = int(song["duration"] // 60)
            secs = int(song["duration"] % 60)
            duration = f" {mins}:{secs:02d}"

        source_emoji = "▶️" if song["source"] == "YouTube" else "☁️"
        title = song["title"][:42]
        buttons.append([
            InlineKeyboardButton(
                text=f"{source_emoji} {title}{duration}",
                callback_data=f"dl_{song['source'][:2]}_{song['id']}"
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await wait_msg.edit_text(
        f"<b>Natijalar:</b> <i>{query}</i>\n\nTanlang:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("dl_"))
async def download_handler(callback: CallbackQuery):
    parts = callback.data.split("_", 2)
    source = parts[1]  # YT yoki SC
    track_id = parts[2]

    if source == "YT":
        url = f"https://www.youtube.com/watch?v={track_id}"
    else:
        url = f"https://soundcloud.com/{track_id}" if not track_id.startswith("http") else track_id
