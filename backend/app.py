from flask import Flask, request, jsonify, render_template
import database as db
import google_calendar
import telegram_bot
import config

app = Flask(__name__)

# === API: Мастера ===
@app.route('/api/masters')
def get_masters():
    masters = db.get_all_masters()
    return jsonify(masters)

# === API: Услуги мастера ===
@app.route('/api/services/<int:master_id>')
def get_services(master_id):
    services = db.get_services_by_master(master_id)
    return jsonify(services)

# === API: Доступные даты ===
@app.route('/api/dates')
def get_available_dates():
    master_id = request.args.get('master_id', type=int)
    dates = google_calendar.get_working_days(master_id)
    return jsonify(dates)

# === API: Свободное время на дату ===
@app.route('/api/times')
def get_available_times():
    master_id = request.args.get('master_id', type=int)
    date = request.args.get('date')
    times = google_calendar.get_free_slots(master_id, date)
    return jsonify(times)

# === API: Создание записи ===
@app.route('/api/book', methods=['POST'])
def create_booking():
    data = request.json
    master_id = data['masterId']
    service_id = data['serviceId']
    date = data['date']
    time = data['time']
    full_name = data['fullName']
    phone = data['phone']
    telegram_notify = data.get('telegram', False)

    # Получаем длительность услуги
    service = db.get_service(service_id)
    duration = service['duration'] if service else 60

    # Создаём событие в Google Calendar
    event_id = google_calendar.create_event(
        master_id=master_id,
        summary=f"Запись: {full_name}",
        start_datetime=f"{date}T{time}",
        duration_minutes=duration
    )

    if not event_id:
        return jsonify({"success": False, "error": "Не удалось создать событие"}), 500

    # Сохраняем в БД
    booking_id = db.add_booking({
        'master_id': master_id,
        'service_id': service_id,
        'client_name': full_name,
        'phone': phone,
        'date': date,
        'time': time,
        'event_id_google': event_id,
        'telegram_notify': telegram_notify
    })

    if telegram_notify:
        # Можно попросить клиента подписаться позже
        pass

    return jsonify({"success": True, "booking_id": booking_id})

# === Админ-панель ===
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        master = db.authenticate_master(login, password)
        if master:
            return render_template('admin_dashboard.html', master=master)
        else:
            return render_template('admin_login.html', error="Неверный логин или пароль")
    return render_template('admin_login.html')

@app.route('/admin/data/<int:master_id>')
def admin_data(master_id):
    master = db.get_master(master_id)
    if not master:
        return "Доступ запрещён", 403
    bookings = db.get_bookings_by_master(master_id)
    working_hours = db.get_working_hours(master_id)
    services = db.get_services_by_master(master_id)
    return jsonify({
        'bookings': bookings,
        'working_hours': working_hours,
        'services': services
    })

if __name__ == '__main__':
    db.init_db()
    app.run(host='0.0.0.0', port=5000)