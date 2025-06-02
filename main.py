import schedule
import time
import telebot
from telebot import types
import pytz
from datetime import datetime, timedelta
import random
import html
import threading

TOKEN = '8082470933:AAHE1S7pkiSl3Q1JLBf8RcAARMfH-OFUQwU'
if not TOKEN:
    raise Exception("TOKEN not provided")

bot = telebot.TeleBot(TOKEN)

PHOTO_REVIEW_GROUP_ID = -1002498200426
ACTIVITY_GROUP_ID = -1002296054466
LOG_GROUP_ID = -1002300029531
TARGET_GROUP_ID = ACTIVITY_GROUP_ID

kz_tz = pytz.timezone('Asia/Almaty')

# Призы для фотоотзывов
photo_prizes = [
    ("Спасибо за отзыв! вот твои 10⭐", 40),
    ("Отличный отзыв! Забирай 15⭐", 25),
    ("Ты молодец! 25⭐ за фотоотзыв", 15),
    ("Половина джекпота за отзыв — 50⭐", 10),
    ("Круто! 75⭐ за отзыв", 6),
    ("ДЖЕКПОТ за отзыв!!! 100⭐", 4)
]

photo_prize_gifs = {
    "Спасибо за отзыв! вот твои 10⭐": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExbHJjd2o3MGd3NzN0dWhyb3k0ZHJtdDh3dW5hZzFkZWxjOTQ1b21yNiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/fYPTGG53rmDYqdWEh2/giphy.gif",
    "Отличный отзыв! Забирай 15⭐": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdDJ5c2NzY2lrOGY0dmZidGx0dmswdWF4Mjk2anBnNGFlZGhkeW0zNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/01V1ds7VIW4elT7z8e/giphy.gif",
    "Ты молодец! 25⭐ за фотоотзыв": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZm5tM3NyOTFzMmliZzcycWhlcTR1eW5iNm4xeHFuZW5zNHJnZGwzNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/oSuwWNBrcTuMEuI2JT/giphy.gif",
    "Половина джекпота за отзыв — 50⭐": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExZnI0c2dkY2o2ODZxdTd2bjA2cDZydjN6emt1Zmg0eWg1ZmZ1ZDc5ZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qaj5tYeKZngAZfUz8D/giphy.gif",
    "Круто! 75⭐ за отзыв": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExcThsMnY3YTY2MTV2bzFsamxoMHgxM2NwbmppZXIwZXR5dnE5NXRyeiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/marFRLUicCgCy5TRsD/giphy.gif",
    "ДЖЕКПОТ за отзыв!!! 100⭐": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExYmNuazl1MGF3bXptMG16ZDlkZWp1MXpmM28zMTN2MXZ0aXhhNm4zZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/OCmfov2P22iFdGsxeY/giphy.gif"
}

# Призы для активности
activity_prizes = [
    ("Заглядывай сюда почаще, и будет больше, а пока — 10⭐!", 40),
    ("Активный участник! 15⭐", 25),
    ("Твой приз — 25⭐", 15),
    ("Половина джекпота за активность — 50⭐", 10),
    ("Чутьчуть до джекпота не хватило — 75⭐", 6),
    ("ДЖЕКПОТ за активность!!! 100⭐", 4)
]

activity_prize_gifs = {
    "Заглядывай сюда почаще, и будет больше, а пока — 10⭐!": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExbHJjd2o3MGd3NzN0dWhyb3k0ZHJtdDh3dW5hZzFkZWxjOTQ1b21yNiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/fYPTGG53rmDYqdWEh2/giphy.gif",
    "Активный участник! 15⭐": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdDJ5c2NzY2lrOGY0dmZidGx0dmswdWF4Mjk2anBnNGFlZGhkeW0zNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/01V1ds7VIW4elT7z8e/giphy.gif",
    "Твой приз — 25⭐": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZm5tM3NyOTFzMmliZzcycWhlcTR1eW5iNm4xeHFuZW5zNHJnZGwzNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/oSuwWNBrcTuMEuI2JT/giphy.gif",
    "Половина джекпота за активность — 50⭐": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExZnI0c2dkY2o2ODZxdTd2bjA2cDZydjN6emt1Zmg0eWg1ZmZ1ZDc5ZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qaj5tYeKZngAZfUz8D/giphy.gif",
    "Чутьчуть до джекпота не хватило — 75⭐": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExcThsMnY3YTY2MTV2bzFsamxoMHgxM2NwbmppZXIwZXR5dnE5NXRyeiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/marFRLUicCgCy5TRsD/giphy.gif",
    "ДЖЕКПОТ за активность!!! 100⭐": "https://media.giphy.com/media/activity-gif6.gif"
}

message_owners = {}
claimed_messages = set()
user_activity = {}
AWARD_INTERVAL_SECONDS = 3 * 60 * 60

