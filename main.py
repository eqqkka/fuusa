import telebot
from telebot import types
import random
from datetime import datetime
import pytz
import threading
import time
import logging

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = '7507582678:AAEA3rC4g1PyjHpWFBCuhhD0qMenLt_1AuY'
PHOTO_REVIEW_GROUP_ID = -1002498200426   # Группа для фотоотзывов
ACTIVITY_GROUP_ID = -1002296054466      # Группа для отслеживания активности
LOG_CHAT_ID = 7823280397                  # Чат для логов
GIF_URL = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xhaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'
MAX_MESSAGES = 666                       # Лимит сообщений для одного пользователя

bot = telebot.TeleBot(TOKEN, parse_mode='MARKDOWN')

# Призы
PRIZES = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('70 звезд!', 5)
]

# Глобальные переменные
claimed_messages = set()
message_owners = {}
user_activity = {}
last_award_hour = None
kz_tz = pytz.timezone('Asia/Almaty')

# Получить случайный приз
def choose_random_prize():
    return random.choices(
        [p[0] for p in PRIZES],
        weights=[p[1] for p in PRIZES]
    )[0]

# Обработка фото с подписью
@bot.message_handler(content_types=['photo'])
def handle_photo_review(message):
    try:
        if message.chat.id != PHOTO_REVIEW_GROUP_ID:
            return

        if not message.caption or len(message.caption.strip()) < 5:
            bot.reply_to(message, "❌ Добавьте описание (минимум 5 символов)")
            return

        msg_id = message.message_id
        user_id = message.from_user.id
        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}"))

        bot.reply_to(message, "Спасибо за отзыв! Нажмите кнопку, чтобы получить приз 🎁", reply_markup=markup)

    except Exception as e:
        logger.error(f"[handle_photo_review] {e}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Ошибка при обработке фото: {e}")

# Обработка кнопки "Получить приз"
@bot.callback_query_handler(func=lambda call: call.data.startswith('spin:'))
def handle_spin(call):
    try:
        msg_id = int(call.data.split(':')[1])
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name

        if msg_id in claimed_messages:
            bot.answer_callback_query(call.id, "⚠️ Приз уже был получен.")
            return

        if message_owners.get(msg_id) != user_id:
            bot.answer_callback_query(call.id, "❌ Только автор отзыва может получить приз.", show_alert=True)
            return

        prize = choose_random_prize()
        claimed_messages.add(msg_id)

        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_animation(call.message.chat.id, GIF_URL, disable_notification=True)
        bot.send_message(call.message.chat.id, f"🎉 @{username}, ваш приз: *{prize}*")
        bot.send_message(LOG_CHAT_ID, f"🎁 Приз: {prize}\n👤 @{username}")

    except Exception as e:
        logger.error(f"[handle_spin] {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка при обработке кнопки", show_alert=True)

# Отслеживание активности в группе
@bot.message_handler(func=lambda msg: msg.chat.id == ACTIVITY_GROUP_ID and not msg.from_user.is_bot)
def handle_activity(message):
    try:
        user_id = message.from_user.id
        user_activity[user_id] = min(user_activity.get(user_id, 0) + 1, MAX_MESSAGES)
    except Exception as e:
        logger.error(f"[handle_activity] {e}")

# Цикл награждения активных участников
def activity_award_loop():
    global last_award_hour
    allowed_hours = {11, 14, 17, 20}  # Каждые 3 часа в разрешённое время

    while True:
        try:
            now = datetime.now(kz_tz)
            if now.hour in allowed_hours and now.hour != last_award_hour:
                if user_activity:
                    top_user_id, top_count = max(user_activity.items(), key=lambda x: x[1])
                    user = bot.get_chat_member(ACTIVITY_GROUP_ID, top_user_id).user
                    username = user.username or user.first_name
                    prize = choose_random_prize()

                    bot.send_animation(ACTIVITY_GROUP_ID, GIF_URL, disable_notification=True)
                    bot.send_message(
                        ACTIVITY_GROUP_ID,
                        f"🏆 @{username} — самый активный участник!\n💬 Сообщений: {top_count}\n🎁 Приз: *{prize}*"
                    )
                    bot.send_message(
                        LOG_CHAT_ID,
                        f"🏆 @{username} получил приз за активность\n💬 {top_count} сообщений\n🎁 {prize}"
                    )

                    user_activity.clear()
                    last_award_hour = now.hour

            time.sleep(60)

        except Exception as e:
            logger.error(f"[activity_award_loop] {e}")
            time.sleep(60)

# Проверка прав доступа бота в группах
def check_bot_permissions():
    try:
        bot.get_chat_member(PHOTO_REVIEW_GROUP_ID, bot.get_me().id)
        bot.get_chat_member(ACTIVITY_GROUP_ID, bot.get_me().id)
        logger.info("Права доступа проверены")
    except Exception as e:
        logger.critical(f"Проблема с правами доступа: {e}")
        raise

if __name__ == '__main__':
    try:
        logger.info("Бот запускается...")
        check_bot_permissions()
        bot.send_message(LOG_CHAT_ID, "✅ Бот успешно запущен.")

        threading.Thread(target=activity_award_loop, daemon=True).start()
        bot.infinity_polling()
    except Exception as e:
        logger.critical(f"Ошибка запуска: {e}")
        bot.send_message(LOG_CHAT_ID, f"❌ Бот остановился с ошибкой: {e}")
