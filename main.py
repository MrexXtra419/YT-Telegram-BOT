import os
import logging
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =============== CONFIG ===============
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not found! Set it in Railway Variables.")

# =============== LOGGING ===============
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =============== FFMPEG AUTO-INSTALL ===============
def install_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print("✅ ffmpeg already installed")
            return
    except FileNotFoundError:
        print("⚙️ Installing ffmpeg...")
        os.system("apt-get update && apt-get install -y ffmpeg")
        print("✅ ffmpeg installed successfully")

# =============== BOT COMMANDS ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hey there! I'm alive and running on Railway!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 Commands:\n/start - Check bot status\n/help - Show this message")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

# =============== MAIN BOT SETUP ===============
def main():
    print("🚀 Starting Telegram Bot...")
    install_ffmpeg()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("🚀 Bot running on Railway...")
    # Direct synchronous call — no asyncio.run()
    app.run_polling(close_loop=False)

# =============== ENTRYPOINT ===============
if __name__ == "__main__":
    main()
