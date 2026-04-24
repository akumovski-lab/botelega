from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import sqlite3

API_TOKEN = "8728680203:AAFeht0RUJV64UuwMzrGBo_rMT_sp01asx0"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect("orders.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    product TEXT,
    price REAL,
    count INTEGER,
    total REAL
)
""")
conn.commit()

# ===== ПАМЯТЬ =====
users = {}

# ===== КНОПКИ =====
kb_yes_no = ReplyKeyboardMarkup(resize_keyboard=True)
kb_yes_no.add(KeyboardButton("Да"), KeyboardButton("Нет"))

kb_cancel = ReplyKeyboardMarkup(resize_keyboard=True)
kb_cancel.add(KeyboardButton("Отмена"))

# ===== СТАРТ =====
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    users[message.from_user.id] = {
        'orders': [],
        'step': 'name'
    }

    await message.answer(
        "🛒 <b>СИСТЕМА УЧЁТА ЗАКАЗОВ</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📌 Введите название товара:",
        parse_mode="HTML",
        reply_markup=kb_cancel
    )

# ===== ОТМЕНА =====
@dp.message_handler(lambda message: message.text == "Отмена")
async def cancel(message: types.Message):
    users.pop(message.from_user.id, None)
    await message.answer("❌ Действие отменено. Нажмите /start")

# ===== ОСНОВНАЯ ЛОГИКА =====
@dp.message_handler()
async def process(message: types.Message):
    user = users.get(message.from_user.id)

    if not user:
        await message.answer("❗ Нажмите /start")
        return

    step = user['step']

    # ===== НАЗВАНИЕ =====
    if step == 'name':
        user['name'] = message.text
        user['step'] = 'price'

        await message.answer(
            f"📦 Товар: <b>{message.text}</b>\n\n💰 Введите цену:",
            parse_mode="HTML"
        )

    # ===== ЦЕНА =====
    elif step == 'price':
        try:
            user['price'] = float(message.text)
            user['step'] = 'count'

            await message.answer("🔢 Введите количество:")
        except:
            await message.answer("❌ Введите число!")

    # ===== КОЛИЧЕСТВО =====
    elif step == 'count':
        try:
            user['count'] = int(message.text)

            user['orders'].append({
                'name': user['name'],
                'price': user['price'],
                'count': user['count']
            })

            user['step'] = 'more'

            await message.answer(
                "✅ <b>Товар добавлен!</b>\n\n➕ Добавить ещё товар?",
                parse_mode="HTML",
                reply_markup=kb_yes_no
            )
        except:
            await message.answer("❌ Введите число!")

    # ===== ЕЩЁ? =====
    elif step == 'more':
        if message.text.lower() == "да":
            user['step'] = 'name'
            await message.answer("📌 Введите название товара:")
        elif message.text.lower() == "нет":
            user['step'] = 'discount'
            await message.answer(
                "🏷 Введите скидку (%):",
                reply_markup=types.ReplyKeyboardRemove()
            )

    # ===== СКИДКА + СОХРАНЕНИЕ =====
    elif step == 'discount':
        try:
            discount = float(message.text)
            total = 0

            text = "🧾 <b>ВАШ ЧЕК</b>\n"
            text += "━━━━━━━━━━━━━━━\n\n"

            for i, item in enumerate(user['orders'], start=1):
                s = item['price'] * item['count']
                total += s

                text += (
                    f"{i}. <b>{item['name']}</b>\n"
                    f"   {item['count']} × {item['price']} = <b>{s}</b>\n\n"
                )

            text += "━━━━━━━━━━━━━━━\n"
            text += f"💰 Сумма: {total}\n"

            if discount > 0:
                final = total * (1 - discount / 100)
                text += f"🏷 Скидка: {discount}%\n"
                text += f"💵 <b>К оплате: {round(final, 2)}</b>"
            else:
                final = total
                text += f"💵 <b>К оплате: {total}</b>"

            # ===== СОХРАНЕНИЕ В БД =====
            for item in user['orders']:
                cursor.execute(
                    "INSERT INTO orders (user_id, product, price, count, total) VALUES (?, ?, ?, ?, ?)",
                    (message.from_user.id, item['name'], item['price'], item['count'], item['price'] * item['count'])
                )

            conn.commit()

            await message.answer(text, parse_mode="HTML")

            user['step'] = 'done'

        except:
            await message.answer("❌ Введите число!")

# ===== ИСТОРИЯ =====
@dp.message_handler(commands=['history'])
async def history(message: types.Message):
    cursor.execute("SELECT product, count, total FROM orders WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchall()

    if not data:
        await message.answer("История пуста")
        return

    text = "📜 <b>История заказов:</b>\n\n"

    for row in data:
        text += f"{row[0]} — {row[1]} шт. = {row[2]} руб.\n"

    await message.answer(text, parse_mode="HTML")

# ===== ЗАПУСК =====
if __name__ == "__main__":
    executor.start_polling(dp)