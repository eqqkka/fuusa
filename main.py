import telebot
from telebot import types
import random
from datetime import datetime
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

# Конфигурация (ЗАМЕНИТЕ ЭТИ ЗНАЧЕНИЯ!)
TOKEN = "7507582678:AAEA3rC4g1PyjHpWFBCuhhD0qMenLt_1AuY"
PHOTO_REVIEW_GROUP_ID = -1002498200426    # ID группы для отзывов
ACTIVITY_GROUP_ID = -1002296054466        # ID группы активности
LOG_CHAT_ID = 7823280397                # Ваш ID для логов
GIF_URL = 'https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xhaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif'  # Ссылка на GIF
MAX_MESSAGES = 250                        # Макс сообщений для активности

# Инициализация бота
bot = telebot.TeleBot(TOKEN, parse_mode="MARKDOWN")

# Настройки призов
PRIZES = [
    ('10 звезд', 40),
    ('15 звезд', 25),
    ('25 звезд', 20),
    ('50 звезд', 10),
    ('70 звезд!', 5)
]

# Глобальные переменные
message_owners = {}
claimed_messages = set()
user_activity = {}
last_award_hour = None
kz_tz = pytz.timezone('Asia/Almaty')

def choose_random_prize():
    return random.choices(
        [p[0] for p in PRIZES], 
        weights=[p[1] for p in PRIZES]
    )[0]

@bot.message_handler(content_types=['photo'])
def handle_photo_review(message):
    try:
        chat_id = message.chat.id
        user = message.from_user
        logger.info(f"[handle_photo_review] Фото получено. chat_id={chat_id}, from_user={user}")
        bot.send_message(LOG_CHAT_ID, f"📷 Фото получено из чата `{chat_id}` от `{user.id if user else 'None'}`")

        if not user:
            logger.warning("Сообщение без from_user (возможно, анонимный админ)")
            return

        if chat_id != PHOTO_REVIEW_GROUP_ID:
            logger.info(f"Пропуск: чат {chat_id} не совпадает с PHOTO_REVIEW_GROUP_ID")
            return

        if not message.caption or len(message.caption.strip()) < 5:
            bot.reply_to(message, "❌ Добавьте описание к фото (минимум 5 символов)")
            return

        msg_id = message.message_id
        user_id = user.id
        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(message, "Спасибо за отзыв! Нажмите кнопку за призом 🎁", reply_markup=markup)

    except Exception as e:
        logger.error(f"[handle_photo_review] Ошибка: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Ошибка при обработке фото: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('spin:'))
def handle_spin(call):
    try:
        msg_id = int(call.data.split(':')[1])
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name

        if msg_id in claimed_messages:
            bot.answer_callback_query(call.id, "⚠️ Приз уже получен!")
            return

        if message_owners.get(msg_id) != user_id:
            bot.answer_callback_query(call.id, "❌ Только автор отзыва!", show_alert=True)
            return

        prize = choose_random_prize()
        claimed_messages.add(msg_id)

        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )

        bot.send_animation(call.message.chat.id, GIF_URL, disable_notification=True)
        bot.send_message(call.message.chat.id, f"🎉 @{username}, ваш приз: *{prize}*")
        bot.send_message(LOG_CHAT_ID, f"🎁 Приз: {prize}\n👤 @{username}")

    except Exception as e:
        logger.error(f"Ошибка callback: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка!", show_alert=True)

@bot.message_handler(content_types=['text'], chat_ids=[ACTIVITY_GROUP_ID])
def handle_activity(message):
    try:
        if not message.from_user.is_bot:
            user_id = message.from_user.id
            user_activity[user_id] = min(
                user_activity.get(user_id, 0) + 1,
                MAX_MESSAGES
            )
    except Exception as e:
        logger.error(f"Ошибка учета активности: {str(e)}")

def activity_award_loop():
    global last_award_hour
    allowed_hours = {11, 14, 17, 20}

    while True:
        try:
            now = datetime.now(kz_tz)
            current_hour = now.hour

            if now.minute % 5 == 0 and current_hour in allowed_hours:
                if current_hour != last_award_hour and user_activity:
                    top_user = max(user_activity.items(), key=lambda x: x[1])[0]
                    msg_count = user_activity[top_user]
                    
                    user_info = bot.get_chat_member(ACTIVITY_GROUP_ID, top_user).user
                    username = user_info.username or user_info.first_name
                    prize = choose_random_prize()

                    bot.send_animation(ACTIVITY_GROUP_ID, GIF_URL, disable_notification=True)
                    bot.send_message(
                        ACTIVITY_GROUP_ID,
                        f"🎊 @{username}, самый активный!\n💬 Сообщений: {msg_count}\n🎁 Приз: {prize}"
                    )
                    bot.send_message(LOG_CHAT_ID, f"🏆 Активный участник: @{username}\n💬 {msg_count} сообщений\n🎁 {prize}")
                    user_activity.clear()
                    last_award_hour = current_hour

            time.sleep(300)
        except Exception as e:
            logger.error(f"Ошибка цикла наград: {str(e)}")
            time.sleep(600)

def check_bot_permissions():
    try:
        chat_member = bot.get_chat_member(PHOTO_REVIEW_GROUP_ID, bot.get_me().id)
        if not chat_member.can_post_messages:
            raise PermissionError("Нет прав на отправку сообщений в группе отзывов")

        chat_member = bot.get_chat_member(ACTIVITY_GROUP_ID, bot.get_me().id)
        if not chat_member.can_send_messages:
            raise PermissionError("Нет прав на отправку сообщений в группе активности")

        logger.info("Проверка прав завершена успешно")
    except Exception as e:
        logger.critical(f"Ошибка прав доступа: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        logger.info("Запуск бота...")
        check_bot_permissions()
        bot.send_message(LOG_CHAT_ID, "🤖 Бот успешно запущен!")
        
        threading.Thread(target=activity_award_loop, daemon=True).start()
        bot.infinity_polling()
        
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")
        bot.send_message(LOG_CHAT_ID, f"🚨 Бот остановлен: {str(e)}")
