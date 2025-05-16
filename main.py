import os
import telebot
from telebot import types
import random
from datetime import datetime, timedelta
import pytz
import threading
import time
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "7507582678:AAHYcKE0SoeWL_kR9oW5lMGh_PA8LDqlq28"
PHOTO_REVIEW_GROUP_ID = -1002498200426
ACTIVITY_GROUP_ID = -1002296054466
LOG_CHAT_ID = 7823280397

# Инициализация бота
bot = telebot.TeleBot(TOKEN, parse_mode="MARKDOWN")
gif_url = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xhaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'

prizes = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('70 звезд!', 5)
]

# Хранилища данных
message_owners = {}
claimed_messages = set()
user_activity = {}
user_activity_lock = threading.Lock()
last_award_hour = None
kz_tz = pytz.timezone('Asia/Almaty')

def choose_random_prize():
    return random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

# Обработчик фотоотзывов
@bot.message_handler(content_types=['photo'], chat_id=PHOTO_REVIEW_GROUP_ID)
def handle_photo_review(message):
    try:
        # Проверка наличия текста
        if not message.caption or not message.caption.strip():
            bot.reply_to(message, "❌ Отзыв должен содержать и фото, и текстовое описание!")
            logger.warning(f"Отклонен отзыв без текста от {message.from_user.id}")
            return

        msg_id = message.message_id
        user_id = message.from_user.id
        message_owners[msg_id] = user_id

        # Создание кнопки
        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        # Формирование ответа
        reply_text = f"{message.caption}\n\nСпасибо за отзыв! Нажми кнопку, чтобы получить приз 🎁"
        bot.reply_to(message, reply_text, reply_markup=markup)
        logger.info(f"Принят отзыв от {user_id}")

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Ошибка обработки отзыва: {str(e)}")

# Обработчик кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith('spin:'))
def handle_spin(call):
    try:
        msg_id = int(call.data.split(':')[1])
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name

        # Проверки
        if msg_id in claimed_messages:
            bot.answer_callback_query(call.id, "⚠️ Приз уже был получен за этот отзыв!")
            return

        if message_owners.get(msg_id) != user_id:
            bot.answer_callback_query(call.id, "❌ Только автор отзыва может получить приз!", show_alert=True)
            return

        # Выдача приза
        prize = choose_random_prize()
        claimed_messages.add(msg_id)

        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
        except Exception as e:
            logger.error(f"Ошибка удаления кнопки: {str(e)}")

        # Отправка уведомлений
        bot.send_animation(call.message.chat.id, gif_url)
        bot.send_message(call.message.chat.id, f"🎉 @{username}, твой приз: *{prize}*")
        bot.send_message(LOG_CHAT_ID, f"🎁 Выдан приз: {prize}\n👤 Пользователь: @{username}")

        bot.answer_callback_query(call.id)

    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка при обработке запроса!", show_alert=True)

# Система учета активности
@bot.message_handler(content_types=['text'], chat_id=ACTIVITY_GROUP_ID)
def handle_activity(message):
    try:
        if message.from_user.is_bot:
            return

        user_id = message.from_user.id
        with user_activity_lock:
            user_activity[user_id] = user_activity.get(user_id, 0) + 1
        logger.debug(f"Активность +1 для {user_id}")

    except Exception as e:
        logger.error(f"Ошибка учета активности: {str(e)}")

# Система наград за активность
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
                
                if top_user:
                    try:
                        user = bot.get_chat_member(ACTIVITY_GROUP_ID, top_user).user
                        username = user.username or user.first_name
                        prize = choose_random_prize()

                        # Отправка награды
                        bot.send_animation(ACTIVITY_GROUP_ID, gif_url)
                        bot.send_message(
                            ACTIVITY_GROUP_ID,
                            f"🏆 Победитель активности!\n"
                            f"👤 @{username}\n"
                            f"💬 Сообщений: {msg_count}\n"
                            f"🎁 Приз: {prize}"
                        )
                        bot.send_message(
                            LOG_CHAT_ID,
                            f"🏅 Награда за активность:\n"
                            f"• Пользователь: @{username}\n"
                            f"• Сообщений: {msg_count}\n"
                            f"• Приз: {prize}"
                        )

                        with user_activity_lock:
                            user_activity.clear()
                        last_award_hour = current_hour

                    except Exception as e:
                        logger.error(f"Ошибка выдачи награды: {str(e)}")

            time.sleep(60)

        except Exception as e:
            logger.error(f"Критическая ошибка: {str(e)}")
            time.sleep(300)

# Запуск фонового процесса
thread = threading.Thread(target=activity_award_loop, daemon=True)
thread.start()

if __name__ == '__main__':
    logger.info("🟢 Запуск бота...")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.critical(f"🔴 Критическая ошибка: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Бот остановлен: {str(e)}")
