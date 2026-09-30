from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import CHANNEL_USERNAME
from models.user import Profile
from utils.premium_emojis import get_custom_emoji_id, get_diamond_display, get_dollar_display

def protection_toggle_keyboard(profile: Profile):
    markup = InlineKeyboardBuilder()
    if profile.on_himoya:
        markup.button(text=f"🛡 - 🟢 ON", callback_data="off_himoya")
    else:
        markup.button(text=f"🛡 - 🔴 OFF", callback_data="on_himoya")
    if profile.on_hujjat:
        markup.button(text=f"📁 - 🟢 ON", callback_data="off_hujjat")
    else:
        markup.button(text=f"📁 - 🔴 OFF", callback_data="on_hujjat")
    if profile.on_osishdan_himoya:
        markup.button(text=f"⚖️ - 🟢 ON", callback_data="off_osish-himoya")
    else:
        markup.button(text=f"⚖️ - 🔴 OFF", callback_data="on_osish-himoya")
    if profile.on_doridan_himoya:
        markup.button(text=f"💊 - 🟢 ON", callback_data="off_dori-himoya")
    else:
        markup.button(text=f"💊 - 🔴 OFF", callback_data="on_dori-himoya")
    if profile.on_maska:
        markup.button(text=f"🎭 - 🟢 ON", callback_data="off_maska")
    else:
        markup.button(text=f"🎭 - 🔴 OFF", callback_data="on_maska")
    if profile.on_qotildan_himoya:
        markup.button(text=f"⛑️ - 🟢 ON", callback_data="off_qotildan-himoya")
    else:
        markup.button(text=f"⛑️ - 🔴 OFF", callback_data="on_qotildan-himoya")
    if profile.on_slip_himoya:
        markup.button(text=f"🪤 - 🟢 ON", callback_data="off_slip-himoya")
    else:
        markup.button(text=f"🪤 - 🔴 OFF", callback_data="on_slip-himoya")
    if profile.on_geroy_himoya:
        markup.button(text=f"🔰 - 🟢 ON", callback_data="off_geroy-himoya")
    else:
        markup.button(text=f"🔰 - 🔴 OFF", callback_data="on_geroy-himoya")
    markup.button(text="⬅️ Orqaga", callback_data="back_profile")
    markup.adjust(2)
    return markup.as_markup()

