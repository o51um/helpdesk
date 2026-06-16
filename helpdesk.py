import telebot
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID не найден в переменных окружения!")

# Преобразуем в число, если это ID
try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    # Если это не число - оставляем как строку (юзернейм)
    pass

bot = telebot.TeleBot(BOT_TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            last_known_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Сохранение имени пользователя
def save_user_name(user_id, name):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, last_known_name) 
        VALUES (?, ?)
    ''', (user_id, name))
    conn.commit()
    conn.close()

# Получение сохранённого имени пользователя
def get_user_name(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_known_name FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

user_data = {}

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Если это личный чат
    if message.chat.type == 'private':
        saved_name = get_user_name(user_id)
        
        if saved_name:
            bot.reply_to(message, 
                f"👋 Привет, {saved_name}!\n"
                "Я помню тебя. Давай создадим новую заявку.\n\n"
                "📍 Укажи рабочее место, где произошла поломка:\n"
                "(Например: Кабинет 301, Склад, Цех №5)"
            )
            user_data[user_id] = {
                'step': 'workplace', 
                'name': saved_name
            }
        else:
            bot.reply_to(message, 
                "👋 Привет! Давай создадим заявку о поломке.\n\n"
                "🔹 Для начала, как тебя зовут? (Имя и Фамилия)"
            )
            user_data[user_id] = {'step': 'name'}
    else:
        # В группах предлагаем перейти в личку
        bot.reply_to(message, 
            "🤖 Я работаю в личных сообщениях.\n"
            "Напиши мне в личку."
        )

# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Игнорируем группы
    if message.chat.type != 'private':
        return
    
    if user_id not in user_data:
        start(message)
        return
    
    step = user_data[user_id].get('step')
    
    # Шаг 1: Получение имени
    if step == 'name':
        if len(text.split()) >= 2:
            user_data[user_id]['name'] = text
            save_user_name(user_id, text)
            user_data[user_id]['step'] = 'workplace'
            bot.reply_to(message, 
                f"✅ Отлично, {text}!\n\n"
                "📍 Теперь укажи рабочее место, где произошла поломка:\n"
                "(Например: ТОСП Тополево, 3 место, обработка)"
            )
        else:
            bot.reply_to(message, 
                "❌ Пожалуйста, введите полное имя (Имя и Фамилия).\n"
                "Например: Иван Петров"
            )
    
    # Шаг 2: Получение рабочего места
    elif step == 'workplace':
        user_data[user_id]['workplace'] = text
        user_data[user_id]['step'] = 'problem'
        bot.reply_to(message, 
            "🔧 Отлично! Теперь опиши суть проблемы:\n"
            "(Что именно сломалось, что не работает, и т.д.)"
        )
    
    # Шаг 3: Получение описания проблемы
    elif step == 'problem' and not user_data[user_id].get('waiting_for_photo'):
        user_data[user_id]['problem'] = text
        bot.reply_to(message, 
            "📸 Хочешь прикрепить фото?\n"
            "Просто отправь фото сейчас, или нажми /skip чтобы пропустить."
        )
        user_data[user_id]['waiting_for_photo'] = True
    
    # Обработка команды /skip
    elif text == '/skip':
        if user_data[user_id].get('waiting_for_photo'):
            finish_request(user_id)
    
    else:
        bot.reply_to(message, "⚠️ Не понимаю. Используй команду /start чтобы начать заново.")

# Обработка фото
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
            "📸 Фото принято! Но сначала опиши проблему текстом.\n"
            "Используй команду /start чтобы начать заново."
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
    
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    message_text = (
        f"🆕 **НОВАЯ ЗАЯВКА**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Заявитель:** {name}\n"
        f"📍 **Место:** {workplace}\n"
        f"🔧 **Проблема:** {problem}\n"
        f"⏰ **Время:** {current_time}\n"
        f"🆔 **ID:** {user_id}\n"
    )
    
    try:
        if photo:
            bot.send_photo(
                ADMIN_CHAT_ID,
                photo,
                caption=message_text,
                parse_mode='Markdown'
            )
        else:
            bot.send_message(
                ADMIN_CHAT_ID,
                message_text,
                parse_mode='Markdown'
            )
        
        bot.send_message(
            user_id,
            "✅ **Заявка успешно отправлена!**\n"
            "Спасибо, мы свяжемся с вами в ближайшее время.\n\n"
            "Чтобы создать новую заявку, нажмите /start",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = str(e)
        bot.send_message(
            user_id,
            f"❌ Ошибка при отправке заявки.\nПопробуйте позже или свяжитесь с администратором."
        )
        print(f"Error: {e}")
    
    if user_id in user_data:
        del user_data[user_id]

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    if message.chat.type == 'private':
        bot.reply_to(message, 
            "🤖 Используйте команду /start чтобы начать оформление заявки."
        )

if __name__ == "__main__":
    init_db()
    print("🤖 Бот запущен и готов к работе!")
    print(f"📨 Заявки будут отправляться в: {ADMIN_CHAT_ID}")
    bot.polling(none_stop=True)