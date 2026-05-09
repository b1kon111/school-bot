import telebot
from telebot import types
import json
import os
from datetime import datetime
import pytz
import schedule
import time
import threading
import holidays

# --- НАСТРОЙКИ ВРЕМЕНИ ---
TIMEZONE = pytz.timezone('Asia/Almaty')
REMINDER_TIME = "08:00"
MARK_START = 8  # Час начала отметки
MARK_END = 9    # Час окончания отметки

def get_today():
    now = datetime.now(TIMEZONE)
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    return days[now.weekday()]

# --- ПРОВЕРКА ВЫХОДНЫХ И ПРАЗДНИКОВ ---
def is_weekend_or_holiday():
    """Проверяет, является ли сегодня выходным днём или праздником в Казахстане"""
    now = datetime.now(TIMEZONE)
    today_date = now.date()
    
    # Проверка выходных (суббота и воскресенье)
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return True, "выходной день (суббота/воскресенье)"
    
    # Проверка праздников Казахстана
    kz_holidays = holidays.Kazakhstan(years=today_date.year)
    if today_date in kz_holidays:
        holiday_name = kz_holidays.get(today_date)
        return True, f"государственный праздник ({holiday_name})"
    
    return False, ""

def get_holiday_info():
    """Возвращает информацию о сегодняшнем дне"""
    now = datetime.now(TIMEZONE)
    today_date = now.date()
    is_holiday, reason = is_weekend_or_holiday()
    
    if is_holiday:
        return f"🚫 <b>Сегодня {reason}.</b> Отметка недоступна."
    return None

# --- НАСТРОЙКИ БОТА ---
TOKEN = '8798484496:AAFXcnWcdKVv3RE31DqN4CKOQUZ47hqhpvs'
DATA_FILE = 'class_db.json'
ADMIN_IDS = [1701265587]  

bot = telebot.TeleBot(TOKEN)

# --- СПИСОК ВСЕХ КНОПОК МЕНЮ (для защиты ввода) ---
MENU_BUTTONS = [
    "📝 Отметиться", "👤 Профиль", "🆘 Помощь", 
    "✏️ Панель старосты", "📋 Список класса", "✏️ Отметить ученика", 
    "🗑️ Удалить ученика", "✏️ Редактировать ученика", "➕ Добавить ученика", "📊 Статистика", 
    "⬅️ Назад в меню", "⬅️ Назад"
]

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
            if 'allowed_users' not in db: db['allowed_users'] = {}
            if 'user_map' not in db: db['user_map'] = {}
            if 'attendance' not in db: db['attendance'] = {}
            if 'users' not in db: db['users'] = {}
            return db
    return {
        "users": {}, "user_map": {}, "attendance": {},
        "allowed_users": {
            "damikiri": "Асанова Дамира", "berriikova": "Берикова Аяна",
            "klawluv": "Жумагазина Анеля", "tolenova_a": "Толенова Тамина",
            "vnlxbb": "Султан Ботагоз", "Qwanxx": "Бегалиеев Куаныш",
            "ayttax": "Кайраткызы Акбота", "aikoshyymm": "Асанхан Аяру",
            "inkxqs": "Абдешова Инабат", "karymsakov17": "Карымсаков Нурдаулет",
            "r4ven_25": "Дубаев Чингиз", "muratovv4": "Мурат Али",
            "nurhzx": "Ундаганов Нурали", "zk1eem": "Кылышбай Жаннур",
            "userk1mi": "Цой Тимур", "ts9qq": "Иманов Диас",
            "amywthh": "Каир Айнара", "madiinasw": "Кенизбай Мадина",
            "ka_ayon": "Касым Аянат", "mxsrm5": "Нсангалиева Мариям",
            "lamivh": "Нуртазин Ерзат", "jdaiaw": "Самат Меирбек",
            "ser1kovnn": "Бакитова Саида", "zhakonaq": "Алибек Жаннур",
            "zk_2312": "Амантаева Инжу", "abix_gg": "Турлан Абылай",
            "shotbikon": "Ерниязов Бекжан", "lokeie": "Кыдыралин Даулет"
        }
    }

