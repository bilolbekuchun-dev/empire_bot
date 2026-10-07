import os
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from utils import admins, statistika
from utils.premium_emojis import (
    ALL_ACTIVE_ROLES, WEAPON_NAMES, CURRENCY_NAMES,
    get_custom_emoji, set_custom_emoji, reset_all_custom_emojis,
    parse_emoji_from_message, role_display, get_item_display,
    get_diamond_display, get_dollar_display
)
from states.admin_states import AdminEmojiStates, AdminSubStates, AdminBroadcastStates
from models.user import RequiredChannel
from utils.admin_panel import execute_broadcast_task
from keyboards.admin_keyboard import (
    admin_emoji_main_menu, admin_emoji_roles_categories_menu,
    admin_emoji_roles_list_menu, admin_emoji_weapons_list_menu,
    admin_emoji_item_actions_menu, admin_back_btn,
    admin_sub_menu_kb, admin_sub_detail_kb, admin_broadcast_menu_kb
)
from config import ADMINS, PRIMARY_ADMIN_ID, PRIMARY_ADMIN_IDS



router = Router()

HARDCODED_ADMINS = set()

async def is_primary_admin(user_id: int) -> bool:
    """Bosh adminlar, ADMINS hamda bazada shakllangan (BotAdmin) barcha adminlar admin paneldan foydalana oladi"""
    if not user_id:
        return False
    if user_id in HARDCODED_ADMINS or user_id in PRIMARY_ADMIN_IDS or user_id == PRIMARY_ADMIN_ID or user_id in ADMINS:
        return True
    from models.user import BotAdmin
    return await BotAdmin.filter(user_id=user_id).exists()

# ==========================================
# 👑 ASOSIY PREMIUM EMOJI ADMIN PANEL
# ==========================================

def get_main_panel_text() -> str:
    d_display = get_diamond_display()
    m_display = get_dollar_display()
    text = (
        "👑 <b>ADMINISTRATOR BOSHQARUV PANELI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Bu yerdan o'yin rollari, qurol-aslahalar, Premium Emojilar, "
        "<b>Majburiy obuna</b> hamda <b>Xabar tarqatish (Broadcast)</b>ni boshqarishingiz mumkin.\n\n"
        f"• 💎 <b>Olmos:</b> {d_display}\n"
        f"• 💵 <b>Dollar:</b> {m_display}\n\n"
        "<i>Kerakli bo'limni tanlang:</i>"
    )
    return text

@router.message(Command("admin", "panel", "admin_panel", "adm"))
@router.message(F.text.in_(["🎛 Admin panel", "Admin panel", "/admin", "/panel"]))
async def admin_panel_cmd(message: Message, state: FSMContext):
    if not await is_primary_admin(message.from_user.id):
        await message.answer("Ushbu buyruq mavjud emas")
        return
    await state.clear()
    text = get_main_panel_text()
    await message.answer(text, parse_mode="HTML", reply_markup=admin_emoji_main_menu())

@router.message(Command("broadcast", "send_all", "rassilka"))
async def broadcast_cmd(message: Message, state: FSMContext):
    if not await is_primary_admin(message.from_user.id):
        return
    await state.clear()
    text = (
        "📢 <b>XABAR TARQATISH (BROADCAST)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Kimlarga xabar tarqatmoqchisiz?\n"
        "<i>Kerakli bo'limni tanlang:</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=admin_broadcast_menu_kb())


@router.callback_query(F.data == "adm_emj_main")
async def adm_emj_main_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.clear()
    text = get_main_panel_text()
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_main_menu())
    await call.answer()

# ==========================================
# 🎭 ROLLAR BO'LIMI
# ==========================================

@router.callback_query(F.data == "adm_emj_roles_menu")
async def adm_emj_roles_menu_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    await state.clear()
    text = (
        "🎭 <b>Rollar Emojilari</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Qaysi toifadagi rollarni sozlamoqchisiz?"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_roles_categories_menu())
    await call.answer()

@router.callback_query(F.data == "adm_emj_cat_tinch")
async def adm_emj_cat_tinch_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    text = "🏛 <b>Tinch aholi rollari (13 ta):</b>\n\nEmoji o'rnatmoqchi bo'lgan rolni tanlang:"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_roles_list_menu("tinch"))
    await call.answer()

