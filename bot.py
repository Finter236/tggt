import os
import asyncio
import random
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
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
dp = Dispatcher()

selected_chats = set()  # Список чатов, где работает бот
bot_running = False  # Статус работы бота
user_data = {}  # Запоминаем информацию о пользователе (имя, интересы)

# 🔹 Главное меню
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("📋 Выбрать чаты"))
menu.add(KeyboardButton("▶ Старт"), KeyboardButton("⏹ Стоп"))
menu.add(KeyboardButton("ℹ Статус"))

# 🔹 Функция генерации ответа через ИИ
def get_ai_response(user_id, prompt):
    user_name = user_data.get(user_id, "ты")

    messages = [
        {"role": "system", "content": f"Ты девушка по имени Светлана, тебе 22 года. Ты дружелюбная, но не слишком фамильярная. Поддерживаешь диалог, шутки, эмоции, но не любишь звонки."},
        {"role": "user", "content": f"Привет, Светлана. Меня зовут {user_name}. Давай поговорим!"}
    ]
    
    messages.append({"role": "user", "content": prompt})

    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPINFRA_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "mistralai/Mistral-7B-Instruct-v0.1", "messages": messages, "max_tokens": 50}

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return random.choice([
            "Что-то у меня интернет лагает, попробуем позже? 🤔",
            "Ой, я сейчас немного занята, давай чуть позже поговорим!",
            "Какая-то ошибка, попробуй написать ещё раз 😊",
            "Может, обсудим это через пару минут? У меня тут небольшие дела."
        ])

# 🔹 Функция отказа от звонков
def check_call_block(message):
    bad_phrases = ["позвонить", "созвон", "звонок", "перезвон", "голосом"]
    if any(phrase in message.lower() for phrase in bad_phrases):
        return random.choice([
            "Мне удобнее общаться в чате, так я могу лучше формулировать мысли. 😊",
            "Не люблю созвоны, в чате удобнее, правда!",
            "Я не особо люблю говорить голосом, давай лучше тут!",
            "Голосом не могу, давай текстом?"
        ])
    return None

# 🔹 Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Я бот-автоответчик. Выбери, где мне работать:", reply_markup=menu)

# 🔹 Выбор чатов
@dp.message(lambda message: message.text == "📋 Выбрать чаты")
async def select_chats(message: types.Message):
    dialogs = await client.get_dialogs()
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for dialog in dialogs[:10]:  
        keyboard.add(KeyboardButton(f"{dialog.name} (ID: {dialog.id})"))
    
    keyboard.add(KeyboardButton("🔙 Назад"))
    await message.answer("Выбери чаты, в которых я должен работать:", reply_markup=keyboard)

# 🔹 Добавление чата в список
@dp.message(lambda message: "(ID:" in message.text)
async def add_chat(message: types.Message):
    chat_id = int(message.text.split("(ID:")[1].split(")")[0])
    selected_chats.add(chat_id)
    await message.answer(f"✅ Добавлен чат: {message.text}", reply_markup=menu)

# 🔹 Запуск бота
@dp.message(lambda message: message.text == "▶ Старт")
async def start_bot(message: types.Message):
    global bot_running
    if not selected_chats:
        await message.answer("❌ Сначала выберите чаты!")
        return
    bot_running = True
    await message.answer("✅ Бот запущен!", reply_markup=menu)

# 🔹 Остановка бота
@dp.message(lambda message: message.text == "⏹ Стоп")
async def stop_bot(message: types.Message):
    global bot_running
    bot_running = False
    await message.answer("⏹ Бот остановлен.", reply_markup=menu)

# 🔹 Проверка статуса
@dp.message(lambda message: message.text == "ℹ Статус")
async def check_status(message: types.Message):
    status = "🟢 Работает" if bot_running else "🔴 Остановлен"
    await message.answer(f"📌 Статус: {status}\n\n📋 Чаты: {len(selected_chats)}", reply_markup=menu)

# 🔹 Автоответчик
@client.on(events.NewMessage)
async def handle_message(event):
    global bot_running
    if not bot_running or event.chat_id not in selected_chats:
        return
    
    delay = random.randint(3, 7)
    await asyncio.sleep(delay)

    ai_reply = get_ai_response(event.sender_id, event.message.message)
    await event.respond(ai_reply)

# 🔹 Запуск
async def main():
    await client.start()
    dp.include_router(bot)
    print("✅ Бот запущен!")
    await dp.start_polling()

with client:
    client.loop.run_until_complete(main())
