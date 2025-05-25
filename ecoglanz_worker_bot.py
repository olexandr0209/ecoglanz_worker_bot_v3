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

    await update.message.reply_text(
        f"✅ Вас розпізнано як працівника!\n"
        "Надішліть команду /orders щоб переглянути доступні заявки."
    )

async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ALLOWED_WORKERS:
        await update.message.reply_text("⛔️ Доступ лише для працівників EcoGlanz!")
        return

    # --- Підключення до Google Sheets ---
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("eco-glanz-bot-key.json", scope)
        client = gspread.authorize(creds)
        # !!! ПРАЦЮЄМО ЛИШЕ З ОДНИМ АРКУШЕМ "Замовлення" у новій таблиці !!!
        sheet = client.open("EcoGlanzOrders2024").worksheet("Замовлення")
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
            await update.message.reply_text("😴 Немає доступних заявок.")
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

    order_index = int(query.data.split("_")[1])
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("eco-glanz-bot-key.json", scope)
        client = gspread.authorize(creds)
        # !!! Лише аркуш "Замовлення" у новій таблиці !!!
        sheet = client.open("EcoGlanzOrders2024").worksheet("Замовлення")
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