def save_db(db):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
        
def is_admin(uid):
    db = load_db()
    username = db['user_map'].get(str(uid))
    return username in {"damikiri", "tolenova_a", "shotbikon"}

# --- МЕНЮ ---
def get_student_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Отметиться", "👤 Профиль")
    markup.add("🆘 Помощь")
    return markup

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Отметиться", "👤 Профиль")
    markup.add("✏️ Панель старосты")
    markup.add("📋 Список класса")
    markup.add("🆘 Помощь")
    return markup

# --- КОМАНДА /start ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = str(message.from_user.id)
    raw_username = message.from_user.username
    db = load_db()

    if not raw_username:
        bot.reply_to(message, "⛔ У тебя не установлен юзернейм в профиле Telegram! Без него бот тебя не узнает.")
        return

    username_lower = raw_username.lower()

    if username_lower not in db['allowed_users']:
        bot.reply_to(message, "⛔ Тебя нет в списке класса.")
        return

    fio = db['allowed_users'][username_lower]
    db['users'][uid] = fio
    db['user_map'][uid] = username_lower
    save_db(db)

    if is_admin(uid):
        menu = get_admin_menu()
    else:
        menu = get_student_menu()

    bot.send_message(message.chat.id, f"Привет, <b>{fio}</b>!", reply_markup=menu, parse_mode='HTML')

# --- ПРОФИЛЬ ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def show_profile(message):
    uid = str(message.from_user.id)
    db = load_db()
    if uid not in db['users']: return

    fio = db['users'][uid]
    today = get_today()
    today_status = "Не отмечен"

    total_present = 0
    total_absent = 0
    total_late = 0

    for day, data in db['attendance'].items():
        if uid in data:
            entry = data[uid]
            if isinstance(entry, dict):
                status = entry.get('status')
                reason = entry.get('reason')
            else:
                status = entry
                reason = None

            if status == 'present': total_present += 1
            elif status == 'absent': total_absent += 1
            elif status == 'late': total_late += 1

            if day == today:
                if status == 'present': today_status = "✅ Присутствует"
                elif status == 'absent':
                    today_status = "❌ Отсутствует"
                    if reason:
                        today_status += f"\nПричина: {reason}"
                elif status == 'late':
                    today_status = "⏰ Опоздал"
                    if reason:
                        today_status += f"\nПричина: {reason}"

    profile_text = f"👤 <b>Профиль: {fio}</b>\n\n"
    profile_text += f"📅 Статус сегодня: {today_status}\n\n"
    profile_text += f"✅ Присутствовал: {total_present} раз\n"
    profile_text += f"❌ Отсутствовал: {total_absent} раз\n"
    profile_text += f"⏰ Опоздал: {total_late} раз"

    bot.send_message(message.chat.id, profile_text, parse_mode='HTML')

# --- ОТМЕТИТЬСЯ (ДЛЯ ВСЕХ) ---
@bot.message_handler(func=lambda m: m.text == "📝 Отметиться")
def mark_self(message):
    uid = str(message.from_user.id)
    db = load_db()
    if uid not in db['users']: return

    # НОВОЕ: Проверка выходных и праздников
    is_holiday, reason = is_weekend_or_holiday()
    if is_holiday:
        bot.send_message(message.chat.id, f"🚫 <b>Сегодня {reason}.</b>\nОтметка недоступна в выходные дни и праздники!", parse_mode='HTML')
        return

    # НОВОЕ: Проверка времени (07:00 - 09:00)
    now = datetime.now(TIMEZONE)
    if not (MARK_START <= now.hour < MARK_END):
        bot.send_message(message.chat.id, f"⛔ Отмечаться можно только с {MARK_START}:00 до {MARK_END}:00 утра!")
        return

    day = get_today()
    # Проверка, отмечался ли уже сегодня
    if day in db['attendance'] and uid in db['attendance'][day]:
        bot.send_message(message.chat.id, "⚠️ Ты уже отмечался сегодня! Можно отмечаться только один раз в день.", 
                         reply_markup=get_admin_menu() if is_admin(uid) else get_student_menu())
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("✅ Я на уроке", "❌ Не смогу прийти", "⏰ Я опоздаю")
    markup.add("⬅️ Назад")
    bot.send_message(message.chat.id, f"📅 <b>{get_today()}</b>\nВыбери статус:", 
                     reply_markup=markup, parse_mode='HTML')

