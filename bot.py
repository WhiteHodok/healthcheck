import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from dotenv import load_dotenv

load_dotenv()

class MainBot:
    def __init__(self):
        self.token = os.getenv('TOKEN_MAIN')
        self.application = Application.builder().token(self.token).build()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Hello! I am your bot.")

    async def run(self):
        self.application.add_handler(CommandHandler("start", self.start))
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        # Заменяем await self.application.idle() на бесконечный цикл
        while True:
            await asyncio.sleep(3600)  # Спим 1 час, чтобы держать бота активным