import os
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)

# --- СТАНИ для ConversationHandler ---
CITY, CLEAN_TYPE, PLACE_TYPE, ADDRESS, DATE, TIME, PHONE, CONFIRM = range(8)

# --- Підключення до Google Sheets ---
def append_to_google_sheet(order):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("eco-glanz-bot-key.json", scope)
        client = gspread.authorize(creds)
        worksheet = client.open("EcoGlanzOrders2024").worksheet("Замовлення")
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

# --- Логіка Telegram-бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Вітаємо в EcoGlanz!\n"
        "Давайте оформимо заявку на прибирання. Спочатку виберіть місто:",
        reply_markup=ReplyKeyboardMarkup([["Київ", "Львів", "Одеса"]], one_time_keyboard=True, resize_keyboard=True)
    )
    context.user_data.clear()
    return CITY

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text
    await update.message.reply_text(
        "Оберіть тип прибирання:",
        reply_markup=ReplyKeyboardMarkup([["Генеральне", "Підтримуюче", "Після ремонту"]], one_time_keyboard=True, resize_keyboard=True)
    )
    return CLEAN_TYPE

async def clean_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["clean_type"] = update.message.text
    await update.message.reply_text(
        "Оберіть тип приміщення:",
        reply_markup=ReplyKeyboardMarkup([["Квартира", "Будинок", "Офіс"]], one_time_keyboard=True, resize_keyboard=True)
    )
    return PLACE_TYPE

async def place_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["place_type"] = update.message.text
    await update.message.reply_text("Введіть адресу прибирання:", reply_markup=ReplyKeyboardRemove())
    return ADDRESS

async def address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text
    await update.message.reply_text("На яку дату запланувати прибирання? (формат: 2024-05-27)")
    return DATE

async def date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text
    await update.message.reply_text("О котрій годині? (наприклад, 10:00)")
    return TIME

async def time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text
    await update.message.reply_text("Залиште номер телефону для звʼязку:")
    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    summary = (
        f"Перевірте дані заявки:\n"
        f"Місто: {context.user_data['city']}\n"
        f"Тип прибирання: {context.user_data['clean_type']}\n"
        f"Приміщення: {context.user_data['place_type']}\n"
        f"Адреса: {context.user_data['address']}\n"
        f"Дата: {context.user_data['date']} {context.user_data['time']}\n"
        f"Телефон: {context.user_data['phone']}\n"
        "Якщо все вірно, натисніть 'Підтвердити', або /cancel для скасування."
    )
    await update.message.reply_text(summary, reply_markup=ReplyKeyboardMarkup([["Підтвердити"]], one_time_keyboard=True, resize_keyboard=True))
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "Підтвердити":
        await update.message.reply_text("Оформлення скасовано.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    order = context.user_data.copy()
    order["user"] = update.effective_user.full_name
    order["timestamp"] = int(time.time())
    order["status"] = "Очікується"

    append_to_google_sheet(order)

    await update.message.reply_text("✅ Заявку прийнято! Наш менеджер звʼяжеться з вами найближчим часом.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Оформлення скасовано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    # Можеш використати змінну середовища або підставити токен прямо тут
    TOKEN = os.getenv("CLIENT_BOT_TOKEN")
    # або замість цього: TOKEN = "ТВОЙ_КЛИЕНТСКИЙ_БОТ_ТОКЕН"

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
            CLEAN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, clean_type)],
            PLACE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, place_type)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_input)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))

    print("🚀 EcoGlanz Client Bot запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
