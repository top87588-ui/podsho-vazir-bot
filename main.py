import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Tokenni Render Environment Variables'dan olamiz
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

games = {}
ROLES = ["👑 Podsho", "🕵️ Vazir", "🪓 Jallod", "🥷 O'g'ri"]

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "<b>👑 Podsho-Vazir O'yiniga Xush Kelibsiz!</b>\n\n"
        "O'yinni guruhda o'ynashingiz mumkin.\n"
        "Guruhga botni qo'shing va <code>/newgame</code> buyrug'ini bering.",
        parse_mode="HTML"
    )

@dp.message(Command("newgame"))
async def cmd_newgame(message: types.Message):
    chat_id = message.chat.id
    games[chat_id] = {
        "players": {},
        "state": "JOINING",
        "vazir_id": None,
        "ogri_id": None
    }
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Qo'shilish", callback_data="join_game")],
        [InlineKeyboardButton(text="🚀 O'yinni Boshlash", callback_data="start_game")]
    ])
    await message.answer(
        "<b>🎲 Podsho-Vazir O'yini Boshlandi!</b>\n\n"
        "Ishtirokchilar 'Qo'shilish' tugmasini bosing (Kamida 4 kishi kerak).\n\n"
        "<b>Hozirgi ishtirokchilar:</b> 0 kishi",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "join_game")
async def process_join(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user
    
    if chat_id not in games or games[chat_id]["state"] != "JOINING":
        await callback.answer("Hozirda faol ro'yxatdan o'tish yo'q!", show_alert=True)
        return

    players = games[chat_id]["players"]
    if user.id in players:
        await callback.answer("Siz allaqachon qo'shilgansiz!", show_alert=True)
        return
    
    if len(players) >= 4:
        await callback.answer("O'yinchilar soni to'ldi (Max 4 kishi)!", show_alert=True)
        return

    players[user.id] = {"name": user.full_name, "role": None}
    await callback.answer("Siz o'yinga qo'shildingiz!")

    player_list = "\n".join([f"• {p['name']}" for p in players.values()])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Qo'shilish", callback_data="join_game")],
        [InlineKeyboardButton(text="🚀 O'yinni Boshlash", callback_data="start_game")]
    ])
    
    await callback.message.edit_text(
        f"<b>🎲 Podsho-Vazir O'yini Boshlandi!</b>\n\n"
        f"<b>Ishtirokchilar ({len(players)}/4):</b>\n{player_list}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "start_game")
async def process_start(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or len(game["players"]) < 4:
        await callback.answer("O'yinni boshlash uchun kamida 4 kishi kerak!", show_alert=True)
        return

    game["state"] = "PLAYING"
    player_ids = list(game["players"].keys())
    
    shuffled_roles = ROLES.copy()
    random.shuffle(shuffled_roles)

    podsho_name = ""
    vazir_name = ""

    for uid, role in zip(player_ids, shuffled_roles):
        game["players"][uid]["role"] = role
        if "Podsho" in role:
            podsho_name = game["players"][uid]["name"]
        elif "Vazir" in role:
            game["vazir_id"] = uid
            vazir_name = game["players"][uid]["name"]
        elif "O'g'ri" in role:
            game["ogri_id"] = uid

        try:
            await bot.send_message(uid, f"🤫 Sizning maxfiy rolingiz: <b>{role}</b>", parse_mode="HTML")
        except:
            pass

    suspect_buttons = []
    for uid, data in game["players"].items():
        if uid != game["vazir_id"]:
            suspect_buttons.append([
                InlineKeyboardButton(text=f"🥷 {data['name']}", callback_data=f"guess_{uid}")
            ])

    vazir_keyboard = InlineKeyboardMarkup(inline_keyboard=suspect_buttons)

    await callback.message.edit_text(
        f"👑 <b>PODSHO:</b> {podsho_name}\n"
        f"🕵️ <b>VAZIR:</b> {vazir_name}\n\n"
        f"📜 <i>Podsho amri: 'Vazirim, saroydan javohir yo'qoldi! O'g'rini top!'</i>\n\n"
        f"<b>Vazir @{vazir_name}, o'g'ri kimligini tanlang!</b>",
        reply_markup=vazir_keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("guess_"))
async def process_guess(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game["state"] != "PLAYING":
        return

    if callback.from_user.id != game["vazir_id"]:
        await callback.answer("Faqat Vazir o'g'rini tanlash huquqiga ega!", show_alert=True)
        return

    guessed_id = int(callback.data.split("_")[1])
    actual_ogri_id = game["ogri_id"]

    vazir_name = game["players"][game["vazir_id"]]["name"]
    guessed_name = game["players"][guessed_id]["name"]
    ogri_name = game["players"][actual_ogri_id]["name"]

    if guessed_id == actual_ogri_id:
        result_text = (
            f"🎯 <b>G'ALABA! VAZIR HAKAM!</b>\n\n"
            f"🕵️ Vazir {vazir_name} haqiqiy o'g'ri — <b>{ogri_name}</b>ni to'g'ri topdi!\n"
            f"🪓 Podsho Jallodga o'g'rini jazolashni buyurdi!"
        )
    else:
        result_text = (
            f"❌ <b>VAZIR ADASHDI!</b>\n\n"
            f"🕵️ Vazir {vazir_name} bekorga <b>{guessed_name}</b>ni aybladi.\n"
            f"🥷 Haqiqiy o'g'ri: <b>{ogri_name}</b> edi!\n"
            f"🪓 Jallod endi adashgan Vazirning o'zini jazolaydi!"
        )

    await callback.message.edit_text(result_text, parse_mode="HTML")
    del games[chat_id]

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
