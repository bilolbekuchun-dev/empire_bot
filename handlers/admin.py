import os
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from utils import admins, statistika
from utils.premium_emojis import (
    get_active_tinch, get_active_mafia, get_active_yakka, get_all_active_roles,
    WEAPON_NAMES, CURRENCY_NAMES,
    get_custom_emoji, set_custom_emoji, reset_all_custom_emojis,
    parse_emoji_from_message, role_display, get_item_display,
    get_diamond_display, get_dollar_display,
    sync_emojis_from_db, _load_config
)
from states.admin_states import AdminEmojiStates
from keyboards.admin_keyboard import (
    admin_emoji_main_menu, admin_emoji_roles_categories_menu,
    admin_emoji_roles_list_menu, admin_emoji_weapons_list_menu,
    admin_emoji_item_actions_menu, admin_back_btn,
    admin_emoji_reset_confirm_menu, admin_meme_menu
)
from config import ADMINS, PRIMARY_ADMIN_ID, PRIMARY_ADMIN_IDS

router = Router()

HARDCODED_ADMINS = set()

async def is_primary_admin(user_id: int) -> bool:
    """Faqatgina ruxsat berilgan 2 ta SUPER ADMIN (8765051736, 6913838682) boshqara oladi va admin panelni ko'radi"""
    if not user_id:
        return False
    return user_id in PRIMARY_ADMIN_IDS

# ==========================================
# 👑 ASOSIY PREMIUM EMOJI ADMIN PANEL
# ==========================================

def get_main_panel_text() -> str:
    d_display = get_diamond_display()
    m_display = get_dollar_display()
    text = (
        "🎨 <b>PREMIUM EMOJI BOSHQARUV PANELI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Bu yerdan o'yin rollari, qurol-aslahalar, olmos va dollar uchun "
        "maxsus <b>Premium Emojilarni</b> o'rnatishingiz va boshqarishingiz mumkin.\n\n"
        f"• 💎 <b>Olmos:</b> {d_display}\n"
        f"• 💵 <b>Dollar:</b> {m_display}\n\n"
        "<i>Kerakli bo'limni tanlang:</i>"
    )
    return text

@router.message(Command("admin"))
@router.message(Command("panel"))
async def admin_panel_cmd(message: Message, state: FSMContext, bot: Bot):
    if not await is_primary_admin(message.from_user.id):
        return
    await state.clear()
    text = get_main_panel_text()
    reply_markup = await admin_emoji_main_menu()

    # Guruhda yoki kanalda yozilsa, panelni bot PM (lichka) iga yuboradi
    if message.chat.type != "private":
        try:
            await message.delete()
        except Exception:
            pass
        try:
            await bot.send_message(
                chat_id=message.from_user.id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"PM admin panel yuborishda xato: {e}")
        return

    await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)

@router.callback_query(F.data == "adm_emj_main")
async def adm_emj_main_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    await state.clear()
    text = get_main_panel_text()
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=await admin_emoji_main_menu())
    await call.answer()

@router.callback_query(F.data == "adm_toggle_webapp")
async def adm_toggle_webapp_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    from utils.webapp_config import is_webapp_active, set_webapp_active
    curr = await is_webapp_active()
    new_status = not curr
    await set_webapp_active(new_status)
    status_str = "🟢 Yoqildi! (Mini App ishlaydi)" if new_status else "🔴 O'chirildi! (Mini App yashirildi)"
    await call.answer(f"WebApp holati: {status_str}", show_alert=True)
    kb = await admin_emoji_main_menu()
    await call.message.edit_reply_markup(reply_markup=kb)



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
    cnt = len(get_active_tinch())
    text = f"🏛 <b>Tinch aholi rollari ({cnt} ta):</b>\n\nEmoji o'rnatmoqchi bo'lgan rolni tanlang:"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_roles_list_menu("tinch"))
    await call.answer()

@router.callback_query(F.data == "adm_emj_cat_mafia")
async def adm_emj_cat_mafia_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    cnt = len(get_active_mafia())
    text = f"🤵 <b>Mafia rollari ({cnt} ta):</b>\n\nEmoji o'rnatmoqchi bo'lgan rolni tanlang:"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_roles_list_menu("mafia"))
    await call.answer()

@router.callback_query(F.data == "adm_emj_cat_yakka")
async def adm_emj_cat_yakka_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    cnt = len(get_active_yakka())
    text = f"⚔️ <b>Yakka va Neytral rollar ({cnt} ta):</b>\n\nEmoji o'rnatmoqchi bo'lgan rolni tanlang:"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_roles_list_menu("yakka"))
    await call.answer()

