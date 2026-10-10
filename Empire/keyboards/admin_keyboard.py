from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.premium_emojis import (
    get_active_tinch, get_active_mafia, get_active_yakka, get_all_active_roles,
    WEAPON_NAMES, CURRENCY_NAMES,
    get_custom_emoji, get_diamond_display, get_dollar_display,
    get_item_display
)

async def admin_emoji_main_menu() -> InlineKeyboardMarkup:
    """Asosiy Premium Emoji Admin Panel menyusi"""
    from utils.webapp_config import get_webapp_button_text
    webapp_btn_text = await get_webapp_button_text()

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎭 Rollar emojilari", callback_data="adm_emj_roles_menu"),
        InlineKeyboardButton(text="⚔️ Qurol-aslahalar", callback_data="adm_emj_weapons_menu")
    )
    d_display = get_diamond_display()
    m_display = get_dollar_display()
    builder.row(
        InlineKeyboardButton(text=f"💎 Olmos ({d_display})", callback_data="adm_emj_currency_diamond"),
        InlineKeyboardButton(text=f"💵 Dollar ({m_display})", callback_data="adm_emj_currency_dollar")
    )
    builder.row(
        InlineKeyboardButton(text=webapp_btn_text, callback_data="adm_toggle_webapp")
    )
    builder.row(
        InlineKeyboardButton(text="💾 BARCHA EMOJILARNI BAZAGA SAQLASH", callback_data="adm_emj_save_to_db")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 BAZADAN QAYTA TIKLASH", callback_data="adm_emj_load_from_db")
    )
    builder.row(
        InlineKeyboardButton(text="👑 Adminlar ro'yxati", callback_data="adm_admins_list_0"),
        InlineKeyboardButton(text="🚫 Banlanganlar", callback_data="adm_blocked_list_0")
    )
    builder.row(
        InlineKeyboardButton(text="🔴 🚨 BARCHA EMOJILARNI TOZALASH 🚨 🔴", callback_data="adm_emj_reset_ask")
    )
    return builder.as_markup()

def admin_emoji_reset_confirm_menu() -> InlineKeyboardMarkup:
    """Emojilarni tozalashni tasdiqlash menyusi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔴 Ha, tasdiqlayman (ortga qaytarilmaydi)", callback_data="adm_emj_reset_do")
    )
    builder.row(
        InlineKeyboardButton(text="🔵 ⬅️ Ortga qaytish", callback_data="adm_emj_main")
    )
    return builder.as_markup()

def admin_emoji_roles_categories_menu() -> InlineKeyboardMarkup:
    """Rollar toifalari menyusi"""
    tinch_cnt = len(get_active_tinch())
    mafia_cnt = len(get_active_mafia())
    yakka_cnt = len(get_active_yakka())

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"🏛 Tinch aholi rollari ({tinch_cnt} ta)", callback_data="adm_emj_cat_tinch")
    )
    builder.row(
        InlineKeyboardButton(text=f"🤵 Mafia rollari ({mafia_cnt} ta)", callback_data="adm_emj_cat_mafia")
    )
    builder.row(
        InlineKeyboardButton(text=f"⚔️ Yakka rollar ({yakka_cnt} ta)", callback_data="adm_emj_cat_yakka")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="adm_emj_main")
    )
    return builder.as_markup()

def admin_emoji_roles_list_menu(category: str) -> InlineKeyboardMarkup:
    """Kategoriya bo'yicha rollar ro'yxati"""
    if category == "tinch":
        roles = get_active_tinch()
    elif category == "mafia":
        roles = get_active_mafia()
    else:
        roles = get_active_yakka()

    all_roles = get_all_active_roles()
    builder = InlineKeyboardBuilder()
    for r in roles:
        custom = get_custom_emoji("roles", r)
        status_icon = "✨" if custom else "▫️"
        idx = all_roles.index(r)
        builder.button(
            text=f"{status_icon} {r}",
            callback_data=f"adm_emj_role_{idx}"
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="🔙 Rollar bo'limiga", callback_data="adm_emj_roles_menu")
    )
    return builder.as_markup()

def admin_emoji_weapons_list_menu() -> InlineKeyboardMarkup:
    """Qurol-aslahalar ro'yxati"""
    builder = InlineKeyboardBuilder()
    for key, (icon, name) in WEAPON_NAMES.items():
        custom = get_custom_emoji("weapons", key)
        status_icon = "✨" if custom else "▫️"
        cur_icon = custom if custom else icon
        builder.button(
            text=f"{status_icon} {cur_icon} {name}",
            callback_data=f"adm_emj_wpn_{key}"
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="adm_emj_main")
    )
    return builder.as_markup()

