from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.role_names import RoleNames
from models.game_set import NickList, NickListItem, NickModeSet


def set_command_permissions_button(chat_id):
    builder = InlineKeyboardBuilder()
    commands = [
        ("start", "start"),
        ("stop", "stop"),
        ("game", "game"),
        ("top1", "Top 1"),
        ("top7", "Top 7"),
        ("top30", "Top 30"),
        ("gtop1", "Taqdirlash Top 1"),
        ("gtop7", "Tadirlash Top 7"),
        ("gtop30", "Taqdirlash Top 30"),
        ("extend", "Extend"),
    ]
    for cmd, label in commands:
        builder.button(text=label, callback_data=f"set-cmdperm_{chat_id}_{cmd}")
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def game_mode_menu_btn(chat_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Modelar haqida", callback_data=f"set-gmode_{chat_id}_info")
    builder.button(text="Mode tanlash", callback_data=f"set-gmode_{chat_id}_select")
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def game_mode_info_btn(chat_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Super", callback_data=f"set-gmode_{chat_id}_info_super")
    builder.button(text="Super VS", callback_data=f"set-gmode_{chat_id}_info_super:vs")
    builder.button(text="Para x Super", callback_data=f"set-gmode_{chat_id}_info_para x super")
    builder.button(text="🔙 Orqaga", callback_data=f"set-gmode_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def game_mode_select_btn(chat_id, default="super"):
    builder = InlineKeyboardBuilder()
    modes = [
        ("super", "Super"), 
        ("super:vs", "Super VS"), 
        ("para x super", "Para x Super")
    ]
    for mode, label in modes:
        selected = "◾️" if default == mode else "▫️"
        builder.button(
            text=f"{label} {selected}",
            callback_data=f"set-gmode_{chat_id}_select_{mode}"
        )
    builder.button(text="🔙 Orqaga", callback_data=f"set-gmode_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def set_weapons_types_button(chat_id):
    builder = InlineKeyboardBuilder()
    weapons = [
        ("himoya", "🛡 Himoya"),
        ("hujjat", "📁 Hujjat"),
        ("qotildan-himoya", "⛑️ Qotildan himoya"),
        ("ovozdan-himoya", "⚖️ Ovozdan himoya"),
        ("miltiq", "🔫 Miltiq"),
        ("doridan-himoya", "💊 Doridan himoya"),
        ("slip-himoya", "🪤 Sirpanishdan himoya"),
        ("maska", "🎭 Maska"),
        ("geroy", "🥷 Geroy"),
        ("active-role", "🃏 Faol rol"),
    ]
    
    for weapon_key, weapon_name in weapons:
        builder.button(text=weapon_name, callback_data=f"set-weapons_{chat_id}_{weapon_key}")
    
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def set_weapons_combined_button(chat_id, weapon_set):
    builder = InlineKeyboardBuilder()
    weapons = [
        ("himoya", "🛡 Himoya"),
        ("hujjat", "📁 Hujjat"),
        ("qotildan-himoya", "⛑️ Qotildan himoya"),
        ("ovozdan-himoya", "⚖️ Ovozdan himoya"),
        ("miltiq", "🔫 Miltiq"),
        ("doridan-himoya", "💊 Doridan himoya"),
        ("slip-himoya", "🪤 Sirpanishdan himoya"),
        ("maska", "🎭 Maska"),
        ("geroy", "🥷 Geroy"),
        ("active-role", "🃏 Faol rol"),
    ]
    for weapon_key, weapon_name in weapons:
        weapon_db = weapon_key.replace("-", "_")
        is_on = getattr(weapon_set, weapon_db, True)
        status = "🟢 ON" if is_on else "🔴 OFF"
        new_value = 0 if is_on else 1
        builder.button(
            text=f"{weapon_name} - {status}",
            callback_data=f"set-weapons_{chat_id}_{weapon_key}_{new_value}"
        )
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()

def set_weapons_values_button(chat_id, weapon, default=True):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Yoqish {'◾️' if default == True else '▫️'}", callback_data=f"set-weapons_{chat_id}_{weapon}_1")
    builder.button(text=f"O'chirish {'◾️' if default == False else '▫️'}", callback_data=f"set-weapons_{chat_id}_{weapon}_0")
    builder.button(text="🔙 Orqaga", callback_data=f"set-weapons_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()

def set_command_permission_values_button(chat_id, cmd, default="admin"):
    builder = InlineKeyboardBuilder()
    options = [("admin", "Admin"), ("member", "Obunachilar"), ("ega", "Ega")]
    for value, label in options:
        selected = "◾️" if default == value else "▫️"
        builder.button(
            text=f"{label} {selected}",
            callback_data=f"set-cmdperm_{chat_id}_{cmd}_{value}"
        )
    builder.button(text="🔙 Orqaga", callback_data=f"set-cmdperm_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def open_settings_button(chat_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Giveawaylar", callback_data=f"set-give_{chat_id}")
    builder.button(text="Vaqtlar", callback_data=f"set-time_{chat_id}")
    builder.button(text="Rollar", callback_data=f"set-roles_{chat_id}")
    builder.button(text="Himoyalar", callback_data=f"set-weapons_{chat_id}")
    builder.button(text="leave qilish", callback_data=f"set-leave_{chat_id}")
    builder.button(text="Buyruqlarga ruxsatlar", callback_data=f"set-cmdperm_{chat_id}")
    builder.button(text="Yozishni cheklash", callback_data=f"set-wgroupperm_{chat_id}")
    builder.button(text="O'yin modini sozlash", callback_data=f"set-gmode_{chat_id}")
    # builder.button(text="Nik to'plamlari", callback_data=f"set-nickpacks_{chat_id}")
    builder.button(text="Boshqa sozlamalar", callback_data=f"set-more_{chat_id}")
    builder.button(text="Chiqish", callback_data=f"del_msg")
    builder.adjust(1)
    return builder.as_markup()

def nickpack_menu_btn(chat_id, nick_lists: list[NickList], nick_mode: NickModeSet):
    builder = InlineKeyboardBuilder()
    for item in nick_lists:
        selected = "◾️" if nick_mode.selected_nicklist == item.name else "▫️"
        builder.button(
            text=f"{selected} {item.name}",
            callback_data=f"set-nickpacks_{chat_id}_select_{item.id}"
        )
    builder.button(text="To'plam yaratish", callback_data=f"set-nickpacks_{chat_id}_create")
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def back_set_menu(chat_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    return builder.as_markup()

def set_more_types_button(chat_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Mafianing ovozi", callback_data=f"set-more_{chat_id}_mafs-vote")
    builder.button(text="Advokatni ko'rish", callback_data=f"set-more_{chat_id}_adv-view")
    builder.button(text="Maksimal o'yinchilar soni", callback_data=f"set-more_{chat_id}_max-players")
    builder.button(text="Rollarni guruhlash", callback_data=f"set-more_{chat_id}_rollarni-guruhlash")
    builder.button(text="Bo'ri yoki tulki", callback_data=f"set-more_{chat_id}_wolf-or-fox")
    builder.button(text="O'yin o'ynashni cheklash", callback_data=f"set-more_{chat_id}_can-gaming")
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def wolf_or_fox_btn(chat_id, default=True):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Bo'ri {'◾️' if default == True else '▫️'}", callback_data=f"set-more_{chat_id}_wolf-or-fox_1")
    builder.button(text=f"Tulki {'◾️' if default == False else '▫️'}", callback_data=f"set-more_{chat_id}_wolf-or-fox_0") 
    builder.button(text="🔙 Orqaga", callback_data=f"set-more_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def can_gaming_btn(chat_id, default=True):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Ha {'◾️' if default == True else '▫️'}", callback_data=f"set-more_{chat_id}_can-gaming_1")
    builder.button(text=f"Yo'q {'◾️' if default == False else '▫️'}", callback_data=f"set-more_{chat_id}_can-gaming_0")
    builder.button(text="🔙 Orqaga", callback_data=f"set-more_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()

def set_max_players_values_button(chat_id, more_type, default=30):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"10 {'◾️' if default == 10 else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_10")
    builder.button(text=f"15 {'◾️' if default == 15 else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_15")
    builder.button(text=f"20 {'◾️' if default == 20 else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_20")
    builder.button(text=f"25 {'◾️' if default == 25 else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_25")
    builder.button(text=f"30 {'◾️' if default == 30 else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_30")
    builder.button(text=f"35 {'◾️' if default == 35 else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_35")
    builder.button(text=f"40 {'◾️' if default == 40 else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_40")
    builder.button(text=f"45 {'◾️' if default == 45 else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_45")
    builder.button(text="🔙 Orqaga", callback_data=f"set-more_{chat_id}")
    builder.adjust(3, 2, 1)
    return builder.as_markup()

def set_mafs_vote_button(chat_id, more_type, default=True):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Ha {'◾️' if default == True else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_0")
    builder.button(text=f"Yo'q {'◾️' if default == False else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_1")
    builder.button(text="🔙 Orqaga", callback_data=f"set-more_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()

def set_rollarni_guruhlash_button(chat_id, more_type, default=True):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Ha {'◾️' if default == True else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_0")
    builder.button(text=f"Yo'q {'◾️' if default == False else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_1")
    builder.button(text="🔙 Orqaga", callback_data=f"set-more_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()

def set_adv_view_button(chat_id, more_type, default=True):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Ha {'◾️' if default == True else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_0")
    builder.button(text=f"Yo'q {'◾️' if default == False else '▫️'}", callback_data=f"set-more_{chat_id}_{more_type}_1")
    builder.button(text="🔙 Orqaga", callback_data=f"set-more_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()

def set_give_types_button(chat_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Olmoslar", callback_data=f"set-give_{chat_id}_diamond")
    builder.button(text="Himoyalar", callback_data=f"set-give_{chat_id}_dollar")
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def set_give_values_button(chat_id, give_type, default=45):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"0 {'◾️' if default == 0 else '▫️'}", callback_data=f"set-give_{chat_id}_{give_type}_0")
    builder.button(text=f"10 {'◾️' if default == 10 else '▫️'}", callback_data=f"set-give_{chat_id}_{give_type}_10")
    builder.button(text=f"20 {'◾️' if default == 20 else '▫️'}", callback_data=f"set-give_{chat_id}_{give_type}_20")
    builder.button(text=f"30 {'◾️' if default == 30 else '▫️'}", callback_data=f"set-give_{chat_id}_{give_type}_30")
    builder.button(text=f"40 {'◾️' if default == 40 else '▫️'}", callback_data=f"set-give_{chat_id}_{give_type}_40")
    builder.button(text=f"50 {'◾️' if default == 50 else '▫️'}", callback_data=f"set-give_{chat_id}_{give_type}_50")
    builder.button(text="🔙 Orqaga", callback_data=f"set-give_{chat_id}")
    builder.adjust(3, 2, 1, 1)
    return builder.as_markup()

def set_time_types_button(chat_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Tun", callback_data=f"set-time_{chat_id}_night")
    builder.button(text="Kun", callback_data=f"set-time_{chat_id}_day")
    builder.button(text="Ovoz berish", callback_data=f"set-time_{chat_id}_vote")
    builder.button(text="Like bosish", callback_data=f"set-time_{chat_id}_like")
    builder.button(text="So'ngi so'z", callback_data=f"set-time_{chat_id}_word")
    builder.button(text="Ro'yxatdan o'tish", callback_data=f"set-time_{chat_id}_reg")
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def set_time_values_button(chat_id, time_type, default=45):
    builder = InlineKeyboardBuilder()
    
    # Ro'yxatdan o'tish uchun maxsus vaqtlar (screenshotdagi kabi)
    if time_type in ["night", "day"]:
        times = [35, 45]
    elif time_type == "reg":
        times = [30, 45, 60, 75, 90, 120, 180, 240, 300, 360]
    else:
        times = [30, 45, 60, 75, 90, 120, 180, 240, 300, 360]
    
    for t in times:
        builder.button(text=f"{t} Sekund {'◾️' if default == t else '▫️'}", callback_data=f"set-time_{chat_id}_{time_type}_{t}")
        
    builder.button(text="🔙 Orqaga", callback_data=f"set-time_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()

def set_roles_types_button(chat_id, page=0):
    builder = InlineKeyboardBuilder()
    # RoleNames dan barcha rollarni olish, lekin asosiy rollarni chiqarib tashlash
    excluded_roles = [RoleNames.DON, RoleNames.MAFIA, RoleNames.KOMISSAR, RoleNames.FUQARO, RoleNames.BORI, RoleNames.ZOMBI, RoleNames.DOKTOR]
    available_roles = [role for role in RoleNames.all() if role not in excluded_roles]
    
    # Sahifalash
    roles_per_page = 15
    total_pages = (len(available_roles) + roles_per_page - 1) // roles_per_page
    start_index = page * roles_per_page
    end_index = start_index + roles_per_page
    current_page_roles = available_roles[start_index:end_index]
    
    for role in current_page_roles:
        # To'liq rol nomini ko'rsatish (emoji bilan birga)
        builder.button(text=role, callback_data=f"set-roles_{chat_id}_{role}")
    
    # Sahifalash tugmalari
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"set-roles_{chat_id}_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"set-roles_{chat_id}_page_{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Sahifa ma'lumoti va orqaga tugmasi
    if total_pages > 1:
        builder.row(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="ignore"))
    
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def set_roles_values_button(chat_id, role, default=True):
    builder = InlineKeyboardBuilder()
    # default=True bu taqiqlangan degan ma'no, False esa ruxsat berilgan
    builder.button(text=f"Taqiqlash {'◾️' if default == True else '▫️'}", callback_data=f"set-roles_{chat_id}_{role}_0")
    builder.button(text=f"Ruxsat berish {'◾️' if default == False else '▫️'}", callback_data=f"set-roles_{chat_id}_{role}_1")
    builder.button(text="🔙 Orqaga", callback_data=f"set-roles_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()

def set_leave_button(chat_id, default=True):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Ha {'◾️' if default == True else '▫️'}", callback_data=f"set-leave_{chat_id}_1")
    builder.button(text=f"Yo'q {'◾️' if default == False else '▫️'}", callback_data=f"set-leave_{chat_id}_0")
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(2)
    return builder.as_markup()


def set_write_group_perm_types_button(chat_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Tun", callback_data=f"set-wgroupperm_{chat_id}_night")
    builder.button(text="Kun", callback_data=f"set-wgroupperm_{chat_id}_day")
    builder.button(text="🔙 Orqaga", callback_data=f"show-settings_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()

def set_write_group_perm_values_button(chat_id, perm_type, default="ega"):
    builder = InlineKeyboardBuilder()
    options = [
        ("ega", "Faqat Ega"),
        ("admin", "Faqat Adminlar"),
        ("alive", "Faqat tirik ishtirokchilar"),
        ("member", "Faqat ishtirokchilar"),
        ("all", "Hamma"),
    ]
    for value, label in options:
        selected = "◾️" if default == value else "▫️"
        builder.button(
            text=f"{label} {selected}",
            callback_data=f"set-wgroupperm_{chat_id}_{perm_type}_{value}"
        )
    builder.button(text="🔙 Orqaga", callback_data=f"set-wgroupperm_{chat_id}")
    builder.adjust(1)
    return builder.as_markup()