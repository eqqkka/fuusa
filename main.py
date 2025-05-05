import os
import telebot
from telebot import types
import random
from datetime import datetime, timedelta
import pytz
import threading
import time

# Получаем токен из переменной окружения или пропиши напрямую:
TOKEN = os.getenv("BOT_TOKEN") or "7507582678:AAFoG380Rso0qT14nJnWD6LgQH3wfEuTeTA"

# Группы
PHOTO_REVIEW_GROUP_ID = -1002498200426  # замените на ID группы для фотоотзывов
ACTIVITY_GROUP_ID = -1002296054466      # группа для активности
LOG_CHAT_ID = 7823280397                # чат для логов

bot = telebot.TeleBot(TOKEN)

GIF_URL = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xoaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'

prizes = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('70 звезд!', 5)
]

# Хранилища
message_owners = {}
claimed_messages = set()
user_activity = {}
last_award_time = None

# Временная зона
kz_tz = pytz.timezone('Asia/Almaty')

def choose_random_prize():
    return random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

# Обработка фотоотзывов
@bot.message_handler(content_types=['photo'])
def handle_photo_review(message):
    if message.chat.id == PHOTO_REVIEW_GROUP_ID and message.caption:
        msg_id = message.message_id
        user_id = message.from_user.id
        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("\ud83c\udf81 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(message, "Спасибо за отзыв! Нажми кнопку, чтобы получить приз \ud83c\udf81", reply_markup=markup)

# Кнопка получения приза за отзыв
@bot.callback_query_handler(func=lambda call: call.data.startswith('spin:'))
def handle_spin(call):
    msg_id = int(call.data.split(':')[1])
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    if msg_id in claimed_messages:
        bot.answer_callback_query(call.id, "Приз уже был выдан за это сообщение.")
        return

    if message_owners.get(msg_id) != user_id:
        bot.answer_callback_query(call.id, "Только автор отзыва может получить приз!", show_alert=True)
        return

    prize = choose_random_prize()
    claimed_messages.add(msg_id)

    bot.send_animation(call.message.chat.id, GIF_URL)
    bot.send_message(call.message.chat.id, f"\ud83c\udf89 @{username}, твой приз: *{prize}*", parse_mode="Markdown")
    bot.send_message(LOG_CHAT_ID, f"\ud83c\udf81 Приз: *{prize}*\n\ud83d\udc64 Пользователь: @{username}", parse_mode="Markdown")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.answer_callback_query(call.id)

# Учёт активности
@bot.message_handler(content_types=['text'])
def handle_activity(message):
    if message.chat.id == ACTIVITY_GROUP_ID:
        user_id = message.from_user.id
        user_activity[user_id] = user_activity.get(user_id, 0) + 1

# Таймер выдачи приза за активность

def activity_award_loop():
    global last_award_time

    # Часы выдачи призов (по Алматы)
    award_hours_weekdays = [8, 11, 14, 17, 20]
    award_hours_weekends = [11, 14, 17, 20]

    while True:
        now = datetime.now(kz_tz)
        weekday = now.weekday()  # 0 = Monday, 6 = Sunday
        current_hour = now.hour
        current_minute = now.minute

        # Выбираем подходящие часы для текущего дня
        allowed_hours = award_hours_weekdays if weekday < 5 else award_hours_weekends

        # Если сейчас нужный час и не выдавался приз в этом часу
        if current_hour in allowed_hours:
            if last_award_time is None or last_award_time.hour != current_hour or (now - last_award_time).seconds > 3600:
                if user_activity:
                    try:
                        # Определяем самого активного
                        top_user = max(user_activity.items(), key=lambda x: x[1])[0]
                        user_info = bot.get_chat_member(ACTIVITY_GROUP_ID, top_user).user
                        username = user_info.username or user_info.first_name

                        # Выдаём приз
                        prize = choose_random_prize()
                        bot.send_animation(ACTIVITY_GROUP_ID, GIF_URL)
                        bot.send_message(
                            ACTIVITY_GROUP_ID,
                            f"🎊 @{username}, ты самый активный за последние 3 часа! Твой приз: *{prize}*",
                            parse_mode="Markdown"
                        )
                        bot.send_message(
                            LOG_CHAT_ID,
                            f"🏆 Приз за активность: *{prize}*\n👤 @{username}",
                            parse_mode="Markdown"
                        )

                        user_activity.clear()
                        last_award_time = now

                    except Exception as e:
                        bot.send_message(LOG_CHAT_ID, f"Ошибка при выдаче приза за активность:\n{e}")
                else:
                    # Если нет сообщений — просто лог
                    last_award_time = now
                    bot.send_message(LOG_CHAT_ID, f"⏰ {now.strftime('%H:%M')} — активных пользователей не было.")
        time.sleep(60)

# Запускаем таймер в отдельном потоке
threading.Thread(target=activity_award_loop, daemon=True).start()

# Запуск бота
bot.polling(none_stop=True)