@router.callback_query(F.data == "adm_emj_cat_mafia")
async def adm_emj_cat_mafia_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    text = "🤵 <b>Mafia rollari (6 ta):</b>\n\nEmoji o'rnatmoqchi bo'lgan rolni tanlang:"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_roles_list_menu("mafia"))
    await call.answer()

@router.callback_query(F.data == "adm_emj_cat_yakka")
async def adm_emj_cat_yakka_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    text = "⚔️ <b>Yakka va Neytral rollar (10 ta):</b>\n\nEmoji o'rnatmoqchi bo'lgan rolni tanlang:"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_roles_list_menu("yakka"))
    await call.answer()

@router.callback_query(F.data.startswith("adm_emj_role_"))
async def adm_emj_role_view_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    idx = int(call.data.replace("adm_emj_role_", ""))
    if idx >= len(ALL_ACTIVE_ROLES):
        return
    role_name = ALL_ACTIVE_ROLES[idx]
    custom = get_custom_emoji("roles", role_name)
    current_display = role_display(role_name)

    status_text = "✅ O'rnatilgan" if custom else "▫️ O'rnatilmagan (Standart)"
    text = (
        f"🎭 <b>Rol:</b> {role_name}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Hozirgi ko'rinishi:</b> {current_display}\n"
        f"• <b>Premium emoji holati:</b> {status_text}\n"
        f"• <b>Saqlangan teg:</b> <code>{custom if custom else 'yoq'}</code>\n\n"
        "<i>Premium emoji o'rnatish uchun quyidagi tugmani bosing:</i>"
    )
    kb = admin_emoji_item_actions_menu("roles", str(idx), "adm_emj_roles_menu")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

# ==========================================
# ⚔️ QUROL-ASLAHALAR BO'LIMI
# ==========================================

@router.callback_query(F.data == "adm_emj_weapons_menu")
async def adm_emj_weapons_menu_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    await state.clear()
    text = "⚔️ <b>Qurol-aslahalar va Inventar:</b>\n\nEmoji o'rnatmoqchi bo'lgan elementni tanlang:"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_weapons_list_menu())
    await call.answer()

@router.callback_query(F.data.startswith("adm_emj_wpn_"))
async def adm_emj_wpn_view_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    key = call.data.replace("adm_emj_wpn_", "")
    info = WEAPON_NAMES.get(key)
    if not info:
        return
    icon, name = info
    custom = get_custom_emoji("weapons", key)
    current_display = get_item_display(key)

    status_text = "✅ O'rnatilgan" if custom else f"▫️ O'rnatilmagan (Standart {icon})"
    text = (
        f"⚔️ <b>Buyum:</b> {name}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Hozirgi ko'rinishi:</b> {current_display} {name}\n"
        f"• <b>Premium emoji:</b> {status_text}\n"
        f"• <b>Saqlangan teg:</b> <code>{custom if custom else 'yoq'}</code>\n\n"
        "<i>Premium emoji o'rnatish uchun quyidagi tugmani bosing:</i>"
    )
    kb = admin_emoji_item_actions_menu("weapons", key, "adm_emj_weapons_menu")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

# ==========================================
# 💎 VA 💵 VALYUTALAR
# ==========================================

@router.callback_query(F.data == "adm_emj_currency_diamond")
async def adm_emj_currency_diamond_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    custom = get_custom_emoji("currency", "diamond")
    cur = get_diamond_display()
    status_text = "✅ O'rnatilgan" if custom else "▫️ O'rnatilmagan (Standart 💎)"
    text = (
        "💎 <b>Olmos Emojisi</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Hozirgi ko'rinishi:</b> {cur}\n"
        f"• <b>Premium emoji:</b> {status_text}\n"
        f"• <b>Saqlangan teg:</b> <code>{custom if custom else 'yoq'}</code>\n\n"
        "<i>Premium emoji o'rnatish uchun quyidagi tugmani bosing:</i>"
    )
    kb = admin_emoji_item_actions_menu("currency", "diamond", "adm_emj_main")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "adm_emj_currency_dollar")