# --- ОБРАБОТКА СТАТУСОВ УЧЕНИКА ---
@bot.message_handler(func=lambda m: m.text in ["✅ Я на уроке", "❌ Не смогу прийти", "⏰ Я опоздаю"])
def set_student_status(message):
    uid = str(message.from_user.id)
    db = load_db()
    day = get_today()

    # НОВОЕ: Проверка выходных и праздников
    is_holiday, reason = is_weekend_or_holiday()
    if is_holiday:
        bot.send_message(message.chat.id, f"🚫 <b>Сегодня {reason}.</b>\nОтметка недоступна!", parse_mode='HTML', 
                         reply_markup=get_admin_menu() if is_admin(uid) else get_student_menu())
        return

    # Защита: Проверка времени и повторной отметки
    now = datetime.now(TIMEZONE)
    if not (MARK_START <= now.hour < MARK_END):
        bot.send_message(message.chat.id, f"⛔ Время отметки (с {MARK_START}:00 до {MARK_END}:00) вышло!")
        return

    if day in db['attendance'] and uid in db['attendance'][day]:
        bot.send_message(message.chat.id, "⚠️ Ты уже отмечался сегодня!", 
                         reply_markup=get_admin_menu() if is_admin(uid) else get_student_menu())
        return

    status_map = {
        "✅ Я на уроке": "present",
        "❌ Не смогу прийти": "absent",
        "⏰ Я опоздаю": "late"
    }

    status = status_map[message.text]
    if day not in db['attendance']: db['attendance'][day] = {}
    db['attendance'][day][uid] = {"status": status}
    save_db(db)

    text_map = {
        "present": "✅ Ты отмечен как присутствующий!",
        "absent": "❌ Ты отмечен как отсутствующий.",
        "late": "⏰ Ты отмечен как опоздавший."
    }

    if status in {"absent", "late"}:
        msg = bot.send_message(message.chat.id, f"{text_map[status]}\n\n📝 Напиши причину {('опоздания' if status == 'late' else 'отсутствия')}:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_reason, day, uid)
        return

    bot.send_message(message.chat.id, text_map[status], 
                     reply_markup=get_admin_menu() if is_admin(uid) else get_student_menu())

def process_reason(message, day, uid):
    if message.text in MENU_BUTTONS:
        bot.send_message(message.chat.id, "❌ Действие отменено.")
        if is_admin(message.from_user.id):
            admin_panel(message)
        else:
            bot.send_message(message.chat.id, "Меню:", reply_markup=get_student_menu())
        return

    reason = message.text.strip()
    if not reason:
        bot.send_message(message.chat.id, "⚠️ Пожалуйста, введи причину.")
        return

    db = load_db()
    if day in db['attendance'] and uid in db['attendance'][day]:
        entry = db['attendance'][day][uid]
        if isinstance(entry, dict):
            entry['reason'] = reason
        else:
            db['attendance'][day][uid] = {"status": entry, "reason": reason}
        save_db(db)

    bot.send_message(message.chat.id, f"✅ Причина сохранена: {reason}", reply_markup=get_admin_menu() if is_admin(uid) else get_student_menu())

# --- ПАНЕЛЬ СТАРОСТЫ ---
@bot.message_handler(func=lambda m: m.text == "✏️ Панель старосты")
def admin_panel(message):
    if not is_admin(message.from_user.id): return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✏️ Отметить ученика")
    markup.add("📋 Список класса")
    markup.add("🗑️ Удалить ученика", "✏️ Редактировать ученика")
    markup.add("➕ Добавить ученика", "📊 Статистика")
    markup.add("⬅️ Назад в меню")
    bot.send_message(message.chat.id, "👑 <b>Панель старосты</b>", reply_markup=markup, parse_mode='HTML')

# --- СПИСОК ДЛЯ ОТМЕТКИ ---
@bot.message_handler(func=lambda m: m.text == "✏️ Отметить ученика")
def mark_manually_start(message):
    if not is_admin(message.from_user.id): return

    db = load_db()
    markup = types.InlineKeyboardMarkup(row_width=2)

    users_sorted = sorted(db['allowed_users'].items(), key=lambda x: x[1])

    for username, fio in users_sorted:
        btn = types.InlineKeyboardButton(text=fio, callback_data=f"choose_un_{username}")
        markup.add(btn)

    bot.send_message(message.chat.id, "Выбери ученика:", reply_markup=markup)

# --- ДОБАВЛЕНИЕ УЧЕНИКА ---
@bot.message_handler(func=lambda m: m.text == "➕ Добавить ученика")
def add_user_start(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "Введи данные в формате:\n`@юзернейм Фамилия Имя`\n\nНапример: `@newuser Новый Ученик`")
    bot.register_next_step_handler(msg, process_add_user)

def process_add_user(message):
    # НОВОЕ: Если нажали кнопку меню во время ввода
    if message.text in MENU_BUTTONS:
        bot.send_message(message.chat.id, "❌ Действие отменено.")
        # Возвращаем в нужное меню
        if is_admin(message.from_user.id):
            admin_panel(message)
        else:
            bot.send_message(message.chat.id, "Меню:", reply_markup=get_student_menu())
        return

    try:
        parts = message.text.split(maxsplit=1)
        username = parts[0].replace('@', '').lower()
        fio = parts[1]

        # 🔑 КЛЮЧ: Получаем ID из Telegram по юзернейму
        try:
            user_info = bot.get_chat(f"@{username}")
            user_id = str(user_info.id)
        except:
            bot.send_message(message.chat.id, "❌ Пользователь с таким юзернеймом не найден в Telegram. Проверь опечатки!")
            return

        db = load_db()
        if username in db['allowed_users']:
            bot.send_message(message.chat.id, "⚠️ Этот ученик уже есть в базе!")
            return

        # 💾 Сохраняем полную информацию (даже если /start не нажимал)
        db['allowed_users'][username] = fio
        db['user_map'][user_id] = username      # ← Теперь бот знает ID!
        db['users'][user_id] = fio               # ← Для статистики
        save_db(db)

        # 📨 Отправляем приветствие ученику (даже если он ещё не писал боту)
        try:
            menu = get_admin_menu() if username in {"damikiri", "tolenova_a", "shotbikon"} else get_student_menu()
            bot.send_message(user_id, f"👋 Привет, <b>{fio}</b>!\n\nТебя добавили в систему отмечания 📝\n\n✅ Теперь ты можешь:\n• 📝 Отметиться на уроке\n• 👤 Посмотреть свой профиль\n• 🆘 Получить помощь\n\n⏰ Напоминание: отметиться можно с 8:00 до 9:00 каждый день!", reply_markup=menu, parse_mode='HTML')
            bot.send_message(message.chat.id, f"✅ Ученик <b>{fio}</b> (@{username}) добавлен!\n🔔 Приветствие отправлено в ЛС", parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Ученик <b>{fio}</b> (@{username}) добавлен в базу, но не удалось отправить приветствие в ЛС.\n\n❓ Возможные причины:\n• Приватный чат заблокирован\n• Блокировка бота\n\n💡 Попросите ученика написать боту /start", parse_mode='HTML')
        admin_panel(message)

    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Ошибка формата. Используй: `@юзернейм Фамилия Имя`")

# --- СТАТИСТИКА ---
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def show_stats(message):
    if not is_admin(message.from_user.id): return
    day = get_today()
    db = load_db()
    today_data = db['attendance'].get(day, {})

    total = len(db['allowed_users'])
    marked = len(today_data)

    report = f"📊 <b>Статистика на {day}:</b>\n"
    report += f"👥 Всего в классе: {total}\n"
    report += f"✅ Отметились: {marked}\n"
    report += f"❓ Не отметились: {total - marked}"

    bot.send_message(message.chat.id, report, parse_mode='HTML')

# --- СПИСОК КЛАССА ---
@bot.message_handler(func=lambda m: m.text == "📋 Список класса")
def class_list(message):
    if not is_admin(message.from_user.id): return

    db = load_db()
    day = get_today()
    today_data = db['attendance'].get(day, {})
    username_to_uid = {un: uid for uid, un in db['user_map'].items()}

    lines = [f"📋 <b>Список класса на {day}:</b>"]
    status_icons = {
        'present': '✅ Присутствует',
        'absent': '❌ Отсутствует',
        'late': '⏰ Опоздал'
    }

    for username, fio in sorted(db['allowed_users'].items(), key=lambda x: x[1]):
        uid = username_to_uid.get(username)
        if uid and uid in today_data:
            entry = today_data[uid]
            if isinstance(entry, dict):
                status = entry.get('status')
                reason = entry.get('reason')
            else:
                status = entry
                reason = None
            status_text = status_icons.get(status, '❓ Не отмечался')
            if reason and status in {'absent', 'late'}:
                status_text += f" (Причина: {reason})"
        elif uid:
            status_text = '❓ Не отметился'
        else:
            status_text = '⚠️ Не запускал /start'

        lines.append(f"• <b>{fio}</b> (@{username}) — {status_text}")

    bot.send_message(message.chat.id, "\n".join(lines), parse_mode='HTML')

# --- УДАЛЕНИЕ УЧЕНИКА ---
@bot.message_handler(func=lambda m: m.text == "🗑️ Удалить ученика")
def delete_student_start(message):
    if not is_admin(message.from_user.id): return

    db = load_db()
    markup = types.InlineKeyboardMarkup(row_width=2)
    for username, fio in sorted(db['allowed_users'].items(), key=lambda x: x[1]):
        markup.add(types.InlineKeyboardButton(text=fio, callback_data=f"delete_un_{username}"))

    bot.send_message(message.chat.id, "Выбери ученика для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_un_'))
def confirm_delete_student(call):
    if not is_admin(call.from_user.id): return

    username = call.data.split('_', 2)[2]
    db = load_db()
    fio = db['allowed_users'].get(username, username)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Удалить", callback_data=f"delete_confirm_{username}"))
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel"))

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Удалить ученика <b>{fio}</b> (@{username})?", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_confirm_'))
def delete_student(call):
    if not is_admin(call.from_user.id): return

    username = call.data.split('_', 2)[2]
    db = load_db()
    fio = db['allowed_users'].pop(username, None)

    for uid, un in list(db['user_map'].items()):
        if un == username:
            db['user_map'].pop(uid, None)
            db['users'].pop(uid, None)
            for day_data in db['attendance'].values():
                day_data.pop(uid, None)

    save_db(db)
    bot.answer_callback_query(call.id, f"✅ Ученик {fio or username} удалён!")
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"✅ Ученик <b>{fio or username}</b> (@{username}) удалён.", parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel_action(call):
    if not is_admin(call.from_user.id): return
    bot.answer_callback_query(call.id, "Отменено")
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Действие отменено.")

# --- РЕДАКТИРОВАНИЕ УЧЕНИКА ---
@bot.message_handler(func=lambda m: m.text == "✏️ Редактировать ученика")
def edit_student_start(message):
    if not is_admin(message.from_user.id): return

    db = load_db()
    markup = types.InlineKeyboardMarkup(row_width=2)
    for username, fio in sorted(db['allowed_users'].items(), key=lambda x: x[1]):
        markup.add(types.InlineKeyboardButton(text=fio, callback_data=f"edit_un_{username}"))

    bot.send_message(message.chat.id, "Выбери ученика для редактирования:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_un_'))
def choose_edit_student(call):
    if not is_admin(call.from_user.id): return

    username = call.data.split('_', 2)[2]
    db = load_db()
    fio = db['allowed_users'].get(username, username)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Изменить юзернейм", callback_data=f"edit_username_{username}"))
    markup.add(types.InlineKeyboardButton("Изменить ФИО", callback_data=f"edit_fio_{username}"))
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="cancel"))

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Редактировать данные ученика <b>{fio}</b> (@{username})?", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_username_'))
def ask_edit_username(call):
    if not is_admin(call.from_user.id): return

    username = call.data.split('_', 2)[2]
    db = load_db()
    fio = db['allowed_users'].get(username, username)

    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id,
                           f"Введи новый юзернейм для <b>{fio}</b> без символа @:", parse_mode='HTML')
    bot.register_next_step_handler(msg, process_edit_username, username)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_fio_'))
def ask_edit_fio(call):
    if not is_admin(call.from_user.id): return

    username = call.data.split('_', 2)[2]
    db = load_db()
    fio = db['allowed_users'].get(username, username)

    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id,
                           f"Введи новое ФИО для <b>{fio}</b> (@{username}):", parse_mode='HTML')
    bot.register_next_step_handler(msg, process_edit_fio, username)


