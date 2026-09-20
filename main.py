import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# Ваш токен уже вставлено сюди
BOT_TOKEN = "8832222029:AAE7wZojF8uaN0rWB3iZSAUv1xplk9w8f-k"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db_questions = {}

class QuestionStates(StatesGroup):
    text = State()

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    args = message.text.split()
    
    if len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
        if target_id == message.from_user.id:
            await message.answer("❌ Ви не можете надсилати анонімні питання самому собі.")
            return
            
        await state.update_data(target_id=target_id)
        await state.set_state(QuestionStates.text)
        await message.answer("🤫 Напишіть ваше анонімне питання. Отримувач не дізнається, хто ви (поки не оплатить Stars).")
        return

    bot_info = await bot.get_me()
    share_link = f"https://t.me{bot_info.username}?start={message.from_user.id}"
    
    welcome_text = (
        "💬 **Питання — один із найкращих способів зрозуміти, що на думці у твоїх друзів.**\n\n"
        f"Ось твоє особисте посилання:\n🔗 `{share_link}`\n\n"
        "Розмісти його в шапці профілю Instagram, TikTok або в Telegram-каналі!"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(QuestionStates.text)
async def process_question(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("target_id")
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Дізнатися, хто це (50 ⭐️)", callback_data=f"ask_reveal_{message.message_id}")]
    ])
    
    try:
        sent_msg = await bot.send_message(
            chat_id=target_id,
            text=f"📩 **Вам надіслали нове анонімне питання!**\n\n«{message.text}»",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        db_questions[sent_msg.message_id] = message.from_user.id
        await message.answer("🚀 Ваше анонімне питання успішно надіслано!")
    except Exception:
        await message.answer("❌ Не вдалося надіслати питання. Можливо, користувач заблокував бота.")

@dp.callback_query(F.data.startswith("ask_reveal_"))
async def send_invoice_stars(callback_query):
    msg_id = int(callback_query.data.split("_")[2])
    
    if msg_id not in db_questions:
        await callback_query.answer("⚠️ Дані про це питання застаріли.", show_alert=True)
        return

    prices = [LabeledPrice(label="Розкрити автора", amount=50)]
    
    await bot.send_invoice(
        chat_id=callback_query.from_user.id,
        title="Дізнатися автора питання",
        description="Ви миттєво отримаєте ім'я та посилання на аккаунт відправника.",
        payload=f"payment_for_{msg_id}",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    await callback_query.answer()

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    msg_id = int(payload.split("_")[2])
    
    author_id = db_questions.get(msg_id)
    if author_id:
        try:
            user_info = await bot.get_chat(author_id)
            username = f"@{user_info.username}" if user_info.username else "Приховано (немає юзернейму)"
            
            response = (
                "🎉 **Особу розкрито!**\n\n"
                f"👤 **Ім'я:** {user_info.full_name}\n"
                f"🔗 **Посилання:** {username}\n"
                f"🆔 **ID:** `{author_id}`"
            )
            await message.answer(response, parse_mode="Markdown")
        except Exception:
            await message.answer(f"🎉 Оплачено! Але профіль захищено налаштуваннями приватності. ID автора: `{author_id}`")
    else:
        await message.answer("❌ Помилка: Автора не знайдено в базі даних.")

async def main():
    print("Бот анонимных вопросов запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