async def adm_emj_currency_dollar_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    custom = get_custom_emoji("currency", "dollar")
    cur = get_dollar_display()
    status_text = "✅ O'rnatilgan" if custom else "▫️ O'rnatilmagan (Standart 💵)"
    text = (
        "💵 <b>Dollar / Pul Emojisi</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Hozirgi ko'rinishi:</b> {cur}\n"
        f"• <b>Premium emoji:</b> {status_text}\n"
        f"• <b>Saqlangan teg:</b> <code>{custom if custom else 'yoq'}</code>\n\n"
        "<i>Premium emoji o'rnatish uchun quyidagi tugmani bosing:</i>"
    )
    kb = admin_emoji_item_actions_menu("currency", "dollar", "adm_emj_main")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


# ==========================================
# ✏️ EMOJI O'RNATISH VA O'CHIRISH JARAYONI
# ==========================================

@router.callback_query(F.data.startswith("adm_emj_del_"))
async def adm_emj_del_item_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    parts = call.data.replace("adm_emj_del_", "").split("_", 1)
    category = parts[0]
    raw_key = parts[1]

    if category == "roles":
        idx = int(raw_key)
        key = ALL_ACTIVE_ROLES[idx]
        set_custom_emoji("roles", key, None)
        await call.answer("✅ Rol emojisi standart holatga qaytarildi!", show_alert=True)
        # Qayta ko'rsatish
        call.data = f"adm_emj_role_{idx}"
        await adm_emj_role_view_cb(call, None)
    elif category == "weapons":
        set_custom_emoji("weapons", raw_key, None)
        await call.answer("✅ Qurol emojisi standart holatga qaytarildi!", show_alert=True)
        call.data = f"adm_emj_wpn_{raw_key}"
        await adm_emj_wpn_view_cb(call)
    elif category == "currency":
        set_custom_emoji("currency", raw_key, None)
        await call.answer("✅ Valyuta emojisi standart holatga qaytarildi!", show_alert=True)
        if raw_key == "diamond":
            await adm_emj_currency_diamond_cb(call)
        else:
            await adm_emj_currency_dollar_cb(call)

@router.callback_query(F.data.startswith("adm_emj_set_"))
async def adm_emj_set_item_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    parts = call.data.replace("adm_emj_set_", "").split("_", 1)
    category = parts[0]
    raw_key = parts[1]

    target_name = ""
    if category == "roles":
        idx = int(raw_key)
        target_name = ALL_ACTIVE_ROLES[idx]
    elif category == "weapons":
        target_name = WEAPON_NAMES.get(raw_key, ("", raw_key))[1]
    elif category == "currency":
        target_name = CURRENCY_NAMES.get(raw_key, ("", raw_key))[1]

    await state.set_state(AdminEmojiStates.waiting_for_emoji)
    await state.update_data(category=category, raw_key=raw_key, target_name=target_name)

    text = (
        f"✏️ <b>{target_name}</b> uchun premium emojini yuboring:\n\n"
        "📌 <i>Siz emojini to'g'ridan-to'g'ri Telegram Premium stikeri/emojisi sifatida yuborishingiz, "
        "yoki <code>&lt;tg-emoji emoji-id='...'&gt;...&lt;/tg-emoji&gt;</code> HTML kodini, "
        "yoki shunchaki <b>emoji_id</b> raqamini yuborishingiz mumkin.</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_btn("adm_emj_main"))
    await call.answer()

@router.message(AdminEmojiStates.waiting_for_emoji, F.chat.type == "private")
async def process_emoji_input_msg(message: Message, state: FSMContext):
    if not await is_primary_admin(message.from_user.id):
        return
    emoji_html = parse_emoji_from_message(message)
    if not emoji_html:
        await message.answer("❌ Emojini aniqlab bo'lmadi. Iltimos, qayta yuboring:")
        return

    data = await state.get_data()
    category = data.get("category")
    raw_key = data.get("raw_key")
    target_name = data.get("target_name")
    await state.clear()

    if category == "roles":
        idx = int(raw_key)
        real_key = ALL_ACTIVE_ROLES[idx]
        set_custom_emoji("roles", real_key, emoji_html)
    elif category == "weapons":
        set_custom_emoji("weapons", raw_key, emoji_html)
    elif category == "currency":
        set_custom_emoji("currency", raw_key, emoji_html)

    await message.answer(
        f"✅ <b>{target_name}</b> uchun premium emoji muvaffaqiyatli saqlandi!\n\n"
        f"• Ko'rinishi: {emoji_html}\n"
        f"• Saqlangan teg: <code>{emoji_html}</code>",
        parse_mode="HTML",
        reply_markup=admin_back_btn("adm_emj_main")
    )

# ==========================================
# 🗑 BARCHA EMOJILARNI TOZALASH
# ==========================================

@router.callback_query(F.data == "adm_emj_reset_confirm")
async def adm_emj_reset_confirm_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    reset_all_custom_emojis()
    await call.answer("🗑 Barcha maxsus premium emojilar tozalandi va standart holatga qaytarildi!", show_alert=True)
    text = get_main_panel_text()
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_main_menu())

