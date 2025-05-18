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

# === КОНФИГУРАЦИЯ ===
TOKEN = "7507582678:AAEDbQCKUOSVVzg6MYhEv-KjUdax741eqn4"
PHOTO_REVIEW_GROUP_ID = -1002498200426  # Замените на ID вашей группы с фотоотзывами
ACTIVITY_GROUP_ID = -1002296054466      # Замените на ID группы активности
LOG_CHAT_ID = 7823280397                 # Замените на ID для логов
GIF_URL = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjhxb2xhaDNsbHN3Y2ZwNXNzbHB0dWVsMzVpZWR4OXV2d3VkdDdtdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WaExa2YxMRnyoLuITy/giphy.gif"
MAX_MESSAGES = 400

# Инициализация бота
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# Призы
PRIZES = [
    ('10 ⭐️', 40),
    ('15 ⭐️', 25),
    ('25 ⭐️', 20),
    ('50 ⭐️', 10),
    ('70 ⭐️!', 5)
]

# Хранилища
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
        if message.chat.id != PHOTO_REVIEW_GROUP_ID:
            return

        logger.info(f"Фотоотзыв от @{message.from_user.username} в группе")

        if not message.caption or len(message.caption.strip()) < 5:
            bot.reply_to(message, "❌ Пожалуйста, добавьте описание (минимум 5 символов)")
            return

        msg_id = message.message_id
        user_id = message.from_user.id

        if msg_id in claimed_messages:
            return

        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)

        bot.reply_to(message, "Спасибо за отзыв! Нажмите кнопку, чтобы получить приз 🎁", reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        bot.send_message(LOG_CHAT_ID, f"❌ Ошибка при обработке фото: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("spin:"))
def handle_spin(call):
    try:
        msg_id = int(call.data.split(":")[1])
        user_id = call.from_user.id

        if msg_id in claimed_messages:
            bot.answer_callback_query(call.id, "⚠️ Приз уже получен.")
            return

        if message_owners.get(msg_id) != user_id:
            bot.answer_callback_query(call.id, "❌ Только автор отзыва может получить приз!", show_alert=True)
            return

        claimed_messages.add(msg_id)
        prize = choose_random_prize()

        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_animation(call.message.chat.id, GIF_URL, disable_notification=True)

        username = call.from_user.username or call.from_user.first_name
        bot.send_message(call.message.chat.id, f"🎉 @{username}, ваш приз: *{prize}*")
        bot.send_message(LOG_CHAT_ID, f"🎁 Фотоотзыв: @{username} получил приз: {prize}")

    except Exception as e:
        logger.error(f"Ошибка при выдаче приза: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка.", show_alert=True)


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
        logger.error(f"Ошибка при учёте активности: {e}")


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
                        f"🏆 @{username}, самый активный!\n💬 Сообщений: {msg_count}\n🎁 Приз: {prize}"
                    )
                    bot.send_message(
                        LOG_CHAT_ID,
                        f"🎉 @{username} получил приз за активность: {prize} ({msg_count} сообщений)"
                    )
                    user_activity.clear()
                    last_award_hour = current_hour

            time.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка цикла наград: {e}")
            time.sleep(120)


def check_bot_permissions():
    try:
        bot_id = bot.get_me().id

        for chat_id in [PHOTO_REVIEW_GROUP_ID, ACTIVITY_GROUP_ID]:
            chat_member = bot.get_chat_member(chat_id, bot_id)
            if not chat_member.can_send_messages:
                raise PermissionError(f"Нет прав отправки сообщений в чате {chat_id}")

        logger.info("✅ Проверка прав — успешно")

    except Exception as e:
        logger.critical(f"❌ Ошибка прав: {e}")
        raise


if __name__ == '__main__':
    try:
        logger.info("🚀 Запуск бота...")
        check_bot_permissions()

        bot.send_message(LOG_CHAT_ID, "🤖 Бот запущен и готов к работе.")
        threading.Thread(target=activity_award_loop, daemon=True).start()
        bot.infinity_polling()

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}")
        bot.send_message(LOG_CHAT_ID, f"❌ Бот остановлен: {e}")
