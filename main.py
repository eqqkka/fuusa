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
TOKEN = "7507582678:AAGDTW1OFv5lQ2RFCm2fmwK2ftht_pUaSGk"
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

# Хранилища данных и блокировки
message_owners = {}
claimed_messages = set()
user_activity = {}
user_activity_lock = threading.Lock()
last_award_hour = None
kz_tz = pytz.timezone('Asia/Almaty')

def choose_random_prize():
    return random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

@bot.message_handler(content_types=['photo'])
def handle_photo_review(message):
    try:
        logger.info(f"Получено фото от {message.from_user.id} в чате {message.chat.id}")
        
        if message.chat.id != PHOTO_REVIEW_GROUP_ID:
            logger.warning(f"Сообщение не из целевой группы: {message.chat.id}")
            return

        if not message.caption or len(message.caption.strip()) < 5:
            bot.reply_to(message, "❌ Пожалуйста, добавьте текстовое описание к фото (минимум 5 символов).")
            logger.warning("Отзыв без описания отклонен")
            return

        msg_id = message.message_id
        user_id = message.from_user.id
        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(message, "Спасибо за отзыв! Нажми кнопку, чтобы получить приз 🎁", reply_markup=markup)
        logger.info(f"Добавлена кнопка для сообщения {msg_id}")

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Ошибка обработки фотоотзыва: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('spin:'))
def handle_spin(call):
    try:
        logger.info(f"Обработка callback: {call.data}")
        msg_id = int(call.data.split(':')[1])
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name

        if msg_id in claimed_messages:
            bot.answer_callback_query(call.id, "⚠️ Приз уже был получен за этот отзыв!")
            logger.warning(f"Повторный запрос приза для сообщения {msg_id}")
            return

        if message_owners.get(msg_id) != user_id:
            bot.answer_callback_query(call.id, "❌ Только автор отзыва может получить приз!", show_alert=True)
            logger.warning(f"Попытка чужого доступа к сообщению {msg_id}")
            return

        prize = choose_random_prize()
        claimed_messages.add(msg_id)

        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
        except Exception as e:
            logger.error(f"Ошибка при удалении кнопки: {str(e)}")

        bot.send_animation(call.message.chat.id, gif_url)
        bot.send_message(call.message.chat.id, f"🎉 @{username}, твой приз: *{prize}*")
        bot.send_message(LOG_CHAT_ID, f"🎁 Приз: *{prize}*\n👤 Пользователь: @{username}")
        logger.info(f"Выдан приз {prize} пользователю {user_id}")

        bot.answer_callback_query(call.id)

    except Exception as e:
        logger.error(f"Ошибка в callback: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка при обработке запроса!", show_alert=True)

@bot.message_handler(content_types=['text'], chat_id=ACTIVITY_GROUP_ID)
def handle_activity(message):
    try:
        if not message.from_user or message.from_user.is_bot:
            return
            
        user_id = message.from_user.id
        with user_activity_lock:
            user_activity[user_id] = user_activity.get(user_id, 0) + 1
        logger.debug(f"Активность +1 для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка учета активности: {str(e)}")

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

                        bot.send_animation(ACTIVITY_GROUP_ID, gif_url)
                        bot.send_message(
                            ACTIVITY_GROUP_ID,
                            f"🎊 @{username}, ты самый активный за последние 3 часа!\n"
                            f"💬 Сообщений: *{msg_count}*\n"
                            f"🎁 Приз: *{prize}*"
                        )
                        bot.send_message(
                            LOG_CHAT_ID,
                            f"🏆 Приз за активность: *{prize}*\n👤 @{username}\n💬 Сообщений: *{msg_count}*"
                        )

                        with user_activity_lock:
                            user_activity.clear()
                        last_award_hour = current_hour
                        logger.info(f"Выдан приз за активность {prize} пользователю {top_user}")

                    except Exception as e:
                        logger.error(f"Ошибка выдачи приза за активность: {str(e)}")
                        with user_activity_lock:
                            user_activity.clear()

                else:
                    logger.info("Нет активности для награждения")

            time.sleep(60)

        except Exception as e:
            logger.error(f"Критическая ошибка в цикле наград: {str(e)}")
            time.sleep(300)

thread = threading.Thread(target=activity_award_loop, daemon=True)
thread.start()

@bot.message_handler(commands=['status'])
def send_status(message):
    try:
        status_info = (
            f"🟢 Бот работает\n"
            f"📊 Статистика:\n"
            f"• Обработано отзывов: {len(message_owners)}\n"
            f"• Выдано призов: {len(claimed_messages)}\n"
            f"• Активных пользователей: {len(user_activity)}"
        )
        bot.reply_to(message, status_info)
    except Exception as e:
        logger.error(f"Ошибка команды status: {str(e)}")

if __name__ == '__main__':
    logger.info("Запуск бота...")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Бот упал с ошибкой: {str(e)}")