# ==========================================
# ⚡️ STANDART BUYRUQLAR (PRESERVED)
# ==========================================

@router.message(F.text.startswith("/gblock"))
async def f_gblock(message: Message, bot: Bot):
    await admins.block_this_group(message=message, bot=bot)

@router.message(Command("eboylar"))
async def global_excel_handler(message: Message, bot: Bot):
    await statistika.export_global_richest_to_excel(message, bot)

@router.message(F.text.startswith("/vip "))
@router.channel_post(F.text.startswith("/vip "))
async def f_vip(message: Message, bot: Bot):
    await admins.distribute_vip_handler(message=message, bot=bot)

@router.callback_query(F.data.startswith("claim_vip_"))
async def f_claim_vip(call: CallbackQuery, bot: Bot):
    await admins.claim_vip_callback(call=call, bot=bot)

@router.message(Command("pchange"))
async def f_pchange(message: Message):
    await admins.change_profile_answer(message=message)

@router.message(Command("rgm"))
async def f_rgm(message: Message, bot: Bot):
    await admins.remove_geroy_market_item(message)

@router.message(F.text.startswith("/ungblock"))
async def f_ungblock(message: Message, bot: Bot):
    await admins.unblock_this_group(message=message, bot=bot)

@router.message(F.text.startswith("/gsearch"))
async def f_gsearch(message: Message, bot: Bot):
    await admins.find_group_by_name(message=message)

@router.message(Command("takevip"))
@router.message(F.text.startswith("/takevip"))
async def f_takevip(message: Message, bot: Bot):
    await admins.take_vip_handler(message=message, bot=bot)

@router.message(Command("givevip"))
@router.message(F.text.startswith("/givevip"))
async def f_givevip(message: Message, bot: Bot):
    await admins.give_vip_handler(message=message, bot=bot)

@router.message(Command("addadmin"))
@router.message(F.text.startswith("/addadmin"))
async def f_addadmin(message: Message):
    if not await is_primary_admin(message.from_user.id):
        return
    await admins.add_bot_admin_handler(message=message)

@router.message(Command("deladmin"))
@router.message(F.text.startswith("/deladmin"))
async def f_deladmin(message: Message):
    if not await is_primary_admin(message.from_user.id):
        return
    await admins.del_bot_admin_handler(message=message)

@router.message(Command("admins"))
@router.message(Command("adminlist"))
@router.message(F.text.startswith("/admins"))
async def f_admins_list(message: Message):
    if not await is_primary_admin(message.from_user.id):
        return
    await admins.list_bot_admins_handler(message=message)

@router.message(Command("setvip"))
@router.message(Command("addvip"))
@router.message(F.text.startswith("/setvip"))
async def f_setvip(message: Message, bot: Bot):
    if not await is_primary_admin(message.from_user.id):
        return
    await admins.give_vip_handler(message=message, bot=bot)

@router.message(Command("delvip"))
@router.message(F.text.startswith("/delvip"))
async def f_delvip(message: Message):
    if not await is_primary_admin(message.from_user.id):
        return
    await admins.del_vip_handler(message=message)

@router.message(F.text.startswith("/vips"))
async def f_vips(message: Message):
    await admins.get_vip_users(message=message)

