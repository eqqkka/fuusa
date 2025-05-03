import telebot
from telebot import types
import random
import threading
import time
from datetime import datetime

TOKEN = '7507582678:AAFh76hUUGKWQr82fPcSnTzTAFZ-bIFwRKo'
LOG_CHAT_ID = 7823280397  # лог-чат (для пересылки выигрышей)
PHOTO_REVIEW_GROUP_ID = -1002498200426  # группа с фотоотзывами
ACTIVITY_GROUP_ID = -1002296054466     # группа с активностью

bot = telebot.TeleBot(TOKEN)

prizes = [
    ('15 звезд', 40),
    ('20 звезд', 25),
    ('25 звезд', 20),
    ('30 звезд', 10),
    ('50 звезд!', 5)
]

GIF_URL = 'https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExa2c2M2dva295MWM3M2JyOWJpemkzMTRqbWwwZmFoY2V3OWpldDd1eCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3oEjHVRs0V0af0zL32/giphy.gif'

message_owners = {}      # message_id -> user_id
claimed_messages = set() # message_id, по которым уже был выдан приз
user_activity = {}       # user_id -> count

# 1. Обработка фото с подписью
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id != PHOTO_REVIEW_GROUP_ID:
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

# 2. Кнопка для получения приза
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

# 3. Учёт сообщений в чате с активностью
@bot.message_handler(func=lambda message: message.chat.id == ACTIVITY_GROUP_ID)
def track_activity(message):
    user_id = message.from_user.id
    user_activity[user_id] = user_activity.get(user_id, 0) + 1

# 4. Автовыдача призов за активность каждые 3 часа

def schedule_worker():
    while True:
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour

        is_weekday = weekday < 5
        is_within_hours = (8 <= hour < 20) if is_weekday else (11 <= hour < 20)

        if is_within_hours:
            if user_activity:
                top_user = max(user_activity.items(), key=lambda x: x[1])[0]
                user_info = bot.get_chat_member(ACTIVITY_GROUP_ID, top_user).user
                username = user_info.username or user_info.first_name

                prize = random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

                bot.send_animation(ACTIVITY_GROUP_ID, GIF_URL)
                bot.send_message(ACTIVITY_GROUP_ID, f"🔥 @{username}, ты самый активный за 3 часа! Твой приз: *{prize}*", parse_mode="Markdown")
                bot.send_message(LOG_CHAT_ID, f"🔥 Самый активный: @{username}\n🎁 Приз: *{prize}*", parse_mode="Markdown")

            user_activity.clear()

        time.sleep(60 * 60 * 3)

threading.Thread(target=schedule_worker, daemon=True).start()
bot.polling(none_stop=True)
