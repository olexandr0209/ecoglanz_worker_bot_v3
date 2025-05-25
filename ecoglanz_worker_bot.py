import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Завантаження працівників з файлу
with open("cities.json", "r") as f:
    WORKERS = json.load(f)

ALLOWED_WORKERS = []
for city, ids in WORKERS.items():
    ALLOWED_WORKERS.extend(ids)

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

async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ALLOWED_WORKERS:
        await update.message.reply_text("⛔️ Доступ лише для працівників EcoGlanz!")
        return

    city = context.user_data.get("city")
    if not city:
        await update.message.reply_text("⚠️ Спочатку надішліть /start для вибору міста.")
        return

    # --- Підключення до Google Sheets ---
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("eco-glanz-bot-key.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("EcoGlanzOrders").worksheet(city)
        records = sheet.get_all_records()

        found = 0
        for i, order in enumerate(records, start=2):  # 1-й рядок — заголовки
            if str(order.get("Статус", "")).strip() == "Очікується":
                found += 1
                text = (
                    f"📍 Адреса: {order.get('Адреса')}\n"
                    f"🧹 Тип: {order.get('Тип прибирання')}\n"
                    f"🏠 Приміщення: {order.get('Приміщення')}\n"
                    f"📆 Дата і час: {order.get('Час заявки')}\n"
                    f"📞 Телефон: {order.get('Телефон')}\n"
                    f"📌 Статус: {order.get('Статус')}"
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Прийняти", callback_data=f"take_{i}")]
                ])
                await update.message.reply_text(text, reply_markup=keyboard)

        if found == 0:
            await update.message.reply_text("😴 Немає доступних заявок у вашому місті.")
    except Exception as e:
        await update.message.reply_text("⚠️ Помилка доступу до Google Таблиці.")
        print("Помилка:", e)

async def handle_take_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_WORKERS:
        await update.callback_query.answer("⛔️ Доступ лише для працівників!", show_alert=True)
        return

    query = update.callback_query
    await query.answer()

    city = context.user_data.get("city")
    order_index = int(query.data.split("_")[1])
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("eco-glanz-bot-key.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("EcoGlanzOrders").worksheet(city)
        # Змінити статус заявки на "Виконується"
        sheet.update_cell(order_index, 8, "Виконується")
        await query.edit_message_text("✅ Ви прийняли замовлення! Статус оновлено.")
    except Exception as e:
        await query.edit_message_text("❌ Не вдалося оновити статус. Спробуйте пізніше.")
        print("Помилка оновлення таблиці:", e)

def main():
    app = ApplicationBuilder().token("7361780063:AAE0GhEFnIN3FMyaLaURtXSdCKmU6iAOTcY").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", list_orders))
    app.add_handler(CallbackQueryHandler(handle_take_order, pattern="^take_"))

    print("🚀 EcoGlanz Workers бот запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