@router.message(F.text.startswith("/checkuser"))
async def f_checkuser(message: Message):
    await admins.check_user_exists(message=message)

@router.message(F.text.startswith("/check "))
async def f_check(message: Message):
    await admins.check_user_full_info(message=message)

@router.message(F.text.startswith("/zapravka1"))
async def f_zapravka1(message: Message):
    await admins.zapravka_olmosh_handler(message=message)

@router.message(F.text.startswith("/zapravka7"))
async def f_zapravka7(message: Message):
    await admins.zapravka_dollar_handler(message=message)

@router.message(F.text.startswith("/blocks"))
async def f_blocks(message: Message):
    await admins.block_users_lst_answer(message=message)

@router.message(F.text.startswith("/bust"))
async def f_bust(message: Message):
    await admins.bust_user_answer(message=message)

@router.message(F.text.startswith("/checkgaming"))
async def f_checkgaming(message: Message):
    await admins.check_gaming_groups_user(message=message)

@router.message(Command("stopgames"))
async def f_stopgames(message: Message, bot: Bot):
    await admins.stop_all_games_handler(message=message, bot=bot)

@router.message(Command("id"))
async def f_id(message: Message):
    await admins.get_chat_id(message=message)

@router.channel_post(F.text.startswith("/gtop"))
async def f_gtop(message: Message, bot: Bot):
    await statistika.gtop_global(message=message, bot=bot)

@router.message(Command("stats"))
async def f_stats(message: Message, bot: Bot):
    if not await is_primary_admin(message.from_user.id):
        await message.answer("Ushbu buyruq mavjud emas")
        return
    await statistika.bozor_statistikasi(message=message)

@router.message(Command("gboylar"))
async def f_gboylar(message: Message):
    if not await is_primary_admin(message.from_user.id):
        await message.answer("Ushbu buyruq mavjud emas")
        return
    await statistika.show_richest_users_in_this_chat(message=message)

@router.message(F.text.startswith("/block"))
async def f_block(message: Message):
    await admins.block_user_answer(message=message)

@router.message(F.text.startswith("/unblock"))
async def f_unblock(message: Message):
    await admins.unblock_user_answer(message=message)

@router.message(F.text.startswith("/gbust"))
async def f_gbust(message: Message):
    await admins.bust_group_balance(message=message)

@router.message(F.text.startswith("/setmoney") | F.text.startswith("/gmoney") | F.text.startswith("/set_gmoney"))
async def f_setmoney(message: Message):
    if not await is_primary_admin(message.from_user.id):
        await message.answer("Ushbu buyruq mavjud emas")
        return
    await admins.set_group_real_money(message=message)

@router.channel_post(F.text.startswith("/top"))
async def f_top(message: Message, bot: Bot):
    await statistika.get_stat_global(message=message, bot=bot)

@router.message(Command("error"))
async def f_error(message: Message):
    if not await is_primary_admin(message.from_user.id):
        await message.answer("Ushbu buyruq mavjud emas")
        return
    if os.path.exists("error.log"):
        await message.answer_document(FSInputFile("error.log"))

@router.message(Command("groups"), F.chat.type == "private")
async def f_groups(message: Message, bot: Bot):
    await admins.get_groups_list(message=message)

@router.callback_query(F.data.startswith("group_info_"))
async def f_group_info(call: CallbackQuery, bot: Bot):
    await admins.get_group_info(call=call, bot=bot)

@router.callback_query(F.data == "admin_groups_list")
async def f_admin_groups_list(call: CallbackQuery, bot: Bot):
    await admins.get_groups_list(message=call.message)
    await call.answer()

@router.message(Command("active"), F.chat.type == "private")
async def f_active(message: Message):
    await admins.find_active_game(message=message)

@router.callback_query(F.data.startswith("groups_page_"))
async def f_groups_page(call: CallbackQuery, bot: Bot):
    await admins.paginate_groups_list(call=call, bot=bot)

@router.callback_query(F.data.startswith("group_delete_"))
async def f_group_delete(call: CallbackQuery, bot: Bot):
    await admins.block_the_group(call, bot)

@router.message(Command("geroys"), F.chat.type == "private")
async def f_geroys(message: Message):
    await admins.get_geroys_list(message=message)

