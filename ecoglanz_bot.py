from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler
)
import json
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# СТАНИ
CITY, PLACE_TYPE, CLEAN_TYPE, ADDRESS, DATE, TIME, CONFIRM, NAME, PHONE = range(9)

ADMIN_ID = 929619425  # твій Telegram ID

# Google Sheets функція
def append_to_google_sheet(order):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("eco-glanz-bot-key.json", scope)
        client = gspread.authorize(creds)

        sheet = client.open("EcoGlanzOrders")
        city_sheet_name = order.get("city")

        try:
            worksheet = sheet.worksheet(city_sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=city_sheet_name, rows="100", cols="20")

        row = [
            order.get("user"),
            order.get("city"),
            order.get("clean_type"),
            order.get("place_type"),
            order.get("address"),
            f"{order.get('date')} {order.get('time')}",
            order.get("phone", ""),
            order.get("timestamp"),
            order.get("status", "Очікується")
        ]
        worksheet.append_row(row)
        print("✅ Записано у Google Таблицю")
    except Exception as e:
        print(f"❌ ПОМИЛКА при записі в таблицю: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Київ", "Одеса", "Львів"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Оберіть ваше місто:", reply_markup=markup)
    return CITY

async def select_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text
    keyboard = [["Квартира", "Будинок"], ["Офіс", "Інше"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Яке приміщення потрібно прибрати?", reply_markup=markup)
    return PLACE_TYPE

async def place_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["place_type"] = update.message.text
    keyboard = [["Стандарт", "Регулярне"], ["Генеральне", "Інше"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Який тип прибирання вас цікавить?", reply_markup=markup)
    return CLEAN_TYPE

async def clean_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["clean_type"] = update.message.text
    await update.message.reply_text("Вкажіть адресу (місто, вулиця, номер будинку/квартири):")
    return ADDRESS

async def address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text

    now = datetime.datetime.today()
    today_label = now.strftime('%A, %d.%m.%Y')
    weekdays_ua = {
        'Monday': 'Понеділок',
        'Tuesday': 'Вівторок',
        'Wednesday': 'Середа',
        'Thursday': 'Четвер',
        'Friday': 'Пʼятниця',
        'Saturday': 'Субота',
        'Sunday': 'Неділя'
    }
    for en, ua in weekdays_ua.items():
        today_label = today_label.replace(en, ua)

    await update.message.reply_text(
        f"📅 Сьогодні: {today_label}\nНа який день планується прибирання? (наприклад, понеділок або  25.05.2025)"
    )
    return DATE

async def date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text

    now = datetime.datetime.today()
    today_label = now.strftime('%A, %d.%m.%Y')
    weekdays_ua = {
        'Monday': 'Понеділок',
        'Tuesday': 'Вівторок',
        'Wednesday': 'Середа',
        'Thursday': 'Четвер',
        'Friday': 'Пʼятниця',
        'Saturday': 'Субота',
        'Sunday': 'Неділя'
    }
    for en, ua in weekdays_ua.items():
        today_label = today_label.replace(en, ua)
    await update.message.reply_text(f"📅 Сьогодні: {today_label}")
    await update.message.reply_text("О котрій годині вам зручно? (наприклад, 10:00)")
    return TIME

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text

    summary = (
        f"🧹 Тип прибирання: {context.user_data['clean_type']}\n"
        f"🏠 Приміщення: {context.user_data['place_type']}\n"
        f"📍 Адреса: {context.user_data['address']}\n"
        f"📆 Дата: {context.user_data['date']}\n"
        f"🕒 Час: {context.user_data['time']}\n"
        f"🌆 Місто: {context.user_data['city']}\n\n"
        f"❓ Замовлення вірно?"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Так, все вірно", callback_data="confirm")],
        [InlineKeyboardButton("✏️ Редагувати", callback_data="edit")]
    ])

    await update.message.reply_text(summary, reply_markup=keyboard)
    return CONFIRM

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "edit":
        await query.edit_message_text("Окей, давайте почнемо спочатку. Натисніть /start")
        return ConversationHandler.END

    await context.bot.send_message(chat_id=user.id, text="Як до вас звертатись?")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["client_name"] = update.message.text

    button = KeyboardButton("📞 Надіслати номер", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Тепер надішліть, будь ласка, свій номер телефону:",
        reply_markup=markup
    )
    return PHONE

async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    user = update.message.from_user

    context.user_data["phone"] = phone

    await update.message.reply_text(
        "✅ Дякуємо! Ваш номер збережено.",
        reply_markup=ReplyKeyboardMarkup([[" "]], resize_keyboard=True)
    )
    await update.message.reply_text("📞 Очікуйте, поки працівник з вами звʼяжеться!")

    order = {
        "user": context.user_data.get("client_name", user.username or user.first_name),
        "city": context.user_data["city"],
        "clean_type": context.user_data["clean_type"],
        "place_type": context.user_data["place_type"],
        "address": context.user_data["address"],
        "date": context.user_data["date"],
        "time": context.user_data["time"],
        "phone": phone,
        "timestamp": datetime.datetime.now().isoformat(),
        "status": "Очікується"
    }

    append_to_google_sheet(order)

    admin_text = (
        "📥 НОВА ЗАЯВКА\n\n"
        f"👤 Клієнт: {order['user']}\n"
        f"🌆 Місто: {order['city']}\n"
        f"🧹 Тип: {order['clean_type']}\n"
        f"🏠 Приміщення: {order['place_type']}\n"
        f"📍 Адреса: {order['address']}\n"
        f"📆 Дата: {order['date']}\n"
        f"🕒 Час: {order['time']}\n"
        f"📞 Телефон: {order['phone']}\n"
        f"📅 Заявка надійшла: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"📌 Статус: Очікується"
    )

    # Надсилання тільки працівникам з відповідного міста
    try:
        with open("cities.json", "r") as f:
            workers = json.load(f)
        city_workers = workers.get(order["city"], [])
        for worker_id in city_workers:
            await context.bot.send_message(chat_id=worker_id, text=admin_text)
    except Exception as e:
        print(f"❌ Не вдалося надіслати працівникам: {e}")

    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Заявку скасовано.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token("8054453181:AAGObFExKj0WRr8bGy9LV7h0kzPxvBAWawk").build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_city)],
            PLACE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, place_type)],
            CLEAN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, clean_type)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time)],
            CONFIRM: [CallbackQueryHandler(confirm_order)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT, save_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    print("🚀 EcoGlanz бот запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