@router.callback_query(F.data.startswith("adm_emj_role_"))
async def adm_emj_role_view_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    idx = int(call.data.replace("adm_emj_role_", ""))
    all_roles = get_all_active_roles()
    if idx >= len(all_roles):
        return
    role_name = all_roles[idx]
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
        all_roles = get_all_active_roles()
        key = all_roles[idx]
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
        all_roles = get_all_active_roles()
        target_name = all_roles[idx]
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

    real_key = None
    if category == "roles":
        idx = int(raw_key)
        all_roles = get_all_active_roles()
        real_key = all_roles[idx]
        set_custom_emoji("roles", real_key, emoji_html)
    elif category == "weapons":
        set_custom_emoji("weapons", raw_key, emoji_html)
    elif category == "currency":
        set_custom_emoji("currency", raw_key, emoji_html)

    # DARHOL (0-soniyada) PostgreSQL bazaga ham saqlash
    try:
        from models.game_set import CustomEmojiConfig
        target_k = real_key if category == "roles" else raw_key
        await CustomEmojiConfig.update_or_create(
            category=category,
            key=target_k,
            defaults={"emoji_html": emoji_html}
        )
    except Exception as db_err:
        print(f"Error auto-saving emoji to DB: {db_err}")

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

@router.callback_query(F.data == "adm_emj_reset_ask")
async def adm_emj_reset_ask_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    text = (
        "⚠️ <b>OGOHLANTIRISH!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Siz barcha o'rnatilgan <b>Premium Emojilarni</b> o'chirib tashlamoqchisiz!\n"
        "<i>Ushbu amalni ortga qaytarib bo'lmaydi!</i> Barcha sozlangan emojilar tozalanadi "
        "va qaytadan kiritishingizga to'g'ri keladi.\n\n"
        "Haqiqatan ham barcha emojilarni tozalamoqchimisiz?"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_emoji_reset_confirm_menu())
    await call.answer()

@router.callback_query(F.data == "adm_emj_reset_do")
async def adm_emj_reset_do_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    reset_all_custom_emojis()
    await call.answer("🗑 Barcha maxsus premium emojilar tozalandi va standart holatga qaytarildi!", show_alert=True)
    text = get_main_panel_text()
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=await admin_emoji_main_menu())

@router.callback_query(F.data == "adm_emj_save_to_db")
async def adm_emj_save_to_db_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    try:
        from models.game_set import CustomEmojiConfig
        config = _load_config()
        count = 0
        for category, items in config.items():
            if isinstance(items, dict):
                for key, val in items.items():
                    if val:
                        await CustomEmojiConfig.update_or_create(
                            category=category,
                            key=key,
                            defaults={"emoji_html": val}
                        )
                        count += 1
        await call.answer(f"💾 {count} ta premium emoji PostgreSQL bazaga muvaffaqiyatli saqlandi! Redeploy bo'lganda ham saqlanib qoladi.", show_alert=True)
    except Exception as e:
        await call.answer(f"❌ Saqlashda xatolik: {str(e)}", show_alert=True)

@router.callback_query(F.data == "adm_emj_load_from_db")
async def adm_emj_load_from_db_cb(call: CallbackQuery):
    if not await is_primary_admin(call.from_user.id):
        return
    try:
        await sync_emojis_from_db()
        await call.answer("🔄 Barcha premium emojilar bazadan qayta tiklandi va yangilandi!", show_alert=True)
        text = get_main_panel_text()
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=await admin_emoji_main_menu())
    except Exception as e:
        await call.answer(f"❌ Tiklashda xatolik: {str(e)}", show_alert=True)

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
    await message.answer("⚠️ Adminlar faqat konfiguratsiya (variables) orqali boshqariladi.", parse_mode="HTML")

@router.message(Command("deladmin"))
@router.message(F.text.startswith("/deladmin"))
async def f_deladmin(message: Message):
    await message.answer("⚠️ Adminlar faqat konfiguratsiya (variables) orqali boshqariladi.", parse_mode="HTML")

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
        return
    await statistika.bozor_statistikasi(message=message)

@router.message(Command("gboylar"))
async def f_gboylar(message: Message):
    if not await is_primary_admin(message.from_user.id):
        return
    await statistika.show_richest_users_in_this_chat(message=message)


@router.message(Command("admins"))
@router.message(Command("admin_list"))
async def f_admins_cmd(message: Message):
    await admins.show_admins_list(message, page=0)

@router.message(Command("ban_list"))
@router.message(Command("banlar"))
@router.message(Command("banned"))
async def f_ban_list_cmd(message: Message):
    await admins.show_blocked_list(message, page=0)

@router.message(Command("addadmin"))
@router.message(Command("add_admin"))
async def f_add_admin_cmd(message: Message):
    await admins.add_admin_answer(message)

