from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os
import asyncio
import requests
from dotenv import load_dotenv

load_dotenv()

class MonitorBot:
    def __init__(self):
        self.token = os.getenv('TOKEN_CHECK')
        self.application = Application.builder().token(self.token).build()
        self.stop_logs_flag = False
        self.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("Узнать статус бота", callback_data='check_status')],
            [InlineKeyboardButton("Получать логи", callback_data='start_logs')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == 'check_status':
            status = self.check_bot_health()
            await query.message.reply_text(f"Статус бота: {status}")
        elif query.data == 'start_logs':
            keyboard = [[InlineKeyboardButton("Отменить логи", callback_data='stop_logs')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Логи запущены. Нажмите кнопку для остановки.", reply_markup=reply_markup)
            await self.send_logs(query.message.chat_id)
        elif query.data == 'stop_logs':
            self.stop_logs_flag = True
            await query.message.reply_text("Логи остановлены.")

    def check_bot_health(self):
        try:
            response = requests.get('http://localhost:5000/healthcheck')
            if response.status_code == 200 and response.json().get("status") == "ok":
                return "ок"
            else:
                return "не ок"
        except Exception:
            return "не ок"

    async def send_logs(self, chat_id):
        self.stop_logs_flag = False
        log_file_path = os.path.join(os.getcwd(), 'logs.log')
        while not self.stop_logs_flag:
            if os.path.exists(log_file_path):
                with open(log_file_path, 'r') as log_file:
                    logs = log_file.read().strip()
                    if logs:
                        await self.application.bot.send_message(chat_id=chat_id, text=logs)
                    else:
                        await self.application.bot.send_message(chat_id=chat_id, text="Log file is empty.")
            else:
                await self.application.bot.send_message(chat_id=chat_id, text="Log file not found.")
            await asyncio.sleep(60)

    async def send_notifications(self, message):
        await self.application.bot.send_message(chat_id=os.getenv('MONITOR_CHAT_ID'), text=message)
        if self.discord_webhook_url:
            requests.post(self.discord_webhook_url, json={"content": message})

    async def check_bot_status(self):
        while True:
            status = self.check_bot_health()
            if status != "ок":
                await self.send_notifications("Your monitored bot is down!")
            await asyncio.sleep(60)

    async def run(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button))
        await self.application.initialize()
        await self.application.start()
        await self.send_notifications("Bot has started!")
        asyncio.create_task(self.check_bot_status())
        await self.application.updater.start_polling()
        # Заменяем await self.application.idle() на бесконечный цикл
        while True:
            await asyncio.sleep(3600)  # Спим 1 час, чтобы держать бота активным