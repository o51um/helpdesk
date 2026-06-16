import telebot
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
from telebot import types
import pytz

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID не найден в переменных окружения!")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    pass

bot = telebot.TeleBot(BOT_TOKEN)

# Настройка временной зоны Владивосток (UTC+10)
VLADIVOSTOK_TZ = pytz.timezone('Asia/Vladivostok')

def get_current_time():
    """Возвращает текущее время во Владивостоке"""
    return datetime.now(VLADIVOSTOK_TZ).strftime("%d.%m.%Y %H:%M")

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            last_known_name TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            workplace TEXT,
            problem TEXT,
            photo_id TEXT,
            status TEXT DEFAULT 'Новая',
            created_at TEXT,
            admin_comment TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_user_name(user_id, name):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, last_known_name) 
        VALUES (?, ?)
    ''', (user_id, name))
    conn.commit()
    conn.close()

def get_user_name(user_id):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_known_name FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_ticket(user_id, name, workplace, problem, photo_id=None):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    created_at = get_current_time()  # Используем время Владивостока
    
    cursor.execute('''
        INSERT INTO tickets (user_id, name, workplace, problem, photo_id, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, workplace, problem, photo_id, created_at, 'Новая'))
    
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

def update_ticket_status(ticket_id, status, admin_comment=None):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    if admin_comment:
        cursor.execute('''
            UPDATE tickets 
            SET status = ?, admin_comment = ? 
            WHERE ticket_id = ?
        ''', (status, admin_comment, ticket_id))
    else:
        cursor.execute('''
            UPDATE tickets 
            SET status = ? 
            WHERE ticket_id = ?
        ''', (status, ticket_id))
    
    conn.commit()
    conn.close()

