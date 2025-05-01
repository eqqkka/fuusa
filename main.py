import telebot
from telebot import types
import random

TOKEN = '7507582678:AAEmU8r65GSXq3efU037r28VN4UQxvA2BhY'
bot = telebot.TeleBot(TOKEN)

LOG_CHAT_ID = 7823280397

# Призы и вероятности
prizes = [
    ('15 звезд', 40),
    ('20 звезд', 25),
    ('25 звезд', 20),
    ('30 звезд', 10),
    ('50 звезд!', 5)
]

GIF_URL = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xoaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'

# Хранилища
message_owners = {}         # message_id -> user_id
claimed_messages = set()    # message_id, по которым уже был выдан приз

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
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

    # Приз
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

    # Удаляем кнопку
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    bot.answer_callback_query(call.id)

bot.polling(none_stop=True)