@router.message(Command("tchat1"), F.chat.type == "private")
@router.message(Command("tchat7"), F.chat.type == "private")
@router.message(Command("tchat30"), F.chat.type == "private")
@router.message(Command("tchat"), F.chat.type == "private")
async def f_tchat(message: Message, bot: Bot):
    await statistika.get_chat_stats(message=message, bot=bot)

@router.message(Command("tchats"), F.chat.type == "private")
async def f_tchats(message: Message, bot: Bot):
    await statistika.get_detailed_chat_stats(message=message, bot=bot)


# ==========================================
# 📢 MAJBURIIY OBUNA BOSHQARUVI
# ==========================================

@router.callback_query(F.data == "adm_sub_menu")
async def adm_sub_menu_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await call.answer()
    await state.clear()
    channels = await RequiredChannel.all().order_by("-id")
    text = (
        "📢 <b>MAJBURIIY OBUNA KANALLARI BOSHQARUVI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Quyida qo'shilgan kanallar ro'yxati keltirilgan.\n"
        "Yangi kanal qo'shish yoki mavjudlarini o'chirish/faollashtirish uchun tugmalardan foydalaning:"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_sub_menu_kb(channels))

@router.callback_query(F.data == "adm_sub_add")
async def adm_sub_add_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await call.answer()
    await state.set_state(AdminSubStates.waiting_for_channel)
    text = (
        "➕ <b>YANGI KANAL QO'SHISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Kanalning <b>username</b> (@kanal_nomi), <b>linki</b> (https://t.me/kanal_nomi yoki taklif havolasi) "
        "yoki <b>ID si</b>ni yuboring.\n\n"
        "<i>⚠️ Eslatma: Bot ushbu kanalda <b>admin</b> bo'lishi shart, aks holda obunani tekshira olmaydi!</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_btn("adm_sub_menu"))

@router.message(AdminSubStates.waiting_for_channel)
async def adm_sub_save_channel(message: Message, state: FSMContext, bot: Bot):
    if not await is_primary_admin(message.from_user.id):
        return
    
    raw = message.text.strip() if message.text else ""
    if not raw:
        await message.answer("❌ Iltimos, kanal havolasi yoki username yuboring!")
        return

    channel_id = None
    username = None
    invite_link = raw
    title = "Kanal"

    target = None
    if raw.startswith("@"):
        target = raw
        username = raw
    elif "t.me/" in raw:
        parts = raw.split("t.me/")[-1].split("/")
        candidate = parts[0].strip()
        if candidate.startswith("+") or candidate.startswith("joinchat"):
            invite_link = raw
            target = None
        else:
            username = "@" + candidate.lstrip("@")
            target = username
            invite_link = raw
    elif raw.lstrip("-").isdigit():
        target = int(raw)
        channel_id = str(raw)

    if target:
        try:
            chat = await bot.get_chat(target)
            title = chat.title or "Kanal"
            channel_id = str(chat.id)
            if chat.username:
                username = f"@{chat.username}"
                if not invite_link or "t.me" not in invite_link:
                    invite_link = f"https://t.me/{chat.username}"
            elif chat.invite_link:
                invite_link = chat.invite_link
        except Exception as e:
            await message.answer(
                f"⚠️ Chat ma'lumotlarini olishda ogohlantirish: {e}\n"
                "Kanal baribir saqlanadi. Bot ushbu kanalda admin ekanligiga ishonch hosil qiling!"
            )

    ch = await RequiredChannel.create(
        title=title,
        channel_id=channel_id,
        invite_link=invite_link,
        username=username,
        is_active=True
    )
    await state.clear()

    channels = await RequiredChannel.all().order_by("-id")
    await message.answer(
        f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📌 Nom: <b>{ch.title}</b>\n"
        f"🔗 Havola: {ch.invite_link}\n"
        f"🆔 ID: <code>{ch.channel_id or 'Noma’lum'}</code>",
        parse_mode="HTML",
        reply_markup=admin_sub_menu_kb(channels)
    )

@router.callback_query(F.data.startswith("adm_sub_info_"))
async def adm_sub_info_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    ch_id = int(call.data.split("_")[-1])
    ch = await RequiredChannel.get_or_none(id=ch_id)
    if not ch:
        await call.answer("Kanal topilmadi!", show_alert=True)
        return
        
    status = "🟢 Faol" if ch.is_active else "🔴 Faol emas"
    cid = ch.channel_id or "Mavjud emas"
    uname = ch.username or "Mavjud emas"
    text = (
        f"📢 <b>KANAL MA'LUMOTLARI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Nomi: <b>{ch.title}</b>\n"
        f"🔗 Havola: {ch.invite_link}\n"
        f"🆔 ID: <code>{cid}</code>\n"
        f"👤 Username: {uname}\n"
        f"⚡️ Holati: <b>{status}</b>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_sub_detail_kb(ch.id, ch.is_active))
    await call.answer()

@router.callback_query(F.data.startswith("adm_sub_toggle_"))
async def adm_sub_toggle_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    ch_id = int(call.data.split("_")[-1])
    ch = await RequiredChannel.get_or_none(id=ch_id)
    if not ch:
        await call.answer("Kanal topilmadi!", show_alert=True)
        return
    ch.is_active = not ch.is_active
    await ch.save()
    
    status = "🟢 Faol" if ch.is_active else "🔴 Faol emas"
    cid = ch.channel_id or "Mavjud emas"
    uname = ch.username or "Mavjud emas"
    text = (
        f"📢 <b>KANAL MA'LUMOTLARI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Nomi: <b>{ch.title}</b>\n"
        f"🔗 Havola: {ch.invite_link}\n"
        f"🆔 ID: <code>{cid}</code>\n"
        f"👤 Username: {uname}\n"
        f"⚡️ Holati: <b>{status}</b>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_sub_detail_kb(ch.id, ch.is_active))
    await call.answer(f"Kanal holati ozgartirildi: {status}")

@router.callback_query(F.data.startswith("adm_sub_del_"))
async def adm_sub_del_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    ch_id = int(call.data.split("_")[-1])
    ch = await RequiredChannel.get_or_none(id=ch_id)
    if ch:
        await ch.delete()
        await call.answer("Kanal o'chirildi!", show_alert=True)
    else:
        await call.answer()
    
    channels = await RequiredChannel.all().order_by("-id")
    text = (
        "📢 <b>MAJBURIIY OBUNA KANALLARI BOSHQARUVI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Quyida qo'shilgan kanallar ro'yxati keltirilgan.\n"
        "Yangi kanal qo'shish yoki mavjudlarini o'chirish/faollashtirish uchun tugmalardan foydalaning:"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_sub_menu_kb(channels))


# ==========================================
# 📢 XABAR TARQATISH (BROADCAST)
# ==========================================

@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_menu_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await call.answer()
    await state.clear()
    text = (
        "📢 <b>XABAR TARQATISH (BROADCAST)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Kimlarga xabar tarqatmoqchisiz?\n"
        "<i>Kerakli bo'limni tanlang:</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_broadcast_menu_kb())

@router.callback_query(F.data.in_(["adm_bcast_users", "adm_bcast_groups"]))
async def adm_bcast_target_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await call.answer()
    target = "users" if call.data == "adm_bcast_users" else "groups"
    await state.set_state(AdminBroadcastStates.waiting_for_message)
    await state.update_data(bcast_target=target)
    
    target_str = "Foydalanuvchilarga" if target == "users" else "Guruhlarga"
    text = (
        f"📢 <b>{target_str.upper()} XABAR TARQATISH</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Tarqatmoqchi bo'lgan xabaringizni yuboring (Matn, Rasm, Video, Stiker yoki Forward xabar).\n\n"
        f"<i>Xabar o'z holaticha barcha {target_str.lower()}ga yetkaziladi.</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_btn("adm_broadcast"))

@router.message(AdminBroadcastStates.waiting_for_message)
async def adm_bcast_send_msg(message: Message, state: FSMContext, bot: Bot):
    if not await is_primary_admin(message.from_user.id):
        return
    data = await state.get_data()
    target = data.get("bcast_target", "users")
    await state.clear()

    from asyncio import create_task
    create_task(execute_broadcast_task(bot=bot, target=target, message=message, admin_id=message.from_user.id))



