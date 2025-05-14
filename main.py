import os
import telebot
from telebot import types
import random
from datetime import datetime, timedelta
import pytz
import threading
import time
import logging
from collections import deque

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "7507582678:AAFRmqHBR4rOICgDlnKQyPnQbBb5n7AkJpw"
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
status_cooldown = deque(maxlen=3)
last_award_hour = None
kz_tz = pytz.timezone('Asia/Almaty')

def choose_random_prize():
    return random.choices([p[0] for p in prizes], weights=[p[1] for p in prizes])[0]

# Обработчики сообщений
@bot.message_handler(content_types=['photo'], chat_id=PHOTO_REVIEW_GROUP_ID)
def handle_photo_review(message):
    try:
        logger.info(f"Получено фото от {message.from_user.id}")
        
        if not message.caption or len(message.caption.strip()) < 5:
            bot.reply_to(message, "❌ Пожалуйста, добавьте текстовое описание к фото (минимум 5 символов).")
            return

        msg_id = message.message_id
        user_id = message.from_user.id
        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(message, "Спасибо за отзыв! Нажми кнопку, чтобы получить приз 🎁", reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Ошибка обработки фотоотзыва: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('spin:'))
def handle_spin(call):
    try:
        msg_id = int(call.data.split(':')[1])
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name

        if msg_id in claimed_messages:
            bot.answer_callback_query(call.id, "⚠️ Приз уже был получен за этот отзыв!")
            return

        if message_owners.get(msg_id) != user_id:
            bot.answer_callback_query(call.id, "❌ Только автор отзыва может получить приз!", show_alert=True)
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

        bot.answer_callback_query(call.id)

    except Exception as e:
        logger.error(f"Ошибка в callback: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка при обработке запроса!", show_alert=True)

@bot.message_handler(content_types=['text'], chat_id=ACTIVITY_GROUP_ID)
def handle_activity(message):
    try:
        if message.from_user.is_bot:
            return
            
        user_id = message.from_user.id
        with user_activity_lock:
            user_activity[user_id] = user_activity.get(user_id, 0) + 1
    except Exception as e:
        logger.error(f"Ошибка учета активности: {str(e)}")

# Система статусов активности
@bot.message_handler(commands=['status'], chat_types=['supergroup', 'group'], chat_id=ACTIVITY_GROUP_ID)
def send_activity_status(message):
    try:
        logger.info(f"Запрос статуса в чате {message.chat.id}")
        
        # Проверка что запрос в нужном чате
        if message.chat.id != ACTIVITY_GROUP_ID:
            logger.warning(f"Попытка запроса статуса в чужом чате: {message.chat.id}")
            return

        # Проверка прав администратора
        try:
            member = bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.status not in ['administrator', 'creator']:
                bot.reply_to(message, "❌ Команда доступна только администраторам!")
                return
        except Exception as e:
            logger.error(f"Ошибка проверки прав: {str(e)}")
            return

        # Формирование и отправка статуса
        status_info = (
            "📊 *Статус активности* 📊\n\n"
            f"🏆 Текущий лидер: {get_top_user()}\n"
            f"💬 Сообщений за период: {get_total_messages()}\n"
            f"🎁 Выдано призов сегодня: {len(claimed_messages)}\n"
            f"⏳ Следующее награждение: {next_award_time()}"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh_status"))
        
        bot.send_message(
            chat_id=ACTIVITY_GROUP_ID,
            text=status_info,
            parse_mode="Markdown",
            reply_markup=markup
        )
        logger.info(f"Статус успешно отправлен в чат {ACTIVITY_GROUP_ID}")

    except Exception as e:
        logger.error(f"Критическая ошибка в статусе: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Ошибка отправки статуса: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "refresh_status")
def refresh_status(call):
    try:
        if call.from_user.id in status_cooldown:
            bot.answer_callback_query(call.id, "⏳ Подождите 3 минуты перед обновлением!")
            return
            
        status_cooldown.append(call.from_user.id)
        send_activity_status()
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Ошибка обновления статуса: {str(e)}")

# Вспомогательные функции
def get_top_user():
    with user_activity_lock:
        if not user_activity:
            return "пока нет данных"
        top_user_id = max(user_activity, key=user_activity.get)
        
    try:
        user = bot.get_chat_member(ACTIVITY_GROUP_ID, top_user_id).user
        return f"@{user.username}" if user.username else user.first_name
    except:
        return "неизвестный пользователь"

def get_total_messages():
    with user_activity_lock:
        return sum(user_activity.values()) if user_activity else 0

def next_award_time():
    now = datetime.now(kz_tz)
    allowed_hours = [11, 14, 17, 20]
    
    for hour in allowed_hours:
        if now.hour < hour:
            next_time = now.replace(hour=hour, minute=0, second=0)
            return next_time.strftime("%H:%M")
    return "завтра в 11:00"

# Система наград за активность
def activity_award_loop():
    global last_award_hour
    allowed_hours = [11, 14, 17, 20]

    while True:
        try:
            now = datetime.now(kz_tz)
            current_hour = now.hour

            if current_hour in allowed_hours and current_hour != last_award_hour:
                send_activity_status()
                
                with user_activity_lock:
                    if user_activity:
                        top_user = max(user_activity.items(), key=lambda x: x[1])[0]
                        msg_count = user_activity[top_user]
                    else:
                        top_user = None

                if top_user:
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

                    except Exception as e:
                        logger.error(f"Ошибка выдачи приза за активность: {str(e)}")

            time.sleep(60)

        except Exception as e:
            logger.error(f"Критическая ошибка в цикле наград: {str(e)}")
            time.sleep(300)

# Запуск фонового потока
thread = threading.Thread(target=activity_award_loop, daemon=True)
thread.start()

if __name__ == '__main__':
    logger.info("Запуск бота...")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Бот упал с ошибкой: {str(e)}")