@router.callback_query(F.data.startswith("adm_admins_list_"))
async def f_adm_admins_list_cb(call: CallbackQuery):
    page = int(call.data.replace("adm_admins_list_", ""))
    await admins.show_admins_list(call, page=page)

@router.callback_query(F.data.startswith("adm_manage_"))
async def f_adm_manage_cb(call: CallbackQuery):
    target_id = int(call.data.replace("adm_manage_", ""))
    await admins.show_admin_detail(call, target_id=target_id)

@router.callback_query(F.data.startswith("adm_action_remove_"))
async def f_adm_action_remove_cb(call: CallbackQuery):
    target_id = int(call.data.replace("adm_action_remove_", ""))
    await admins.remove_bot_admin_handler(call, target_id=target_id)

@router.callback_query(F.data.startswith("adm_action_ban_"))
async def f_adm_action_ban_cb(call: CallbackQuery):
    target_id = int(call.data.replace("adm_action_ban_", ""))
    await admins.ban_bot_admin_handler(call, target_id=target_id)

@router.callback_query(F.data.startswith("adm_blocked_list_"))
async def f_adm_blocked_list_cb(call: CallbackQuery):
    page = int(call.data.replace("adm_blocked_list_", ""))
    await admins.show_blocked_list(call, page=page)