def process_edit_username(message, old_username):
    if message.text in MENU_BUTTONS:
        bot.send_message(message.chat.id, "❌ Действие отменено.")
        if is_admin(message.from_user.id):
            admin_panel(message)
        else:
            bot.send_message(message.chat.id, "Меню:", reply_markup=get_student_menu())
        return

    new_username = message.text.replace('@', '').strip().lower()
    if not new_username:
        bot.send_message(message.chat.id, "⚠️ Неверный юзернейм. Попробуй ещё раз.")
        return

    db = load_db()
    if new_username in db['allowed_users']:
        bot.send_message(message.chat.id, "⚠️ Этот юзернейм уже используется.")
        return

    try:
        bot.get_chat(f"@{new_username}")
    except Exception:
        bot.send_message(message.chat.id, "❌ Пользователь с таким юзернеймом не найден. Проверь опечатки.")
        return

    fio = db['allowed_users'].pop(old_username, None)
    if fio is None:
        bot.send_message(message.chat.id, "⚠️ Ученик не найден.")
        return

    db['allowed_users'][new_username] = fio
    for uid, un in list(db['user_map'].items()):
        if un == old_username:
            db['user_map'][uid] = new_username
    save_db(db)

    bot.send_message(message.chat.id, f"✅ Юзернейм обновлён на @{new_username}")
    admin_panel(message)