def choose_random_prize(prize_list):
    return random.choices(
        [prize[0] for prize in prize_list],
        weights=[prize[1] for prize in prize_list]
    )[0]

def get_user_mention(user):
    if user.username:
        return f"@{user.username}"
    else:
        name = html.escape(user.first_name or "друг")
        return f"<a href='tg://user?id={user.id}'>{name}</a>"

def get_mention_by_id(user_id):
    try:
        user = bot.get_chat_member(ACTIVITY_GROUP_ID, user_id).user
        return get_user_mention(user)
    except Exception:
        return f"<a href='tg://user?id={user_id}'>победитель</a>"

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_chat_members(message):
    if message.chat.id != TARGET_GROUP_ID:
        return
    for new_user in message.new_chat_members:
        mention = get_user_mention(new_user)
        bot.send_message(message.chat.id, f"Добро пожаловать, {mention}! У нас самые активные получают призы каждые 3 часа 🎁", parse_mode='HTML')

@bot.message_handler(commands=['getchatid'])
def get_chat_id(message):
    bot.send_message(message.chat.id, f"Chat ID: {message.chat.id}")

@bot.message_handler(content_types=['photo'])
def handle_photo_review(message):
    if message.chat.id == PHOTO_REVIEW_GROUP_ID and message.caption:
        msg_id = message.message_id
        user_id = message.from_user.id
        message_owners[msg_id] = user_id

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🎁 Получить приз", callback_data=f"spin:{msg_id}")
        markup.add(button)
        bot.reply_to(message, "Спасибо за отзыв! Нажми кнопку, чтобы получить приз 🎁", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("spin:"))
def handle_spin_button(call):
    try:
        msg_id = int(call.data.split(":")[1])
        user_id = message_owners.get(msg_id)

        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "Эта кнопка не для тебя!", show_alert=True)
            return

        if msg_id in claimed_messages:
            bot.answer_callback_query(call.id, "Приз уже получен.")
            return

        claimed_messages.add(msg_id)
        bot.answer_callback_query(call.id, "Поздравляем! 🎉")

        prize_text = choose_random_prize(photo_prizes)
        gif_url = photo_prize_gifs.get(prize_text)
        username_mention = get_user_mention(call.from_user)

        if gif_url:
            bot.send_animation(call.message.chat.id, gif_url)

        bot.send_message(
            call.message.chat.id,
            f"🎁 {username_mention}, {prize_text}",
            parse_mode='HTML'
        )

        bot.send_message(
            LOG_GROUP_ID,
            f"🎁 Приз за отзыв\nПользователь: {username_mention} (ID: {call.from_user.id})\nПриз: {prize_text}",
            parse_mode='HTML'
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Будем ждать вас еще!"
        )

    except Exception as e:
        print(f"Ошибка обработки кнопки: {e}")

# Часовой пояс Алматы
ALMATY_TZ = pytz.timezone("Asia/Almaty")
AWARD_HOURS = [10, 13, 16, 19, 22]  # Время по Алмате

@bot.message_handler(func=lambda message: message.chat.id == ACTIVITY_GROUP_ID and not message.from_user.is_bot)
def track_user_activity(message):
    user_id = message.from_user.id
    user_activity[user_id] = user_activity.get(user_id, 0) + 1

def award_most_active_user():
    global user_activity
    try:
        if not user_activity:
            print("[INFO] Нет активности для награждения.")
        else:
            top_user_id = max(user_activity, key=user_activity.get)
            prize_text = choose_random_prize(activity_prizes)
            gif_url = activity_prize_gifs.get(prize_text)
            mention = get_mention_by_id(top_user_id)

            if gif_url:
                bot.send_animation(ACTIVITY_GROUP_ID, gif_url)

            bot.send_message(
                ACTIVITY_GROUP_ID,
                f"🎉 Поздравляем {mention}!\n🎁 Твой приз за активность: {prize_text}",
                parse_mode='HTML'
            )

            bot.send_message(
                LOG_GROUP_ID,
                f"🎁 Приз за активность\nПользователь ID: {top_user_id}\nПриз: {prize_text}"
            )

            print(f"[INFO] Награждён пользователь {top_user_id} призом: {prize_text}")

        user_activity = {}
    except Exception as e:
        print(f"[ERROR] Ошибка при награждении активного пользователя: {e}")

# Проверка времени каждые 30 секунд
def schedule_thread():
    while True:
        now = datetime.now(ALMATY_TZ)
        if now.minute == 0 and now.second < 30 and now.hour in AWARD_HOURS:
            award_most_active_user()
            time.sleep(60)  # Ждём минуту, чтобы не выполнить награждение повторно
        time.sleep(30)

threading.Thread(target=schedule_thread, daemon=True).start()

print("[INFO] Бот запущен.")
bot.infinity_polling()
