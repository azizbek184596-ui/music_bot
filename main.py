import asyncio
import yt_dlp
from typing import Optional, Dict, List

# yt-dlp sozlamalari (xatolarni kamaytirish uchun)
YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,          # Faqat ma'lumot olish (tez)
    "default_search": "ytsearch5", # 5 ta natija
    "ignoreerrors": True,
    "noplaylist": True,
    "geo_bypass": True,
    "socket_timeout": 15,
}

async def search_youtube(query: str, limit: int = 5) -> List[Dict]:
    """
    YouTube'dan qidiruv qiladi.
    Qaytaradi: [{"title": ..., "url": ..., "duration": ..., "uploader": ...}, ...]
    """
    opts = YDL_OPTS.copy()
    opts["default_search"] = f"ytsearch{limit}"

    def _search():
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if not info or "entries" not in info:
                    return []
                
                results = []
                for entry in info["entries"]:
                    if not entry:
                        continue
                    results.append({
                        "title": entry.get("title", "Noma'lum"),
                        "url": entry.get("url") or entry.get("webpage_url"),
                        "duration": entry.get("duration"),
                        "uploader": entry.get("uploader") or entry.get("channel"),
                        "thumbnail": entry.get("thumbnail"),
                        "id": entry.get("id"),
                    })
                return results
            except Exception as e:
                print(f"Qidiruv xatosi: {e}")
                return []

    return await asyncio.to_thread(_search)


# Test qilish uchun
async def main():
    results = await search_youtube("Hamdam sobirov")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']} — {r['url']}")

if __name__ == "__main__":
    asyncio.run(main())
