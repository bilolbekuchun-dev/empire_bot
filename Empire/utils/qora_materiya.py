import random
from aiogram.types import CallbackQuery
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.game_data import Game, GamePlayer, GamePhase
from utils.role_names import RoleNames

QM_VS_SELECT = "qm_vs_sel"
QM_VS_PICK = "qm_vs_pick"
QM_PORTLAT = "qm_portlat"
QM_TIR_SELECT = "qm_tir_sel"
QM_TIR_PICK = "qm_tir_pick"
QM_XAZINA_NUM = "qm_xaz_num"
QM_XAZINA = "qm_xaz"

async def qm_voidswap_select(call: CallbackQuery, bot: Bot):
    """Void Swap: Rollarni almashtirish uchun o'yinchi tanlash"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="qm_noop")
    await call.message.edit_text(
        "🔮 <b>Qora Materiya: Void Swap</b>\n\n"
        "Qaysi o'yinchi bilan rolingizni almashtirmoqchisiz?",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await call.answer()

async def qm_voidswap_pick(call: CallbackQuery, bot: Bot):
    await call.answer("🔮 Rolingiz muvaffaqiyatli almashtirildi!", show_alert=True)

async def qm_portlatish(call: CallbackQuery, bot: Bot):
    """Portlatish: Barcha himoyalarni o'chirish"""
    await call.answer("💥 Qora Materiya: Barcha himoyalar portlatildi va zararsizlantirildi!", show_alert=True)

async def qm_tiriltir_select(call: CallbackQuery, bot: Bot):
    """Tiriltirish: O'lgan o'yinchini qayta o'yinga qaytarish"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="qm_noop")
    await call.message.edit_text(
        "✨ <b>Qora Materiya: Tiriltirish</b>\n\n"
        "O'yinga qaytarmoqchi bo'lgan marhum o'yinchini tanlang:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await call.answer()

async def qm_tiriltir_pick(call: CallbackQuery, bot: Bot):
    await call.answer("✨ O'yinchi hayotga qaytarildi va o'yinga qo'shildi!", show_alert=True)

async def qm_xazina_start(call: CallbackQuery, bot: Bot):
    """Xazina sandig'i"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 4):
        builder.button(text=f"📦 Sandiq #{i}", callback_data=f"{QM_XAZINA_NUM}_{i}")
    builder.adjust(3)
    await call.message.edit_text(
        "🧰 <b>Qora Materiya: Xazina Sandig'i</b>\n\n"
        "Omadingizni sinab ko'rish uchun sandiqlardan birini tanlang:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await call.answer()

async def qm_xazina_pick(call: CallbackQuery, bot: Bot):
    rewards = ["1000 $ dollar", "50 💎 olmos", "🔪 Qotildan himoya", "🔰 Geroy himoya"]
    won = random.choice(rewards)
    await call.answer(f"🎉 Tabriklaymiz! Sandiqdan chiqdi: {won}", show_alert=True)