def profile_keyboards_on_private(profile: Profile):
    markup = InlineKeyboardBuilder()
    dia_id = get_custom_emoji_id("currency", "diamond")
    dollar_id = get_custom_emoji_id("currency", "dollar")
    
    markup.button(text="🛡 Himoyalar", callback_data="open_protections")
    markup.button(text="Do'kon", callback_data="shop", icon_custom_emoji_id="5373052667671093676")
    markup.button(text="Mening param", callback_data="my_para_menu", icon_custom_emoji_id="5402100905883488232")
    if dia_id:
        markup.button(text="Xarid qilish", callback_data="get_diamond_hamyonlar", icon_custom_emoji_id=dia_id)
    else:
        markup.button(text="💎 Xarid qilish", callback_data="get_diamond_hamyonlar")
    if dollar_id:
        markup.button(text="Xarid qilish", callback_data="get_dollar", icon_custom_emoji_id=dollar_id)
    else:
        markup.button(text="💵 Xarid qilish", callback_data="get_dollar")
    markup.button(text="🥷 Mening geroyim", callback_data="my_geroy")
    markup.button(text="🎲 Premium guruhlar", callback_data="prem_groups")
    markup.button(text="Yangiliklar", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    markup.adjust(1, 2, 2, 2, 1, 2)
    return markup.as_markup()

def blocking_users(user1_id, user2_id):
    m = InlineKeyboardBuilder()
    m.button(text="Ikkalasini ham bloklash", callback_data=f"block_{user1_id}_{user2_id}")
    return m.as_markup()

def profile_keyboards():
    markup = InlineKeyboardBuilder()
    dia_id = get_custom_emoji_id("currency", "diamond")
    dollar_id = get_custom_emoji_id("currency", "dollar")
    
    markup.button(text="Do'kon", callback_data="shop", icon_custom_emoji_id="5373052667671093676")
    markup.button(text="Mening param", callback_data="my_para_menu", icon_custom_emoji_id="5402100905883488232")
    if dollar_id:
        markup.button(text="Xarid qilish", callback_data="get_dollar", icon_custom_emoji_id=dollar_id)
    else:
        markup.button(text="💵 Xarid qilish", callback_data="get_dollar")
    if dia_id:
        markup.button(text="Xarid qilish", callback_data="get_diamond_hamyonlar", icon_custom_emoji_id=dia_id)
    else:
        markup.button(text="💎 Xarid qilish", callback_data="get_diamond_hamyonlar")
    markup.button(text="🎲 Premium guruhlar", callback_data="prem_groups")
    markup.button(text="Yangiliklar", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    
    markup.adjust(2, 2, 2)
    return markup.as_markup()

def shop_keyboard(himoya_price, hujjat_price, osish_himoya_price, dori_himoya_price, maska_price, qotildan_himoya_price, militiq_price, geroy_price, slip_himoya_price, send_profile_price, geroydan_himoya_price):
    builder = InlineKeyboardBuilder()

    builder.button(text=f"🛡 Himoya - {himoya_price}💵", callback_data="buy_himoya")
    builder.button(text=f"📁 Hujjat - {hujjat_price}💵", callback_data="buy_hujjat")
    builder.button(text=f"⚖️ Ovozdan himoya - {osish_himoya_price}💎", callback_data="buy_osish_himoya")
    builder.button(text=f"🔫 Miltiq - {militiq_price}💎", callback_data="buy_miltiq")
    builder.button(text=f"💊 Doridan himoya - {dori_himoya_price}💵", callback_data="buy_dori_himoya")
    builder.button(text=f"🎭 Maska - {maska_price}💵", callback_data="buy_maska")
    builder.button(text=f"⛑️ Qotildan himoya {qotildan_himoya_price}💎", callback_data="buy_qotildan_himoya")
    builder.button(text=f"🪤 Sirpanishdan himoya {slip_himoya_price}💎", callback_data="buy_slip_himoya")
    builder.button(text=f"🔰 Geroydan himoya {geroydan_himoya_price}💎", callback_data="buy_geroydan_himoya")
    builder.button(text=f"🔄 Profil almashish {send_profile_price}💎", callback_data="replace_profile")
    builder.button(text=f"🥷 Geroy {geroy_price}💎", callback_data="buy_geroy")
    builder.button(text="🗃 Sandiqlar", callback_data="open-sandiq")
    builder.button(text=f"🃏 Faol rol", callback_data="active_role")
    builder.button(text="🎨 VIP emoji o'zgartirish", callback_data="vip_emoji_change")
    builder.button(text="⬅️ Orqaga", callback_data="back_profile")
    builder.adjust(2)

    return builder.as_markup()

def active_role_keyboard(role_price: dict):
    builder = InlineKeyboardBuilder()

    for role, price in role_price.items():
        # Telegram xato bermasligi uchun premium kodni qirqib, faqat ismini (masalan, " Bo'ri") olyapmiz:
        clean_role = role.split(">")[-1].strip() if "<tg-emoji" in role else role

        if price < 10:
            builder.button(
                text=f"{role} - {price}💎",
                callback_data=f"role-buy_{clean_role}"
            )
        else:
            builder.button(
                text=f"{role} - {price}💵",
                callback_data=f"role-buy_{clean_role}"
            )
    builder.button(text="🗑 Faol rolni o'chirish - 100💵", callback_data="role-del")
    builder.button(text="⬅️ Orqaga", callback_data="back_shop")
    builder.adjust(2)
    return builder.as_markup()

sandiqlar_menu = InlineKeyboardBuilder()
sandiqlar_menu.button(text="💰 Super sandiq", callback_data="super_sandiq")
sandiqlar_menu.button(text="💎 Mega sandiq", callback_data="mega_sandiq")
sandiqlar_menu.button(text="⭐️ Vip user", callback_data="vip_user")
sandiqlar_menu.button(text="⬅️ Orqaga", callback_data="shop")
sandiqlar_menu.adjust(1)
sandiqlar_menu = sandiqlar_menu.as_markup()

super_sandiq_menu = InlineKeyboardBuilder()
super_sandiq_menu.button(text="1", callback_data="super_sandiq-1")
super_sandiq_menu.button(text="2", callback_data="super_sandiq-2")
super_sandiq_menu.button(text="3", callback_data="super_sandiq-3")
super_sandiq_menu.button(text="4", callback_data="super_sandiq-4")
super_sandiq_menu.button(text="5", callback_data="super_sandiq-5")
super_sandiq_menu.button(text="6", callback_data="super_sandiq-6")
super_sandiq_menu.button(text="7", callback_data="super_sandiq-7")
super_sandiq_menu.button(text="8", callback_data="super_sandiq-8")
super_sandiq_menu.button(text="9", callback_data="super_sandiq-9")
super_sandiq_menu.button(text="⬅️ Orqaga", callback_data="back_profile")
super_sandiq_menu.adjust(3)
super_sandiq_menu = super_sandiq_menu.as_markup()

mega_sandiq_menu = InlineKeyboardBuilder()
mega_sandiq_menu.button(text="1", callback_data="mega_sandiq-1")
mega_sandiq_menu.button(text="2", callback_data="mega_sandiq-2")
mega_sandiq_menu.button(text="3", callback_data="mega_sandiq-3")
mega_sandiq_menu.button(text="4", callback_data="mega_sandiq-4")
mega_sandiq_menu.button(text="5", callback_data="mega_sandiq-5")
mega_sandiq_menu.button(text="6", callback_data="mega_sandiq-6")
mega_sandiq_menu.button(text="7", callback_data="mega_sandiq-7")
mega_sandiq_menu.button(text="8", callback_data="mega_sandiq-8")
mega_sandiq_menu.button(text="9", callback_data="mega_sandiq-9")
mega_sandiq_menu.button(text="⬅️ Orqaga", callback_data="back_profile")
mega_sandiq_menu.adjust(3)
mega_sandiq_menu = mega_sandiq_menu.as_markup()

geroy_menu = InlineKeyboardBuilder()
geroy_menu.button(text="➕ 1000 Ball", callback_data="geroy_update-ball")
geroy_menu.button(text="🛡 Himoyani yangilash", callback_data="geroy_update-shield")
geroy_menu.button(text="🩸 Qurolni o'qlash", callback_data="geroy_update-gun")
geroy_menu.button(text="🖋 Geroy nomini o'zgertirish", callback_data="geroy_update-name")
geroy_menu.button(text="⭐️ Darajalar haqida", callback_data="geroy_levels-list")
geroy_menu.button(text="🛒 Geroy Marketga qo'shish", callback_data="add_my_geroy_market")
geroy_menu.button(text="⬅️ Orqaga", callback_data="back_profile")
geroy_menu.adjust(1)
geroy_menu = geroy_menu.as_markup()

back_geroy_menu = InlineKeyboardBuilder()
back_geroy_menu.button(text="⬅️ Orqaga", callback_data="my_geroy")
back_geroy_menu = back_geroy_menu.as_markup()

back_profile_menu = InlineKeyboardBuilder()
back_profile_menu.button(text="⬅️ Orqaga", callback_data="back_profile")
back_profile_menu = back_profile_menu.as_markup()

def approve_transfer_profile_btn(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Qabul qilish", callback_data=f"rp_approve_{user_id}")
    builder.button(text="Bekor qilish", callback_data=f"rp_cancel_{user_id}")
    builder.adjust(1)
    return builder.as_markup()
def para_gift_menu(gender_changes_left: int = 3):
    markup = InlineKeyboardBuilder()

    markup.button(text="Dollar yuborish", callback_data="para_send_dollar", icon_custom_emoji_id="5211062061932521090")
    markup.button(text="Olmos yuborish", callback_data="para_send_diamond", icon_custom_emoji_id="5210941235912552228")

    items = [
        ("Himoya", "himoya", "5334560212986632624"),
        ("Hujjat", "hujjat", "5357315181649076022"),
        ("Qotildan himoya", "qotildan_himoya", None),
        ("Osishdan himoya", "osishdan_himoya", "5283063413373684641"),
        ("Miltiq", "miltiq", "5471993127734632155"),
        ("Doridan himoya", "doridan_himoya", "5420163708674384414"),
        ("Maska", "maska", "5350658016700013471"),
        ("Sirpanishdan himoya", "slip_himoya", None),
        ("Geroydan himoya", "geroy_himoya", None)
    ]

    for text, key, emoji_id in items:
        if emoji_id:
            markup.button(text=f"{text} yuborish", callback_data=f"para_send_item_{key}", icon_custom_emoji_id=emoji_id)
        else:
            markup.button(text=f"{text} yuborish", callback_data=f"para_send_item_{key}")

    markup.button(text="💬 Anonim suhbat", callback_data="para_chat_start")
    rows = [2, 2, 2, 2, 2, 1]
    if gender_changes_left > 0:
        markup.button(text=f"🔄 Jinsni o'zgartirish ({gender_changes_left}/3)", callback_data="gender_menu_open")
        rows.append(1)
    markup.button(text="⬅️ Orqaga", callback_data="back_profile")
    rows.append(1)
    markup.adjust(*rows)
    return markup.as_markup()

def anon_chat_keyboard():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Suhbatni yopish")]],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True
    )

def para_no_para_keyboard(gender_changes_left: int = 3):
    markup = InlineKeyboardBuilder()
    markup.button(text="🎲 Random para topish", callback_data="find_random_para")
    if gender_changes_left > 0:
        markup.button(text=f"🔄 Jinsni o'zgartirish ({gender_changes_left}/3)", callback_data="gender_menu_open")
        markup.button(text="⬅️ Orqaga", callback_data="back_profile")
        markup.adjust(1, 1, 1)
    else:
        markup.button(text="⬅️ Orqaga", callback_data="back_profile")
        markup.adjust(1, 1)
    return markup.as_markup()
