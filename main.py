import telebot
from telebot import types
import random
from datetime import datetime, timedelta
import pytz
import threading
import time

TOKEN = '7507582678:AAFh76hUUGKWQr82fPcSnTzTAFZ-bIFwRKo'
bot = telebot.TeleBot(TOKEN)

GROUP_ID_PHOTO = -1002498200426  # Первая группа (фотоотзывы)
GROUP_ID_ACTIVE = -1002296054466  # Вторая группа (активность)
LOG_CHAT_ID = 782328-397

GIF_URL = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xoaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'

# Призы и вероятности
prizes = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('75 звезд!', 4)
    ('100 звезд!!', 1)
]

# Хранилища
message_owners = {}  # message_id -> user_id
claimed_messages = set()  # message_id, по которым уже был выдан приз
user_activity = {}  # user_id -> кол-во сообщений

# Обработка фотоотзывов
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id != GROUP_ID_PHOTO:
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
    bot.send_message(
        call.message.chat.id,
        f"🎉 @{username}, твой приз: *{prize}*",
        parse_mode="Markdown"
    )

    bot.send_message(
        LOG_CHAT_ID,
        f"🎁 Приз: *{prize}*\n👤 Пользователь: @{username}",
        parse_mode="Markdown"
    )

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.answer_callback_query(call.id)

# Подсчёт активности в группе
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID_ACTIVE and m.text)
def track_activity(message):
    user_id = message.from_user.id
    user_activity[user_id] = user_activity.get(user_id, 0) + 1

# Выдача приза самому активному пользователю
def award_top_user():
    while True:
        tz = pytz.timezone("Asia/Almaty")
        now = datetime.now(tz)
        weekday = now.weekday()
        hour = now.hour

        # Условия: будни 08–20, выходные 11–20
        if (weekday < 5 and 8 <= hour < 21) or (weekday >= 5 and 11 <= hour < 21):
            if user_activity:
                top_user_id = max(user_activity, key=user_activity.get)
                top_user_mention = f"[{top_user_id}](tg://user?id={top_user_id})"
                prize = random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

                bot.send_animation(GROUP_ID_ACTIVE, GIF_URL)
                bot.send_message(
                    GROUP_ID_ACTIVE,
                    f"🏆 Самый активный участник последних часов — {top_user_mention}!\n🎁 Приз: *{prize}*",
                    parse_mode="Markdown"
                )

                bot.send_message(
                    LOG_CHAT_ID,
                    f"🎁 Приз за активность: *{prize}*\n👤 Пользователь: {top_user_mention}",
                    parse_mode="Markdown"
                )

                user_activity.clear()
        time.sleep(60 * 60 * 3)  # каждые 3 часа

# Запускаем поток отслеживания активности
threading.Thread(target=award_top_user, daemon=True).start()

bot.polling(none_stop=True)
