import os
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --- Telegram Bot Token ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Download Folder ---
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Progress Hook ---
def progress_hook(d):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '').strip()
        s = d.get('_speed_str', '')
        eta = d.get('eta', 0)
        print(f"Downloading: {p} | Speed: {s} | ETA: {eta}s")


# --- /start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 *YouTube Downloader Bot*\n\n"
        "Choose what you want to download:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Video", callback_data="video")],
            [InlineKeyboardButton("🎵 Audio", callback_data="audio")]
        ])
    )


# --- Handle Button Selection ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "video":
        keyboard = [
            [InlineKeyboardButton("360p", callback_data="v_360p")],
            [InlineKeyboardButton("480p", callback_data="v_480p")],
            [InlineKeyboardButton("720p", callback_data="v_720p")],
            [InlineKeyboardButton("1080p", callback_data="v_1080p")]
        ]
        await query.edit_message_text("🎬 Choose video quality:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "audio":
        keyboard = [
            [InlineKeyboardButton("64 kbps", callback_data="a_64k")],
            [InlineKeyboardButton("128 kbps", callback_data="a_128k")],
            [InlineKeyboardButton("192 kbps", callback_data="a_192k")]
        ]
        await query.edit_message_text("🎵 Choose audio quality:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith(("v_", "a_")):
        context.user_data["choice"] = data
        await query.edit_message_text("📎 Now send me the YouTube link you want to download.")


# --- Handle YouTube Link ---
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    choice = context.user_data.get("choice")

    if not choice:
        await update.message.reply_text("⚠️ Please choose *Video* or *Audio* first with /start", parse_mode="Markdown")
        return

    await update.message.reply_text("⏳ Downloading... Please wait.")

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "progress_hooks": [progress_hook],
        "quiet": True,
    }

    if choice.startswith("v_"):
        quality = choice.split("_")[1]
        ydl_opts["format"] = f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]"
    else:
        bitrate = choice.split("_")[1]
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate[:-1]
            }]
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            file_path = ydl.prepare_filename(info)
            if choice.startswith("a_"):
                file_path = os.path.splitext(file_path)[0] + ".mp3"

        await update.message.reply_document(open(file_path, "rb"))
        await update.message.reply_text("✅ Done! File uploaded successfully.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")


# --- Main Function ---
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("🚀 Bot running on Railway...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
