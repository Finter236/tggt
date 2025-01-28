import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from telethon import TelegramClient, events
from dotenv import load_dotenv

# 🔹 Загружаем переменные из .env
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")

# 🔹 Настройки
client = TelegramClient("bot_session", API_ID, API_HASH)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

selected_chats = set()  # Список чатов, где работает бот
bot_running = False  # Статус работы бота

# 🔹 Главное меню
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("📋 Выбрать чаты"))
menu.add(KeyboardButton("▶ Старт"), KeyboardButton("⏹ Стоп"))
menu.add(KeyboardButton("ℹ Статус"))

# 🔹 Функция генерации ответа
def get_ai_response(prompt):
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPINFRA_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "mistralai/Mistral-7B-Instruct-v0.1", "messages": [{"role": "user", "content": prompt}], "max_tokens": 50}

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "Ой, что-то пошло не так. Давай попробуем позже!"

# 🔹 Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Я бот-автоответчик. Выбери, где мне работать:", reply_markup=menu)

# 🔹 Выбор чатов
@dp.message_handler(lambda message: message.text == "📋 Выбрать чаты")
async def select_chats(message: types.Message):
    dialogs = await client.get_dialogs()
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for dialog in dialogs[:10]:  # Ограничим до 10 чатов для удобства
        keyboard.add(KeyboardButton(f"{dialog.name} (ID: {dialog.id})"))
    
    keyboard.add(KeyboardButton("🔙 Назад"))
    await message.answer("Выбери чаты, в которых я должен работать:", reply_markup=keyboard)

# 🔹 Добавление чата в список
@dp.message_handler(lambda message: "(ID:" in message.text)
async def add_chat(message: types.Message):
    chat_id = int(message.text.split("(ID:")[1].split(")")[0])
    selected_chats.add(chat_id)
    await message.answer(f"✅ Добавлен чат: {message.text}", reply_markup=menu)

# 🔹 Запуск бота
@dp.message_handler(lambda message: message.text == "▶ Старт")
async def start_bot(message: types.Message):
    global bot_running
    if not selected_chats:
        await message.answer("❌ Сначала выберите чаты!")
        return
    bot_running = True
    await message.answer("✅ Бот запущен!", reply_markup=menu)

# 🔹 Остановка бота
@dp.message_handler(lambda message: message.text == "⏹ Стоп")
async def stop_bot(message: types.Message):
    global bot_running
    bot_running = False
    await message.answer("⏹ Бот остановлен.", reply_markup=menu)

# 🔹 Проверка статуса
@dp.message_handler(lambda message: message.text == "ℹ Статус")
async def check_status(message: types.Message):
    status = "🟢 Работает" if bot_running else "🔴 Остановлен"
    await message.answer(f"📌 Статус: {status}\n\n📋 Чаты: {len(selected_chats)}", reply_markup=menu)

# 🔹 Автоответчик (если бот включён)
@client.on(events.NewMessage)
async def handle_message(event):
    global bot_running
    if not bot_running or event.chat_id not in selected_chats:
        return
    
    ai_reply = get_ai_response(event.message.message)
    await event.respond(ai_reply)

# 🔹 Запуск
async def main():
    await client.start()
    print("✅ Бот запущен!")
    await dp.start_polling()

with client:
    client.loop.run_until_complete(main())
