import telegram
from telegram.ext import Updater, CommandHandler
import datetime
import database as db
import config
import threading
from apscheduler.schedulers.background import BackgroundScheduler

bot = telegram.Bot(token=config.TELEGRAM_TOKEN)
scheduler = BackgroundScheduler()

def start(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text="Вы подписались на напоминания!")
    # Сохраняем chat_id клиента, если он дал согласие
    conn = sqlite3.connect('bookings.db')
    cur = conn.cursor()
    # Это упрощённо — в реальности нужно привязать к клиенту
    # Можно добавить таблицу client_notifications(chat_id, phone_or_name)
    conn.close()

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
        WHERE b.date = ? AND b.telegram_notify = 1 AND b.chat_id IS NOT NULL
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
            bot.send_message(chat_id=book['chat_id'], text=message)
        except Exception as e:
            print(f"Не удалось отправить в чат {book['chat_id']}: {e}")

def start_bot():
    """Запуск Telegram-бота в фоне"""
    if not config.TELEGRAM_TOKEN or config.TELEGRAM_TOKEN == "TOKEN_TELEGRAMM":
        print("Токен Telegram не задан — бот не запущен.")
        return

    updater = Updater(config.TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    
    thread = threading.Thread(target=updater.start_polling, daemon=True)
    thread.start()
    print("Telegram-бот запущен.")

    # Запуск напоминаний каждый день в 9:00
    scheduler.add_job(send_reminders, 'cron', hour=9, minute=0)
    scheduler.start()