def get_ticket_info(ticket_id):
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticket_id, user_id, name, workplace, problem, photo_id, status, created_at, admin_comment
        FROM tickets WHERE ticket_id = ?
    ''', (ticket_id,))
    result = cursor.fetchone()
    conn.close()
    return result

user_data = {}

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if message.chat.type == 'private':
        saved_name = get_user_name(user_id)
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn1 = types.KeyboardButton('📝 Новая заявка')
        btn2 = types.KeyboardButton('📋 Мои заявки')
        markup.add(btn1, btn2)
        
        if saved_name:
            bot.reply_to(message, 
                f"👋 Привет, {saved_name}!\n"
                "Что хочешь сделать?",
                reply_markup=markup
            )
        else:
            bot.reply_to(message, 
                "👋 Привет! Давай создадим заявку о поломке.\n\n"
                "🔹 Для начала, как тебя зовут? (Имя и Фамилия)"
            )
            user_data[user_id] = {'step': 'name'}
    else:
        bot.reply_to(message, 
            "🤖 Я работаю в личных сообщениях.\n"
            "Напиши мне в личку."
        )

@bot.message_handler(func=lambda message: message.text in ['📝 Новая заявка', '📋 Мои заявки'])
def handle_buttons(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == '📝 Новая заявка':
        saved_name = get_user_name(user_id)
        if saved_name:
            bot.reply_to(message, 
                "📍 Укажи рабочее место, где произошла поломка:\n"
                "(Например: Кабинет 301, Склад, Цех №5)"
            )
            user_data[user_id] = {
                'step': 'workplace', 
                'name': saved_name
            }
        else:
            bot.reply_to(message, 
                "🔹 Как тебя зовут? (Имя и Фамилия)"
            )
            user_data[user_id] = {'step': 'name'}
    
    elif text == '📋 Мои заявки':
        show_user_tickets(message)

def show_user_tickets(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticket_id, status, problem, created_at 
        FROM tickets 
        WHERE user_id = ? 
        ORDER BY ticket_id DESC 
        LIMIT 10
    ''', (user_id,))
    tickets = cursor.fetchall()
    conn.close()
    
    if not tickets:
        bot.reply_to(message, 
            "📭 У вас пока нет заявок.\n"
            "Нажмите '📝 Новая заявка' чтобы создать."
        )
        return
    
    response = "📋 **Ваши заявки:**\n\n"
    for ticket in tickets:
        status_emoji = {
            'Новая': '🆕',
            'В работе': '🔄',
            'Принята': '✅',
            'Отклонена': '❌',
            'Завершена': '🎉'
        }.get(ticket[1], '📌')
        
        response += f"#{ticket[0]} {status_emoji} {ticket[1]}\n"
        response += f"📝 {ticket[2][:50]}...\n"
        response += f"📅 {ticket[3]} (Владивосток)\n\n"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if message.chat.type != 'private':
        return
    
    if text in ['📝 Новая заявка', '📋 Мои заявки']:
        return
    
    if user_id not in user_data:
        start(message)
        return
    
    step = user_data[user_id].get('step')
    
    if step == 'name':
        if len(text.split()) >= 2:
            user_data[user_id]['name'] = text
            save_user_name(user_id, text)
            user_data[user_id]['step'] = 'workplace'
            bot.reply_to(message, 
                f"✅ Отлично, {text}!\n\n"
                "📍 Теперь укажи рабочее место, где произошла поломка:\n"
                "(Например: ТОСП, Тополево, Обработка, 4 место)"
            )
        else:
            bot.reply_to(message, 
                "❌ Пожалуйста, введите полное имя (Имя и Фамилия).\n"
                "Например: Иван Петров"
            )
    
    elif step == 'workplace':
        user_data[user_id]['workplace'] = text
        user_data[user_id]['step'] = 'problem'
        bot.reply_to(message, 
            "🔧 Отлично! Теперь опиши суть проблемы:\n"
            "(Что именно сломалось, что не работает, и т.д.)"
        )
    
    elif step == 'problem' and not user_data[user_id].get('waiting_for_photo'):
        user_data[user_id]['problem'] = text
        bot.reply_to(message, 
            "📸 Хочешь прикрепить фото?\n"
            "Отправь фото сейчас, или нажми /skip чтобы пропустить.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        user_data[user_id]['waiting_for_photo'] = True
    
    elif text == '/skip':
        if user_data[user_id].get('waiting_for_photo'):
            finish_request(user_id)
    
    else:
        bot.reply_to(message, "⚠️ Не понимаю. Нажми /start чтобы начать.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    if message.chat.type != 'private':
        return
    
    if user_id not in user_data:
        start(message)
        return
    
    if user_data[user_id].get('waiting_for_photo'):
        file_id = message.photo[-1].file_id
        user_data[user_id]['photo'] = file_id
        
        if message.caption:
            user_data[user_id]['problem'] = message.caption.strip()
        
        finish_request(user_id)
    else:
        bot.reply_to(message, 
            "📸 Фото принято! Но сначала создай заявку через /start"
        )

@bot.message_handler(commands=['skip'])
def skip_photo(message):
    user_id = message.from_user.id
    if user_id in user_data and user_data[user_id].get('waiting_for_photo'):
        finish_request(user_id)

def finish_request(user_id):
    data = user_data[user_id]
    name = data.get('name', 'Не указано')
    workplace = data.get('workplace', 'Не указано')
    problem = data.get('problem', 'Не указано')
    photo = data.get('photo')
    
    ticket_id = save_ticket(user_id, name, workplace, problem, photo)
    
    current_time = get_current_time()  # Время Владивостока
    message_text = (
        f"🆕 **НОВАЯ ЗАЯВКА #{ticket_id}**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Заявитель:** {name}\n"
        f"📍 **Место:** {workplace}\n"
        f"🔧 **Проблема:** {problem}\n"
        f"⏰ **Время:** {current_time} (Владивосток)\n"
        f"🆔 **ID:** {user_id}\n"
    )
    
    # Кнопки для админа
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton('✅ Принята', callback_data=f'status_{ticket_id}_Принята')
    btn2 = types.InlineKeyboardButton('🔄 В работе', callback_data=f'status_{ticket_id}_В работе')
    btn3 = types.InlineKeyboardButton('🎉 Завершена', callback_data=f'status_{ticket_id}_Завершена')
    btn4 = types.InlineKeyboardButton('❌ Отклонена', callback_data=f'status_{ticket_id}_Отклонена')
    btn5 = types.InlineKeyboardButton('📝 Ответить', callback_data=f'reply_{ticket_id}')
    markup.add(btn1, btn2, btn3, btn4, btn5)
    
    try:
        if photo:
            bot.send_photo(
                ADMIN_CHAT_ID,
                photo,
                caption=message_text,
                parse_mode='Markdown',
                reply_markup=markup
            )
        else:
            bot.send_message(
                ADMIN_CHAT_ID,
                message_text,
                parse_mode='Markdown',
                reply_markup=markup
            )
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn1 = types.KeyboardButton('📝 Новая заявка')
        btn2 = types.KeyboardButton('📋 Мои заявки')
        markup.add(btn1, btn2)
        
        bot.send_message(
            user_id,
            f"✅ **Заявка #{ticket_id} успешно отправлена!**\n"
            f"Статус: 🆕 Новая\n"
            f"⏰ Время: {current_time} (Владивосток)\n\n"
            "Мы свяжемся с вами в ближайшее время.\n"
            "Статус заявки можно посмотреть в 'Мои заявки'.",
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        bot.send_message(
            user_id,
            f"❌ Ошибка при отправке заявки.\nПопробуйте позже."
        )
        print(f"Error: {e}")
    
    if user_id in user_data:
        del user_data[user_id]

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split('_')
    
    if data[0] == 'status':
        ticket_id = int(data[1])
        status = data[2]
        
        update_ticket_status(ticket_id, status)
        
        ticket = get_ticket_info(ticket_id)
        if ticket:
            user_id = ticket[1]
            name = ticket[2]
            
            status_emoji = {
                'Новая': '🆕',
                'В работе': '🔄',
                'Принята': '✅',
                'Отклонена': '❌',
                'Завершена': '🎉'
            }.get(status, '📌')
            
            # Отправляем уведомление пользователю
            try:
                if status == 'Завершена':
                    extra_msg = "\n🎉 Заявка выполнена! Спасибо за обращение."
                elif status == 'Отклонена':
                    extra_msg = "\n❌ Заявка отклонена. Если есть вопросы, обратитесь к администратору."
                elif status == 'Принята':
                    extra_msg = "\n✅ Заявка принята в работу."
                elif status == 'В работе':
                    extra_msg = "\n🔄 Начата работа над заявкой."
                else:
                    extra_msg = ""
                
                bot.send_message(
                    user_id,
                    f"📢 **Обновление статуса заявки #{ticket_id}**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Заявитель: {name}\n"
                    f"📌 Новый статус: {status_emoji} {status}{extra_msg}\n"
                    f"⏰ {get_current_time()} (Владивосток)\n\n"
                    f"Нажмите '📋 Мои заявки' для просмотра всех заявок.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Не удалось уведомить пользователя: {e}")
            
            bot.answer_callback_query(call.id, f"Статус изменён на '{status}'")
            
            # Обновляем кнопки
            new_markup = types.InlineKeyboardMarkup(row_width=3)
            statuses = [
                ('✅ Принята', 'Принята'),
                ('🔄 В работе', 'В работе'),
                ('🎉 Завершена', 'Завершена'),
                ('❌ Отклонена', 'Отклонена')
            ]
            
            if status != 'Завершена':
                for label, s in statuses:
                    if s == status:
                        new_markup.add(types.InlineKeyboardButton(
                            f'✅ {status}', 
                            callback_data='info'
                        ))
                    else:
                        new_markup.add(types.InlineKeyboardButton(
                            label, 
                            callback_data=f'status_{ticket_id}_{s}'
                        ))
                new_markup.add(types.InlineKeyboardButton('📝 Ответить', callback_data=f'reply_{ticket_id}'))
            else:
                new_markup.add(types.InlineKeyboardButton(
                    '🎉 Завершена', 
                    callback_data='info'
                ))
                new_markup.add(types.InlineKeyboardButton('📝 Ответить', callback_data=f'reply_{ticket_id}'))
            
            try:
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=new_markup
                )
            except:
                pass
    
    elif data[0] == 'reply':
        ticket_id = int(data[1])
        msg = bot.send_message(
            call.message.chat.id,
            f"📝 Введите комментарий для заявки #{ticket_id}:"
        )
        bot.register_next_step_handler(msg, process_admin_reply, ticket_id)
        bot.answer_callback_query(call.id, "Введите ваш ответ")

def process_admin_reply(message, ticket_id):
    admin_comment = message.text
    ticket = get_ticket_info(ticket_id)
    
    if ticket:
        user_id = ticket[1]
        name = ticket[2]
        
        update_ticket_status(ticket_id, 'Принята', admin_comment)
        
        try:
            bot.send_message(
                user_id,
                f"💬 **Ответ по заявке #{ticket_id}**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Заявитель: {name}\n"
                f"📌 Ответ администратора:\n{admin_comment}\n"
                f"⏰ {get_current_time()} (Владивосток)\n\n"
                f"Нажмите '📋 Мои заявки' для просмотра всех заявок.",
                parse_mode='Markdown'
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ Ответ отправлен пользователю по заявке #{ticket_id}"
            )
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Не удалось отправить ответ пользователю. Ошибка: {e}"
            )

@bot.message_handler(commands=['stats'])
def show_stats(message):
    # Проверяем что это админ
    if str(message.from_user.id) != str(ADMIN_CHAT_ID) and message.from_user.username != 'o51um':
        bot.reply_to(message, "⛔ Доступ запрещён")
        return
    
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM tickets')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT status, COUNT(*) FROM tickets GROUP BY status')
    stats = cursor.fetchall()
    
    conn.close()
    
    response = f"📊 **Статистика заявок**\n━━━━━━━━━━━━━━━━━━━\n"
    response += f"📋 Всего: {total}\n"
    response += f"⏰ {get_current_time()} (Владивосток)\n\n"
    
    status_order = ['Новая', 'В работе', 'Принята', 'Завершена', 'Отклонена']
    status_emoji = {
        'Новая': '🆕',
        'В работе': '🔄',
        'Принята': '✅',
        'Завершена': '🎉',
        'Отклонена': '❌'
    }
    
    for status in status_order:
        count = next((s[1] for s in stats if s[0] == status), 0)
        emoji = status_emoji.get(status, '📌')
        response += f"{emoji} {status}: {count}\n"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    if message.chat.type == 'private':
        bot.reply_to(message, 
            "🤖 Нажми /start чтобы начать."
        )

if __name__ == "__main__":
    init_db()
    print("🤖 Бот запущен и готов к работе!")
    print(f"📨 Заявки будут отправляться в: {ADMIN_CHAT_ID}")
    print(f"⏰ Временная зона: Владивосток (UTC+10)")
    print(f"🕐 Текущее время: {get_current_time()}")
    print("\n📌 Команды:")
    print("   /start - Главное меню")
    print("   /stats - Статистика (только для админа)")
    bot.polling(none_stop=True)