def process_edit_fio(message, username):
    if message.text in MENU_BUTTONS:
        bot.send_message(message.chat.id, "❌ Действие отменено.")
        if is_admin(message.from_user.id):
            admin_panel(message)
        else:
            bot.send_message(message.chat.id, "Меню:", reply_markup=get_student_menu())
        return

    new_fio = message.text.strip()
    if not new_fio:
        bot.send_message(message.chat.id, "⚠️ Неверное ФИО. Попробуй ещё раз.")
        return

    db = load_db()
    if username not in db['allowed_users']:
        bot.send_message(message.chat.id, "⚠️ Ученик не найден.")
        return

    db['allowed_users'][username] = new_fio
    for uid, un in db['user_map'].items():
        if un == username:
            db['users'][uid] = new_fio
    save_db(db)

    bot.send_message(message.chat.id, f"✅ ФИО обновлено: <b>{new_fio}</b>", parse_mode='HTML')
    admin_panel(message)

# --- ОБРАБОТКА КНОПОК АДМИНА ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('choose_un_'))
def choose_student(call):
    if not is_admin(call.from_user.id): return

    username = call.data.split('_', 2)[2]
    db = load_db()
    fio = db['allowed_users'].get(username)

    student_uid = None
    for uid, un in db['user_map'].items():
        if un == username:
            student_uid = uid
            break

    if not student_uid:
        bot.answer_callback_query(call.id, f"⚠️ {fio} не писал /start!", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Присутствует", callback_data=f"set_{student_uid}_present"))
    markup.add(types.InlineKeyboardButton("❌ Отсутствует", callback_data=f"set_{student_uid}_absent"))
    markup.add(types.InlineKeyboardButton("⏰ Опоздал", callback_data=f"set_{student_uid}_late"))

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Отмечаем: <b>{fio}</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def set_status(call):
    if not is_admin(call.from_user.id): return
    
    # НОВОЕ: Проверка выходных и праздников
    is_holiday, reason = is_weekend_or_holiday()
    if is_holiday:
        bot.answer_callback_query(call.id, f"🚫 Сегодня {reason}. Отметка недоступна!", show_alert=True)
        return
    
    parts = call.data.split('_')
    student_uid = parts[1]
    status = parts[2]
    day = get_today()
    db = load_db()

    if day not in db['attendance']: db['attendance'][day] = {}
    db['attendance'][day][student_uid] = status
    save_db(db)

    name = db['users'].get(student_uid, "Ученик")
    icon = "✅" if status == "present" else "❌" if status == "absent" else "⏰"
    bot.answer_callback_query(call.id, f"{name}: {icon} Готово!")
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"{icon} <b>{name}</b> отмечен!", parse_mode='HTML')

