import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================
# YouTube Download Function
# ==========================
async def download_video(url: str, output_dir: str = "downloads") -> str:
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
        "progress_hooks": [lambda d: print(f"Progress: {d.get('status')}")],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
    except Exception as e:
        print(f"[ERR] Download failed: {e}")
        return None

# ==========================
# Telegram Handlers
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Send me a YouTube link to download!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⬇️ Downloading video, please wait...")

    filename = await download_video(url)
    if filename and os.path.exists(filename):
        await update.message.reply_video(video=open(filename, "rb"))
        os.remove(filename)
    else:
        await update.message.reply_text("⚠️ Download failed. Please check the link.")

# ==========================
# Bot Entry Point
# ==========================
async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("[ERR] Missing BOT_TOKEN environment variable!")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot running on Railway...")
    await app.run_polling()  # ✅ replaces updater.idle()

# ==========================
# Run bot
# ==========================
if __name__ == "__main__":
    asyncio.run(main())