@router.callback_query(F.data == "adm_close")
async def f_adm_close_cb(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()

@router.message(F.text.startswith("/block") | F.text.startswith("/ban"))
async def f_block(message: Message):
    await admins.block_user_answer(message=message)

@router.message(F.text.startswith("/unblock") | F.text.startswith("/unban"))
async def f_unblock(message: Message):
    await admins.unblock_user_answer(message=message)

@router.message(F.text.startswith("/gbust"))
async def f_gbust(message: Message):
    await admins.bust_group_balance(message=message)

@router.message(F.text.startswith("/setmoney") | F.text.startswith("/gmoney") | F.text.startswith("/set_gmoney"))
async def f_setmoney(message: Message):
    if not await is_primary_admin(message.from_user.id):
        return
    await admins.set_group_real_money(message=message)

@router.channel_post(F.text.startswith("/top"))
async def f_top(message: Message, bot: Bot):
    await statistika.get_stat_global(message=message, bot=bot)

@router.message(Command("error"))
async def f_error(message: Message):
    if not await is_primary_admin(message.from_user.id):
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
# 🤡 MEM PANEL BOSHQARUVI
# ==========================================

async def get_meme_panel_data():
    from utils.database import redis_client as r
    enabled_raw = await r.get("meme_panel:enabled")
    enabled = (enabled_raw.decode() if isinstance(enabled_raw, bytes) else str(enabled_raw or "")) == "1"

    text_raw = await r.get("meme_panel:text")
    text = text_raw.decode() if isinstance(text_raw, bytes) else (str(text_raw) if text_raw else None)

    sticker_raw = await r.get("meme_panel:sticker")
    sticker = sticker_raw.decode() if isinstance(sticker_raw, bytes) else (str(sticker_raw) if sticker_raw else None)

    media_type_raw = await r.get("meme_panel:media_type")
    media_type = media_type_raw.decode() if isinstance(media_type_raw, bytes) else (str(media_type_raw) if media_type_raw else "stiker")

    return enabled, text, sticker, media_type


async def render_meme_panel_text() -> tuple[str, bool, bool, bool]:
    enabled, text, sticker, media_type = await get_meme_panel_data()
    status_str = "🟢 Yoqilgan (Erkaklar o'rtasida para so'rovi bloklanadi)" if enabled else "🔴 O'chiq (Standart rejim)"

    disp_text = text if text else "<i>(Default: Birodar, o'zingni bos! 😂 Erkaklar bir-biri bilan para bo'la olmaydi.)</i>"
    disp_sticker = f"<code>{sticker}</code> ({media_type})" if sticker else "<i>(O'rnatilmagan)</i>"

    panel_text = (
        "🤡 <b>MEM PANEL BOSHQARUVI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Holat:</b> {status_str}\n\n"
        f"📝 <b>Sozlangan matn:</b>\n{disp_text}\n\n"
        f"🎭 <b>Sozlangan stiker/rasm:</b>\n{disp_sticker}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Kerakli amalni tanlang:</i>"
    )
    return panel_text, enabled, bool(text), bool(sticker)


@router.callback_query(F.data == "adm_meme_main")
async def adm_meme_main_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    await state.clear()
    panel_text, enabled, has_text, has_sticker = await render_meme_panel_text()
    kb = admin_meme_menu(enabled, has_text, has_sticker)
    await call.message.edit_text(panel_text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "adm_meme_toggle")
async def adm_meme_toggle_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    await state.clear()
    from utils.database import redis_client as r
    enabled_raw = await r.get("meme_panel:enabled")
    cur_enabled = (enabled_raw.decode() if isinstance(enabled_raw, bytes) else str(enabled_raw or "")) == "1"
    new_state = "0" if cur_enabled else "1"
    await r.set("meme_panel:enabled", new_state)

    panel_text, enabled, has_text, has_sticker = await render_meme_panel_text()
    kb = admin_meme_menu(enabled, has_text, has_sticker)
    await call.message.edit_text(panel_text, parse_mode="HTML", reply_markup=kb)
    status_msg = "🟢 Yoqildi" if enabled else "🔴 O'chirildi"
    await call.answer(f"Mem panel statusi: {status_msg}")


@router.callback_query(F.data == "adm_meme_set_text")
async def adm_meme_set_text_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    from states.admin_states import AdminMemeStates
    await state.set_state(AdminMemeStates.waiting_for_text)
    kb = admin_back_btn("adm_meme_main")
    text = (
        "✏️ <b>Yangi mem matnini yuboring:</b>\n\n"
        "<i>Erkak kishi erkakka /para so'rov yuborganda ushbu matn lichkaga yuboriladi.</i>\n"
        "<i>Masalan: Birodar, o'zingni bos! 😂 Erkaklar bir-biri bilan para bo'la olmaydi.</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.message(AdminMemeStates.waiting_for_text)
async def adm_meme_save_text(message: Message, state: FSMContext):
    if not await is_primary_admin(message.from_user.id):
        return
    from utils.database import redis_client as r
    await r.set("meme_panel:text", message.text)
    await state.clear()
    await message.answer("✅ <b>Mem matni muvaffaqiyatli saqlandi!</b>", parse_mode="HTML")
    panel_text, enabled, has_text, has_sticker = await render_meme_panel_text()
    kb = admin_meme_menu(enabled, has_text, has_sticker)
    await message.answer(panel_text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "adm_meme_set_sticker")
async def adm_meme_set_sticker_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    from states.admin_states import AdminMemeStates
    await state.set_state(AdminMemeStates.waiting_for_sticker)
    kb = admin_back_btn("adm_meme_main")
    text = (
        "🎭 <b>Mem stikerini yoki media faylini yuboring:</b>\n\n"
        "<i>Istalgan stiker, photo (rasm), GIF, video yoki video-eshtet yuborishingiz mumkin.</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.message(AdminMemeStates.waiting_for_sticker)
async def adm_meme_save_sticker(message: Message, state: FSMContext):
    if not await is_primary_admin(message.from_user.id):
        return
    from utils.database import redis_client as r
    file_id = None
    media_type = "sticker"

    if message.sticker:
        file_id = message.sticker.file_id
        media_type = "sticker"
    elif message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.animation:
        file_id = message.animation.file_id
        media_type = "animation"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    elif message.video_note:
        file_id = message.video_note.file_id
        media_type = "video_note"
    elif message.document:
        file_id = message.document.file_id
        media_type = "document"

    if not file_id:
        await message.answer("⚠️ Iltimos, stiker, rasm, GIF yoki video yuboring.")
        return

    await r.set("meme_panel:sticker", file_id)
    await r.set("meme_panel:media_type", media_type)
    await state.clear()
    await message.answer(f"✅ <b>Mem mediasi ({media_type}) saqlandi!</b>", parse_mode="HTML")
    panel_text, enabled, has_text, has_sticker = await render_meme_panel_text()
    kb = admin_meme_menu(enabled, has_text, has_sticker)
    await message.answer(panel_text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "adm_meme_reset_text")
async def adm_meme_reset_text_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    await state.clear()
    from utils.database import redis_client as r
    await r.delete("meme_panel:text")
    panel_text, enabled, has_text, has_sticker = await render_meme_panel_text()
    kb = admin_meme_menu(enabled, has_text, has_sticker)
    await call.message.edit_text(panel_text, parse_mode="HTML", reply_markup=kb)
    await call.answer("Matn default qiymatga tiklandi")


@router.callback_query(F.data == "adm_meme_del_sticker")
async def adm_meme_del_sticker_cb(call: CallbackQuery, state: FSMContext):
    if not await is_primary_admin(call.from_user.id):
        return
    await state.clear()
    from utils.database import redis_client as r
    await r.delete("meme_panel:sticker")
    await r.delete("meme_panel:media_type")
    panel_text, enabled, has_text, has_sticker = await render_meme_panel_text()
    kb = admin_meme_menu(enabled, has_text, has_sticker)
    await call.message.edit_text(panel_text, parse_mode="HTML", reply_markup=kb)
    await call.answer("Mem mediasi o'chirildi")

