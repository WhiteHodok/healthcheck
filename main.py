import asyncio
from bot import MainBot
from monitor import MonitorBot
from web import run_flask
import threading


async def main():
    main_bot = MainBot()
    monitor_bot = MonitorBot()

    # Запуск Flask в отдельном потоке
    threading.Thread(target=run_flask).start()

    # Запуск ботов
    await asyncio.gather(
        main_bot.run(),
        monitor_bot.run()
    )


if __name__ == '__main__':
    asyncio.run(main())