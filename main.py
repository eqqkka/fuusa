import telebot
from telebot import types
import random
import datetime
import threading
import time

TOKEN = '7507582678:AAFh76hUUGKWQr82fPcSnTzTAFZ-bIFwRKo'
GROUP_REVIEW_ID = -1002498200426  # ID первой группы (где фотоотзывы)
GROUP_ACTIVITY_ID = -1002296054466  # ID второй группы (где призы за актив)
LOG_CHAT_ID = 782328097  # ID лог-чата

bot = telebot.TeleBot(TOKEN)

prizes = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('75 звезд!', 5)
]

GIF_URL = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xoaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'

message_owners = {}         # message_id -> user_id
claimed_messages = set()    # обработанные сообщения с кнопкой
activity_counter = {}       # user_id -> count для второй группы

# 1. Обработка фото с подписью в первой группе
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id != GROUP_REVIEW_ID:
        return

    if message.caption:
        msg_id = message.message_id
        user_id = message.from_user.id

        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("\ud83c\udf81 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(
            message,
            "Спасибо за отзыв! Нажми кнопку, чтобы получить приз \ud83c\udf81",
            reply_markup=markup
        )

# 2. Нажатие на кнопку для получения приза
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
    bot.send_message(LOG_CHAT_ID, f"\ud83c\udf81 Приз: *{prize}*\n\ud83d\udc64 Пользователь: @{username}", parse_mode="Markdown")

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.answer_callback_query(call.id)

# 3. Учёт активности во второй группе
@bot.message_handler(func=lambda message: message.chat.id == GROUP_ACTIVITY_ID)
def track_activity(message):
    user_id = message.from_user.id
    activity_counter[user_id] = activity_counter.get(user_id, 0) + 1

# 4. Расписание выбора топ-активного участника

def is_time_to_check():
    now = datetime.datetime.now()
    weekday = now.weekday()  # 0-пн, 6-вс
    hour = now.hour
    if weekday < 5:
        return 8 <= hour < 20
    else:
        return 11 <= hour < 20

def pick_top_user():
    if not activity_counter:
        return

    top_user = max(activity_counter, key=activity_counter.get)
    prize = random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]
    user_mention = f'<a href="tg://user?id={top_user}">пользователь</a>'

    bot.send_animation(GROUP_ACTIVITY_ID, GIF_URL)
    bot.send_message(GROUP_ACTIVITY_ID, f"\ud83c\udf89 Поздравляем, {user_mention}! Ты был(а) самым активным за 3 часа и получаешь приз: *{prize}*", parse_mode="HTML")
    bot.send_message(LOG_CHAT_ID, f"\ud83c\udf81 Приз за активность: *{prize}*\n\ud83d\udc64 Пользователь: {top_user}", parse_mode="Markdown")

    activity_counter.clear()

# 5. Поток для автоматического выбора победителя

def activity_loop():
    while True:
        now = datetime.datetime.now()
        if is_time_to_check() and now.minute == 0:
            pick_top_user()
            time.sleep(3600 * 3)  # ждать 3 часа
        time.sleep(60)

threading.Thread(target=activity_loop, daemon=True).start()

# 6. Запуск бота
bot.polling(none_stop=True)
