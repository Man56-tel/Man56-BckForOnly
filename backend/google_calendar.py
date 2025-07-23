import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import database as db
import config

# Область доступа
SCOPES = ['https://www.googleapis.com/auth/calendar ']

def get_calendar_service(master_id):
    """Получаем service для Google Calendar (по мастеру)"""
    creds = None
    token_path = f'token_master_{master_id}.pickle'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

def get_working_days(master_id):
    """Возвращаем список доступных дат (на основе рабочих дней из БД)"""
    working_hours = db.get_working_hours(master_id)
    days_active = {item['day_of_week'] for item in working_hours}

    dates = []
    today = datetime.date.today()
    for i in range(30):  # на 30 дней вперёд
        date = today + datetime.timedelta(days=i)
        if date.weekday() in days_active:
            dates.append(date.isoformat())
    return dates

def get_free_slots(master_id, date_str):
    """Получаем свободные слоты на указанную дату"""
    master = db.get_master(master_id)
    service = get_calendar_service(master_id)

    start_time = "09:00"  # временно, можно вынести в БД
    end_time = "19:00"

    # Получим рабочее время из БД
    wh = db.get_working_hours(master_id)
    day_of_week = datetime.datetime.strptime(date_str, '%Y-%m-%d').weekday()
    wh_day = [h for h in wh if h['day_of_week'] == day_of_week]
    if wh_day:
        start_time = wh_day[0]['start_time']
        end_time = wh_day[0]['end_time']
        break_start = wh_day[0].get('break_start')
        break_end = wh_day[0].get('break_end')
    else:
        return []

    start_dt = f"{date_str}T{start_time}:00"
    end_dt = f"{date_str}T{end_time}:00"

    body = {
        "timeMin": start_dt + '+03:00',
        "timeMax": end_dt + '+03:00',
        "items": [{"id": master['calendar_id']}],
        "singleEvents": True,
        "orderBy": "startTime"
    }

    events_result = service.freebusy().query(body=body).execute()
    busy = events_result.get('calendars', {}).get(master['calendar_id'], {}).get('busy', [])
    
    free_slots = []
    current = datetime.datetime.fromisoformat(f"{date_str}T{start_time}:00")
    end = datetime.datetime.fromisoformat(f"{date_str}T{end_time}:00")

    duration = datetime.timedelta(minutes=30)

    while current + duration <= end:
        slot_start = current
        slot_end = current + duration

        # Проверка перерыва
        if break_start and break_end:
            break_start_dt = datetime.datetime.fromisoformat(f"{date_str}T{break_start}:00")
            break_end_dt = datetime.datetime.fromisoformat(f"{date_str}T{break_end}:00")
            if break_start_dt <= slot_start < break_end_dt:
                current += duration
                continue

        # Проверка занятости
        is_busy = False
        for event in busy:
            ev_start = datetime.datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            ev_end = datetime.datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
            if ev_start.tzinfo:
                ev_start = ev_start.astimezone().replace(tzinfo=None)
                ev_end = ev_end.astimezone().replace(tzinfo=None)
            if slot_start < ev_end and slot_end > ev_start:
                is_busy = True
                break

        if not is_busy:
            free_slots.append(current.strftime('%H:%M'))

        current += duration

    return free_slots

def create_event(master_id, summary, start_datetime, duration_minutes):
    """Создаём событие в календаре"""
    master = db.get_master(master_id)
    service = get_calendar_service(master_id)

    start = f"{start_datetime}:00"
    end = (datetime.datetime.fromisoformat(start) + datetime.timedelta(minutes=duration_minutes)).isoformat()

    event = {
        'summary': summary,
        'start': {'dateTime': start, 'timeZone': 'Europe/Moscow'},
        'end': {'dateTime': end, 'timeZone': 'Europe/Moscow'}
    }

    try:
        event = service.events().insert(calendarId=master['calendar_id'], body=event).execute()
        return event.get('id')
    except Exception as e:
        print(f"Ошибка создания события: {e}")
        return None