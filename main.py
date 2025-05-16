import os
import telebot
from telebot import types
import random
from datetime import datetime, timedelta
import pytz
import threading
import time
import logging

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "7507582678:AAGc6onDmF5X5kyyZmOyjPXb7ob9lrBkoCQ"
PHOTO_REVIEW_GROUP_ID = -1002498200426
ACTIVITY_GROUP_ID = -1002296054466
LOG_CHAT_ID = 7823280397

# Инициализация бота
bot = telebot.TeleBot(TOKEN, parse_mode="MarkdownV2")
gif_url = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xhaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'

# Призы и вес
prizes = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('70 звезд!', 5)
]

# Экранирование MarkdownV2
def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

# Хранилища
message_owners = {}
claimed_messages = set()
user_activity = {}
user_activity_lock = threading.Lock()
last_award_hour = None
kz_tz = pytz.timezone('Asia/Almaty')

def choose_random_prize():
    return random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

# Обработка фотоотзывов
@bot.message_handler(content_types=['photo'], chat_id=PHOTO_REVIEW_GROUP_ID)
def handle_photo_review(message):
    try:
        if not message.caption or len(message.caption.strip()) < 5:
            bot.reply_to(message, "❌ Пожалуйста, добавьте текстовое описание к фото (минимум 5 символов).")
            return

        msg_id = message.message_id
        user_id = message.from_user.id
        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(message, "Спасибо за отзыв! Нажми кнопку, чтобы получить приз 🎁", reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Ошибка фото: {str(e)}")

# Кнопка призов
@bot.callback_query_handler(func=lambda call: call.data.startswith('spin:'))
def handle_spin(call):
    try:
        msg_id = int(call.data.split(':')[1])
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name

        if msg_id in claimed_messages:
            bot.answer_callback_query(call.id, "⚠️ Приз уже был получен!")
            return

        if message_owners.get(msg_id) != user_id:
            bot.answer_callback_query(call.id, "❌ Только автор может получить приз!", show_alert=True)
            return

        prize = choose_random_prize()
        claimed_messages.add(msg_id)

        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )

        username_md = escape_markdown_v2(username)
        prize_md = escape_markdown_v2(prize)

        bot.send_animation(call.message.chat.id, gif_url)
        bot.send_message(call.message.chat.id, f"🎉 @{username_md}, твой приз: *{prize_md}*")
        bot.send_message(LOG_CHAT_ID, f"🎁 Приз: *{prize_md}*\n👤 Пользователь: @{username_md}")

        bot.answer_callback_query(call.id)

    except Exception as e:
        logger.error(f"Ошибка callback: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка при обработке!", show_alert=True)

# Учёт активности
@bot.message_handler(content_types=['text'], chat_id=ACTIVITY_GROUP_ID)
def handle_activity(message):
    try:
        if message.from_user.is_bot:
            return

        user_id = message.from_user.id
        with user_activity_lock:
            user_activity[user_id] = user_activity.get(user_id, 0) + 1

    except Exception as e:
        logger.error(f"Ошибка активности: {str(e)}")

# Цикл награждения
def activity_award_loop():
    global last_award_hour
    allowed_hours = [11, 14, 17, 20]

    while True:
        try:
            now = datetime.now(kz_tz)
            current_hour = now.hour

            if current_hour in allowed_hours and current_hour != last_award_hour:
                top_user = None
                msg_count = 0

                with user_activity_lock:
                    if user_activity:
                        top_user, msg_count = max(user_activity.items(), key=lambda x: x[1])

                if top_user is not None:
                    try:
                        user_info = bot.get_chat_member(ACTIVITY_GROUP_ID, top_user).user
                        username = user_info.username or user_info.first_name
                        prize = choose_random_prize()

                        username_md = escape_markdown_v2(username)
                        prize_md = escape_markdown_v2(prize)

                        bot.send_animation(ACTIVITY_GROUP_ID, gif_url)
                        bot.send_message(
                            ACTIVITY_GROUP_ID,
                            f"🎊 @{username_md}, ты самый активный за последние 3 часа!\n"
                            f"💬 Сообщений: *{msg_count}*\n"
                            f"🎁 Приз: *{prize_md}*"
                        )
                        bot.send_message(
                            LOG_CHAT_ID,
                            f"🏆 Приз за активность: *{prize_md}*\n👤 @{username_md}\n💬 Сообщений: *{msg_count}*"
                        )

                        with user_activity_lock:
                            user_activity.clear()
                        last_award_hour = current_hour

                    except Exception as e:
                        logger.error(f"Ошибка награды: {str(e)}")

            time.sleep(60)

        except Exception as e:
            logger.error(f"Критическая ошибка наградного цикла: {str(e)}")
            time.sleep(300)

# Запуск потока
thread = threading.Thread(target=activity_award_loop, daemon=True)
thread.start()

# Запуск бота
if __name__ == '__main__':
    logger.info("✅ Бот запущен")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Бот упал с ошибкой: {str(e)}")
