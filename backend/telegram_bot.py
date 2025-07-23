from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import datetime
import sqlite3
import config
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# Глобальная переменная для хранения Application
application = None

async def start(update: Update, context):
    chat_id = update.effective_chat.id
    await update.message.reply_text("Вы подписались на напоминания!")
    # Здесь можно сохранить chat_id в БД, если нужно

def send_reminders():
    """Отправляем напоминания за день до визита"""
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    conn = sqlite3.connect('bookings.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT b.*, m.name as master_name, s.name as service_name 
        FROM bookings b
        JOIN masters m ON b.master_id = m.id
        JOIN services s ON b.service_id = s.id
        WHERE b.date = ? AND b.telegram_notify = 1
    """, (tomorrow,))
    bookings = [dict(row) for row in cur.fetchall()]
    conn.close()

    for book in bookings:
        message = f"""
🔔 Напоминание!

Вы записаны к {book['master_name']} завтра в {book['time']}.
Услуга: {book['service_name']}

Ждём вас!
        """.strip()
        try:
            application.bot.send_message(chat_id=book['chat_id'], text=message)
        except Exception as e:
            print(f"Не удалось отправить в чат {book['chat_id']}: {e}")

def start_bot():
    """Запуск Telegram-бота в фоне"""
    if not config.TELEGRAM_TOKEN or config.TELEGRAM_TOKEN == "TOKEN_TELEGRAMM":
        print("Токен Telegram не задан — бот не запущен.")
        return

    global application
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    # Запускаем polling в фоновом потоке
    from threading import Thread
    thread = Thread(target=application.run_polling, daemon=True)
    thread.start()
    print("Telegram-бот запущен.")

    # Назначаем задачу на 9:00 ежедневно
    scheduler.add_job(send_reminders, 'cron', hour=9, minute=0)
    scheduler.start()
