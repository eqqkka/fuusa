import telebot
from telebot import types
import random
from datetime import datetime, timedelta
import pytz
import threading
import time

TOKEN = '7507582678:AAFh76hUUGKWQr82fPcSnTzTAFZ-bIFwRKo'
bot = telebot.TeleBot(TOKEN)

PHOTO_REVIEW_GROUP_ID = -1002498200426  # замените на ID вашей группы с отзывами
ACTIVITY_GROUP_ID = -1002296054466
LOG_CHAT_ID = 7823280397

GIF_URL = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xoaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'

# Призы и шансы выпадения
prizes = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('70 звезд!', 5)
]

message_owners = {}         # msg_id -> user_id
claimed_messages = set()    # msg_id, на которые уже нажали
user_activity = {}          # user_id -> количество сообщений

kazakhstan_tz = pytz.timezone("Asia/Almaty")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id != PHOTO_REVIEW_GROUP_ID:
        return
    if message.caption:
        msg_id = message.message_id
        user_id = message.from_user.id

        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("\ud83c\udff1 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(
            message,
            "Спасибо за отзыв! Нажми кнопку, чтобы получить приз \ud83c\udff1",
            reply_markup=markup
        )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.chat.id == ACTIVITY_GROUP_ID:
        user_id = message.from_user.id
        user_activity[user_id] = user_activity.get(user_id, 0) + 1

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
    bot.send_message(call.message.chat.id, f"\ud83c\udf89 @{username}, твой приз: *{prize}*", parse_mode="Markdown")
    bot.send_message(LOG_CHAT_ID, f"\ud83c\udff1 Приз: *{prize}*\n\ud83d\udc64 Пользователь: @{username}", parse_mode="Markdown")

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.answer_callback_query(call.id)

# Функция для выдачи приза самому активному пользователю
def reward_top_user():
    while True:
        now = datetime.now(kazakhstan_tz)
        weekday = now.weekday()

        # Проверка, попадаем ли мы в нужный диапазон времени
        if (weekday < 5 and 8 <= now.hour < 20) or (weekday >= 5 and 11 <= now.hour < 20):
            if user_activity:
                top_user_id = max(user_activity, key=user_activity.get)
                chat_member = bot.get_chat_member(ACTIVITY_GROUP_ID, top_user_id)
                username = chat_member.user.username or chat_member.user.first_name

                prize = random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

                bot.send_animation(ACTIVITY_GROUP_ID, GIF_URL)
                bot.send_message(ACTIVITY_GROUP_ID, f"\ud83c\udf1f @{username}, ты самый активный участник! Твой приз: *{prize}*", parse_mode="Markdown")
                bot.send_message(LOG_CHAT_ID, f"\ud83c\udf1f Приз за активность: *{prize}*\n\ud83d\udc64 Пользователь: @{username}", parse_mode="Markdown")

            user_activity.clear()
        
        # Ждём 3 часа
        time.sleep(3 * 60 * 60)

# Запуск потока с автонаградой
threading.Thread(target=reward_top_user, daemon=True).start()

bot.polling(none_stop=True)
