from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.premium_emojis import (
    ACTIVE_ROLES_TINCH, ACTIVE_ROLES_MAFIA, ACTIVE_ROLES_YAKKA,
    ALL_ACTIVE_ROLES, WEAPON_NAMES, CURRENCY_NAMES,
    get_custom_emoji, get_diamond_display, get_dollar_display,
    get_item_display
)

def admin_emoji_main_menu() -> InlineKeyboardMarkup:
    """Asosiy Admin Panel menyusi"""
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
        InlineKeyboardButton(text="📢 Xabar yuborish (Broadcast)", callback_data="adm_broadcast"),
        InlineKeyboardButton(text="📢 Majburiy obuna", callback_data="adm_sub_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Barcha emojilarni tozalash", callback_data="adm_emj_reset_confirm")
    )
    return builder.as_markup()


def admin_sub_menu_kb(channels) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status = "🟢" if ch.is_active else "🔴"
        builder.row(
            InlineKeyboardButton(text=f"{status} {ch.title}", callback_data=f"adm_sub_info_{ch.id}")
        )
    builder.row(
        InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="adm_sub_add")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="adm_emj_main")
    )
    return builder.as_markup()

def admin_sub_detail_kb(ch_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = "🔴 O'chirish (Deaktiv)" if is_active else "🟢 Yoqish (Aktiv)"
    builder.row(
        InlineKeyboardButton(text=toggle_text, callback_data=f"adm_sub_toggle_{ch_id}"),
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adm_sub_del_{ch_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Kanallar ro'yxatiga", callback_data="adm_sub_menu")
    )
    return builder.as_markup()


def admin_emoji_roles_categories_menu() -> InlineKeyboardMarkup:
    """Rollar toifalari menyusi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏛 Tinch aholi rollari (13 ta)", callback_data="adm_emj_cat_tinch")
    )
    builder.row(
        InlineKeyboardButton(text="🤵 Mafia rollari (6 ta)", callback_data="adm_emj_cat_mafia")
    )
    builder.row(
        InlineKeyboardButton(text="⚔️ Yakka rollar (10 ta)", callback_data="adm_emj_cat_yakka")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="adm_emj_main")
    )
    return builder.as_markup()

def admin_emoji_roles_list_menu(category: str) -> InlineKeyboardMarkup:
    """Kategoriya bo'yicha rollar ro'yxati"""
    if category == "tinch":
        roles = ACTIVE_ROLES_TINCH
    elif category == "mafia":
        roles = ACTIVE_ROLES_MAFIA
    else:
        roles = ACTIVE_ROLES_YAKKA

    builder = InlineKeyboardBuilder()
    for r in roles:
        custom = get_custom_emoji("roles", r)
        status_icon = "✨" if custom else "▫️"
        idx = ALL_ACTIVE_ROLES.index(r)
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
    builder.adjust(2)
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
    builder.row(
        InlineKeyboardButton(text="👤 Foydalanuvchilarga tarqatish", callback_data="adm_bcast_users"),
        InlineKeyboardButton(text="👥 Guruhlarga tarqatish", callback_data="adm_bcast_groups")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="adm_emj_main")
    )
    return builder.as_markup()


def admin_vip_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="adm_main")
    return builder.as_markup()

def admin_logs_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="adm_main")
    return builder.as_markup()