# --- ПОМОЩЬ ---
@bot.message_handler(func=lambda m: m.text == "🆘 Помощь")
def help_cmd(message):
    uid = str(message.from_user.id)
    db = load_db()
    if uid not in db['users']: return

    help_text = "📚 <b>Справка:</b>\n\n"
    help_text += f"📝 <b>Отметиться</b> — выбери статус (с {MARK_START}:00 до {MARK_END}:00, 1 раз в день).\n"
    help_text += "👤 <b>Профиль</b> — твоя статистика.\n\n"
    help_text += "💡 <b>Предложения:</b>\n"
    help_text += "Напиши сообщение 'Предложение: ...' в этот чат, чтобы отправить идею Бекжану."

    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

# --- ПРЕДЛОЖЕНИЯ ---
@bot.message_handler(func=lambda m: m.text.lower().startswith('предложение'))
def forward_suggestion(message):
    uid = str(message.from_user.id)
    db = load_db()
    fio = db['users'].get(uid, "Неизвестный")

    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"💡 <b>Новое предложение от {fio}:</b>\n\n{message.text}", parse_mode='HTML')
        except: pass

    bot.reply_to(message, "✅ Твоё предложение отправлено Бекжану! Спасибо!")

# --- НАЗАД ---
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад в меню")
def back_to_menu(message):
    uid = str(message.from_user.id)
    if is_admin(uid):
        bot.send_message(message.chat.id, "Меню:", reply_markup=get_admin_menu())
    else:
        bot.send_message(message.chat.id, "Меню:", reply_markup=get_student_menu())

