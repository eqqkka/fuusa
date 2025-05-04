import telebot
from telebot import types
import random
from datetime import datetime, timedelta
import threading
import time
import pytz

TOKEN = '7507582678:AAFh76hUUGKWQr82fPcSnTzTAFZ-bIFwRKo'
bot = telebot.TeleBot(TOKEN)

# Чаты
PHOTO_REVIEW_CHAT_ID = -1002498200426  # Замените на чат для отзывов с фото
ACTIVITY_CHAT_ID = -1002296054466      # Группа для активности
LOG_CHAT_ID = 7823280397         # Лог-чат

# Призы и вероятности
prizes = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('75 звезд!', 4)
    ('100 звезд!', 1)
]

GIF_URL = 'https://media.giphy.com/media/WaExa2YxMRnyoLuITy/giphy.gif'

message_owners = {}
claimed_messages = set()
activity_counter = {}  # user_id -> count

# Часовой пояс Казахстана
kazakhstan_tz = pytz.timezone('Asia/Almaty')


# ——— Обработка фотоотзывов с подписью и кнопкой
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id != PHOTO_REVIEW_CHAT_ID:
        return
    if message.caption:
        msg_id = message.message_id
        user_id = message.from_user.id
        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(
            message,
            "Спасибо за отзыв! Нажми кнопку, чтобы получить приз 🎁",
            reply_markup=markup
        )


# ——— Кнопка получения приза за отзыв
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

    prize = random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]
    claimed_messages.add(msg_id)

    bot.send_animation(call.message.chat.id, GIF_URL)
    bot.send_message(call.message.chat.id, f"🎉 @{username}, твой приз: *{prize}*", parse_mode="Markdown")
    bot.send_message(LOG_CHAT_ID, f"🎁 Приз: *{prize}*\n👤 Пользователь: @{username}", parse_mode="Markdown")

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.answer_callback_query(call.id)


# ——— Счётчик текстовых сообщений в группе активности
@bot.message_handler(func=lambda message: message.chat.id == ACTIVITY_CHAT_ID and message.text)
def track_activity(message):
    user_id = message.from_user.id
    activity_counter[user_id] = activity_counter.get(user_id, 0) + 1


# ——— Планировщик: раздача приза активному участнику
def check_and_award_top_user():
    while True:
        now = datetime.now(kazakhstan_tz)
        weekday = now.weekday()
        hour = now.hour

        if ((weekday < 5 and 8 <= hour < 20) or (weekday >= 5 and 11 <= hour < 20)):
            if now.minute == 0 and now.hour % 3 == 0:
                if activity_counter:
                    top_user_id = max(activity_counter, key=activity_counter.get)
                    user_info = bot.get_chat_member(ACTIVITY_CHAT_ID, top_user_id).user
                    username = user_info.username or user_info.first_name
                    prize = random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

                    bot.send_animation(ACTIVITY_CHAT_ID, GIF_URL)
                    bot.send_message(ACTIVITY_CHAT_ID, f"🔥 Самый активный за 3 часа — @{username}!\n🎁 Приз: *{prize}*", parse_mode="Markdown")
                    bot.send_message(LOG_CHAT_ID, f"🏆 Активный участник:\n👤 @{username}\n🎁 Приз: *{prize}*", parse_mode="Markdown")

                    activity_counter.clear()

        time.sleep(60)


# ——— Запуск фонового потока
threading.Thread(target=check_and_award_top_user, daemon=True).start()

# ——— Запуск бота
bot.polling(none_stop=True)
