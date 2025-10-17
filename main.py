import os
import asyncio
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import yt_dlp
from telegram.request import HTTPXRequest

# ==================== CONFIG ====================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "PASTE_YOUR_TOKEN_HERE"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 1900 * 1024 * 1024  # 1.9 GB
# =================================================

def sanitize_filename(name: str) -> str:
    """Clean unsafe filename characters."""
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in name).strip()

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Send me a YouTube link to download.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not ("youtube.com" in url or "youtu.be" in url):
        await update.message.reply_text("⚠️ Please send a valid YouTube link.")
        return

    keyboard = [
        [InlineKeyboardButton("🎥 360p", callback_data=f"video|{url}|360"),
         InlineKeyboardButton("🎥 480p", callback_data=f"video|{url}|480")],
        [InlineKeyboardButton("🎥 720p", callback_data=f"video|{url}|720"),
         InlineKeyboardButton("🎥 1080p", callback_data=f"video|{url}|1080")],
        [InlineKeyboardButton("🎵 MP3 Best", callback_data=f"audio|{url}|best"),
         InlineKeyboardButton("🎵 MP3 Medium", callback_data=f"audio|{url}|medium"),
         InlineKeyboardButton("🎵 MP3 Low", callback_data=f"audio|{url}|low")],
    ]
    await update.message.reply_text(
        "Choose format:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== DOWNLOAD HANDLER ====================

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    type_, url, quality = query.data.split("|")
    progress_msg = await query.message.reply_text("⏳ Starting download...")

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }

    if type_ == "video":
        ydl_opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best"
    else:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    loop = asyncio.get_running_loop()

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            percent = int(d.get("downloaded_bytes", 0) / total * 100)
            if percent % 10 == 0:
                asyncio.run_coroutine_threadsafe(
                    progress_msg.edit_text(f"⏳ Downloading... {percent}%"), loop
                )
        elif d["status"] == "finished":
            asyncio.run_coroutine_threadsafe(
                progress_msg.edit_text("✅ Download complete! Processing..."), loop
            )

    ydl_opts["progress_hooks"] = [progress_hook]

    try:
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)

        info = await loop.run_in_executor(None, run_download)

        safe_title = sanitize_filename(info.get("title", "video"))
        found_file = None
        for f in os.listdir(DOWNLOAD_DIR):
            if f.lower().startswith(safe_title.lower()):
                found_file = os.path.join(DOWNLOAD_DIR, f)
                break

        if not found_file:
            files = sorted(
                [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
                key=os.path.getmtime, reverse=True
            )
            found_file = files[0] if files else None

        if not found_file:
            await progress_msg.edit_text("⚠️ Could not find downloaded file.")
            return

        file_size = os.path.getsize(found_file)
        file_size_mb = file_size / (1024 * 1024)
        await progress_msg.edit_text(f"📤 Preparing upload ({file_size_mb:.1f} MB)...")

        if file_size > MAX_FILE_SIZE:
            await progress_msg.edit_text("📦 Splitting large file into parts...")
            await split_and_upload(found_file, query, type_)
        else:
            await upload_file(found_file, query, type_)

        os.remove(found_file)
        await progress_msg.edit_text("✅ Sent successfully!")

    except Exception as e:
        await progress_msg.edit_text(f"⚠️ Download failed:\n`{e}`", parse_mode="Markdown")

# ==================== SPLIT + UPLOAD HELPERS ====================

async def split_and_upload(filepath, query, type_):
    part_size = MAX_FILE_SIZE
    total_size = os.path.getsize(filepath)
    total_parts = math.ceil(total_size / part_size)

    with open(filepath, "rb") as src:
        for i in range(total_parts):
            part_name = f"{filepath}.part{i+1}"
            with open(part_name, "wb") as dest:
                dest.write(src.read(part_size))

            await query.message.reply_text(f"📤 Uploading Part {i+1}/{total_parts}...")
            with open(part_name, "rb") as f:
                if type_ == "video":
                    await query.message.reply_video(video=f)
                else:
                    await query.message.reply_audio(audio=f)
            os.remove(part_name)

async def upload_file(filepath, query, type_):
    with open(filepath, "rb") as f:
        if type_ == "video":
            await query.message.reply_video(video=f)
        else:
            await query.message.reply_audio(audio=f)

# ==================== MAIN (ASYNC VERSION) ====================

async def main():
    print("🚀 Bot running on Railway...")

    request = HTTPXRequest(
        connection_pool_size=8,
        read_timeout=900.0,
        write_timeout=900.0,
        connect_timeout=60.0,
        pool_timeout=60.0
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(download_video))

    await app.initialize()
    await app.start()
    print("✅ Bot started successfully!")
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
