TOKEN = os.environ.get("BOT_TOKEN", "").strip()

if not TOKEN:
    raise RuntimeError("BOT_TOKEN mavjud emas")

print("TOKEN LENGTH:", len(TOKEN))
print("TOKEN PREFIX:", TOKEN[:10])

bot = Bot(token=TOKEN)
