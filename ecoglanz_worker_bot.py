import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

import pkg_resources
print("📦 Встановлені пакети:", [p.project_name for p in pkg_resources.working_set])

ADMIN_ID = 929619425

# Завантаження списку працівників з файлу
with open("cities.json", "r") as f:
    WORKERS = json.load(f)

# Створюємо білий список усіх працівників (ID)
ALLOWED_WORKERS = []
for city, ids in WORKERS.items():
    ALLOWED_WORKERS.extend(ids)

# Підключення до Google Таблиці
def get_orders_for_city(city):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("eco-glanz-bot-key.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("EcoGlanzOrders").worksheet(city)
        records = sheet.get_all_records()
        return records
    except Exception as e:
        print("Помилка доступу до Google Таблиці:", e)
        return []

# Команда /start для працівників
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ALLOWED_WORKERS:
        await update.message.reply_text("⛔️ Доступ лише для працівників EcoGlanz!")
        return

    found = False
    for city, ids in WORKERS.items():
        if user_id in ids:
            context.user_data["city"] = city
            found = True
            break

    if not found:
        await update.message.reply_text("❌ У вас немає доступу до системи. Зверніться до адміністратора.")
        return

    await update.message.reply_text(
        f"✅ Вас розпізнано як працівника міста {context.user_data['city']}\n"
        "Надішліть команду /orders щоб переглянути доступні заявки."
    )

# Команда /orders — показ заявок для свого міста
async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ALLOWED_WORKERS:
        await update.message.reply_text("⛔️ Доступ лише для працівників EcoGlanz!")
        return

    city = context.user_data.get("city")
    if not city:
        await update.message.reply_text("⚠️ Спочатку надішліть /start для вибору міста.")
        return

    orders = get_orders_for_city(city)
    count = 0
    for i, order in enumerate(orders):
        if order.get("Статус") == "Очікується":
            count += 1
            text = (
                f"📍 Адреса: {order['Адреса']}\n"
                f"🧹 Тип: {order['Тип прибирання']}\n"
                f"📆 Дата: {order['Дата і час']}\n"
                f"📞 Телефон: {order['Телефон']}\n"
                f"📌 Статус: {order['Статус']}"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Прийняти", callback_data=f"take_{i}")]
            ])
            await update.message.reply_text(text, reply_markup=keyboard)

    if count == 0:
        await update.message.reply_text("😴 Немає доступних заявок у вашому місті.")

# Обробка натискання кнопки "Прийняти"
async def handle_take_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_WORKERS:
        await update.callback_query.answer("⛔️ Доступ лише для працівників!", show_alert=True)
        return

    query = update.callback_query
    await query.answer()

    city = context.user_data.get("city")
    user_name = update.effective_user.first_name
    order_index = int(query.data.split("_")[1])
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("eco-glanz-bot-key.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("EcoGlanzOrders").worksheet(city)
        cell = sheet.find("Очікується")
        row = cell.row
        sheet.update_cell(row, 8, "Виконується")
        sheet.update_cell(row, 1, f"Прийняв: {user_name}")
        await query.edit_message_text("✅ Ви прийняли замовлення! Статус оновлено.")
    except Exception as e:
        await query.edit_message_text("❌ Не вдалося оновити статус. Спробуйте пізніше.")
        print("Помилка оновлення таблиці:", e)

def main():
    # Можна брати токен з змінної середовища для безпеки:
    # TOKEN = os.getenv("WORKER_BOT_TOKEN")
    # app = ApplicationBuilder().token(TOKEN).build()
    app = ApplicationBuilder().token("7361780063:AAE0GhEFnIN3FMyaLaURtXSdCKmU6iAOTcY").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", list_orders))
    app.add_handler(CallbackQueryHandler(handle_take_order, pattern="^take_"))

    print("🚀 EcoGlanz Workers бот запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