def admin_emoji_item_actions_menu(category: str, key: str, back_cb: str) -> InlineKeyboardMarkup:
    """Bitta element uchun boshqaruv tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Premium emoji o'rnatish", callback_data=f"adm_emj_set_{category}_{key}"),
        InlineKeyboardButton(text="❌ Emojini o'chirish", callback_data=f"adm_emj_del_{category}_{key}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=back_cb)
    )
    return builder.as_markup()

def admin_back_btn(target_callback: str = "adm_emj_main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data=target_callback)
    return builder.as_markup()

async def groups_list_button(chats, page: int, total_pages: int):
    buttons = [
        [InlineKeyboardButton(text=chat.title or "Nomsiz", callback_data=f"group_info_{chat.chat_id}")]
        for chat in chats
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⏪ Oldingi", callback_data=f"groups_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="⏩ Keyingi", callback_data=f"groups_page_{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def group_button(url, chat_id):
    builder = InlineKeyboardBuilder()
    if url:
        builder.button(text="Kirish", url=url)
    builder.button(text="O'chirish", callback_data=f"group_delete_{chat_id}")
    builder.button(text="Orqaga", callback_data="admin_groups_list")
    builder.adjust(2)
    return builder.as_markup()

def back_groups_list_btn():
    builder = InlineKeyboardBuilder()
    builder.button(text="Orqaga", callback_data="admin_groups_list")
    return builder.as_markup()

def admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Foydalanuvchilar", callback_data="adm_users")
    builder.button(text="🎮 O'yinlar", callback_data="adm_games")
    builder.button(text="👑 VIP a'zolar", callback_data="adm_vips")
    builder.button(text="📢 Xabar yuborish", callback_data="adm_broadcast")
    builder.button(text="📜 Loglar", callback_data="adm_logs")
    builder.button(text="🎨 Emojilar", callback_data="adm_emj_main")
    builder.button(text="🤡 Mem panel", callback_data="adm_meme_main")
    builder.adjust(2)
    return builder.as_markup()

def admin_meme_menu(enabled: bool, has_text: bool = False, has_sticker: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    status_text = "🔴 O'chirish" if enabled else "🟢 Yoqish"
    builder.row(
        InlineKeyboardButton(text=f"Holat: {status_text}", callback_data="adm_meme_toggle")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Matnni sozlash", callback_data="adm_meme_set_text"),
        InlineKeyboardButton(text="🎭 Stiker/Rasm sozlash", callback_data="adm_meme_set_sticker")
    )
    extra_row = []
    if has_text:
        extra_row.append(InlineKeyboardButton(text="🔄 Matnni tiklash", callback_data="adm_meme_reset_text"))
    if has_sticker:
        extra_row.append(InlineKeyboardButton(text="🗑 Stikerni o'chirish", callback_data="adm_meme_del_sticker"))
    if extra_row:
        builder.row(*extra_row)
    builder.row(
        InlineKeyboardButton(text="🔙 Admin panel", callback_data="adm_emj_main")
    )
    return builder.as_markup()

def admin_users_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Qidirish", callback_data="adm_user_search")
    builder.button(text="🔙 Orqaga", callback_data="adm_main")
    builder.adjust(1)
    return builder.as_markup()

def admin_user_manage_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="adm_users")
    return builder.as_markup()

def admin_games_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="adm_main")
    return builder.as_markup()

def admin_broadcast_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="adm_main")
    return builder.as_markup()

def admin_vip_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="adm_main")
    return builder.as_markup()

def admin_logs_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="adm_main")
    return builder.as_markup()

def admin_list_keyboard(admins: list, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in admins:
        name = u.full_name or f"User_{u.user_id}"
        builder.row(
            InlineKeyboardButton(
                text=f"👑 {name} ({u.user_id})",
                callback_data=f"adm_manage_{u.user_id}"
            )
        )
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"adm_admins_list_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Keyingisi", callback_data=f"adm_admins_list_{page+1}"))
    if nav_buttons:
        builder.row(*nav_buttons)
    builder.row(
        InlineKeyboardButton(text="🔙 Admin panel", callback_data="adm_emj_main")
    )
    return builder.as_markup()

def admin_single_manage_kb(target_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Adminlikdan olish", callback_data=f"adm_action_remove_{target_id}"),
        InlineKeyboardButton(text="🚫 Ban qilish", callback_data=f"adm_action_ban_{target_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm_admins_list_0")
    )
    return builder.as_markup()

def blocked_list_keyboard(page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"adm_blocked_list_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Keyingisi", callback_data=f"adm_blocked_list_{page+1}"))
    if nav_buttons:
        builder.row(*nav_buttons)
    builder.row(
        InlineKeyboardButton(text="❌ Yopish", callback_data="adm_close"),
        InlineKeyboardButton(text="🔙 Admin panel", callback_data="adm_emj_main")
    )
    return builder.as_markup()