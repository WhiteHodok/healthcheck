from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import requests
from flask import Flask, jsonify
import threading
import asyncio
from dotenv import load_dotenv
import logging
import os

# Инициализируем .env файл
load_dotenv()

# Логгирование действий бота
logging.basicConfig(level=logging.INFO)

# Инициализация aiogram бота
bot = Bot(token=os.getenv('TOKEN_MAIN'))
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Инициализация Flask приложения
app = Flask(__name__)

# Инициализация Телеграм-бота для уведомлений
monitor_bot = Bot(token=os.getenv('TOKEN_CHECK'))
monitor_dp = Dispatcher(monitor_bot)
monitor_dp.middleware.setup(LoggingMiddleware())

# Инициализация Дискорд вебхука
discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

# Клавиатура для мониторингового бота
keyboard_check = InlineKeyboardMarkup()
keyboard_check.add(InlineKeyboardButton("Узнать статус бота", callback_data='check_status'))
keyboard_check.add(InlineKeyboardButton("Получать логи", callback_data='start_logs'))

# Функция отправки уведомлений
async def send_notifications(message):
    # Отправка уведомления в Телеграм
    await monitor_bot.send_message(chat_id=os.getenv('MONITOR_CHAT_ID'), text=message)

    # Отправка уведомления в Дискорд
    if discord_webhook_url:
        requests.post(discord_webhook_url, json={"content": message})

# Команда /start для основного бота
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Hello! I am your bot.")

# Команда /start для мониторингового бота
@monitor_dp.message_handler(commands=['start'])
async def monitor_start(message: types.Message):
    await message.reply("Выберите действие:", reply_markup=keyboard_check)

# CallbackQuery handler для мониторингового бота
@monitor_dp.callback_query_handler(lambda c: c.data == 'check_status' or c.data == 'start_logs' or c.data == 'stop_logs')
async def process_callback(callback_query: CallbackQuery):
    if callback_query.data == 'check_status':
        status = check_bot_health()
        await monitor_bot.send_message(chat_id=callback_query.from_user.id, text=f"Статус бота: {status}")
    elif callback_query.data == 'start_logs':
        # Запуск отправки логов
        asyncio.create_task(send_logs(callback_query.from_user.id))
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Отменить логи", callback_data='stop_logs'))
        await monitor_bot.send_message(chat_id=callback_query.from_user.id, text="Логи запущены. Нажмите кнопку для остановки.", reply_markup=keyboard)
    elif callback_query.data == 'stop_logs':
        # Остановка отправки логов
        global stop_logs_flag
        stop_logs_flag = True
        await monitor_bot.send_message(chat_id=callback_query.from_user.id, text="Логи остановлены.",reply_markup=types.ReplyKeyboardRemove())
        await monitor_bot.send_message(chat_id=os.getenv('MONITOR_CHAT_ID'), text="Вы вернулись в меню.", reply_markup=keyboard_check)

# Функция проверки состояния основного бота
def check_bot_health():
    try:
        response = requests.get('http://localhost:5000/healthcheck')
        if response.status_code == 200 and response.json().get("status") == "ok":
            return "ок"
        else:
            return "не ок"
    except Exception as e:
        return "не ок"

# Функция отправки логов
stop_logs_flag = False
async def send_logs(chat_id):
    global stop_logs_flag
    stop_logs_flag = False
    log_file_path = os.path.join(os.getcwd(), 'logs.log')  # Укажите фактическое имя файла логов здесь
    while not stop_logs_flag:
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r') as log_file:
                logs = log_file.read().strip()  # Удаляем лишние пробелы
                if logs:  # Проверяем, что логи не пустые
                    await monitor_bot.send_message(chat_id=chat_id, text=logs)
                else:
                    await monitor_bot.send_message(chat_id=chat_id, text="Log file is empty.")
        else:
            await monitor_bot.send_message(chat_id=chat_id, text="Log file not found.")
        await asyncio.sleep(60)  # Отправка логов каждые 60 секунд


# Эндпоинт healthcheck
@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    return jsonify(status='ok'), 200

# Запуск Flask приложения в отдельном потоке
def run_flask():
    app.run(port=5000)

# Проверка состояния основного бота
async def check_bot_status():
    while True:
        status = check_bot_health()
        if status != "ок":
            await send_notifications("Your monitored bot is down!")
        await asyncio.sleep(60)  # Проверка каждые 60 секунд

# Запуск основного aiogram бота
async def run_bot():
    await send_notifications("Bot has started!")  # Отправка уведомления о запуске
    asyncio.create_task(check_bot_status())  # Запуск проверки состояния бота
    await dp.start_polling()

# Запуск мониторингового aiogram бота
async def run_monitor_bot():
    await monitor_dp.start_polling()

if __name__ == '__main__':
    # Запуск Flask в отдельном потоке
    threading.Thread(target=run_flask).start()

    # Запуск основного aiogram бота и мониторингового aiogram бота
    loop = asyncio.get_event_loop()
    loop.create_task(run_monitor_bot())
    loop.run_until_complete(run_bot())
