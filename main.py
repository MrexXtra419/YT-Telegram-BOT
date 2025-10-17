import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# ==========================
# CONFIG
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==========================
# DOWNLOAD LOGIC
# ==========================
async def download_video(url: str) -> str | None:
    """Download YouTube video using yt_dlp and return filename."""
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
    }

    try:
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        loop = asyncio.get_running_loop()
        filename = await loop.run_in_executor(None, run_download)
        return filename

    except Exception as e:
        print(f"[ERR] Download failed: {e}")
        return None

# ==========================
# BOT COMMANDS
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Send me a YouTube link to download!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not ("youtube.com" in url or "youtu.be" in url):
        await update.message.reply_text("⚠️ Please send a valid YouTube link.")
        return

    await update.message.reply_text("⬇️ Downloading video, please wait...")

    filename = await download_video(url)
    if filename and os.path.exists(filename):
        await update.message.reply_video(video=open(filename, "rb"))
        os.remove(filename)
        await update.message.reply_text("✅ Done!")
    else:
        await update.message.reply_text("❌ Download failed.")

# ==========================
# MAIN APP
# ==========================
async def main():
    if not BOT_TOKEN:
        print("[ERR] BOT_TOKEN not set in environment!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot running on Railway...")
    await app.run_polling()  # async-safe

# ==========================
# ASYNCIO LOOP FIX
# ==========================
if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Railway or environments with existing loop
        print("⚙️ Using existing event loop...")
        loop.create_task(main())
    else:
        asyncio.run(main())