@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back_simple(message):
    uid = str(message.from_user.id)
    if is_admin(uid):
        bot.send_message(message.chat.id, "Меню:", reply_markup=get_admin_menu())
    else:
        bot.send_message(message.chat.id, "Меню:", reply_markup=get_student_menu())

# --- ФУНКЦИЯ РАССЫЛКИ ---
def send_morning_reminder():
    db = load_db()
    today = get_today()
    
    # НОВОЕ: Проверка выходных и праздников
    is_holiday, reason = is_weekend_or_holiday()
    if is_holiday:
        print(f"Рассылка пропущена: сегодня {reason}")
        return
    
    print(f"Рассылка напоминаний на {today}...")

    for uid in db['user_map'].keys():
        try:
            if day_in_attendance := db['attendance'].get(today):
                if uid in day_in_attendance:
                    continue 

            bot.send_message(uid, 
                f"📢 <b>Доброе утро!</b>\n\n"
                f"Сегодня <b>{today}</b>. Не забудь отметиться на уроке!\n"
                f"Время отметки: с {MARK_START}:00 до {MARK_END}:00 ⏰\n"
                "Нажми кнопку <b>'📝 Отметиться'</b> в меню 👇",
                parse_mode='HTML')
            time.sleep(0.1)
        except Exception as e:
            print(f"Не удалось отправить сообщение {uid}: {e}")

# --- ПОТОК ДЛЯ РАССЫЛКИ ---
def scheduler_thread():
    schedule.every().day.at(REMINDER_TIME).do(send_morning_reminder)
    
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == '__main__':
    print("Бот запущен!")
    
    t = threading.Thread(target=scheduler_thread)
    t.daemon = True
    t.start()
    
    bot.infinity_polling()