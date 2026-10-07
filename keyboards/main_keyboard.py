from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from config import BOT_URL, SUPPORT_ADMIN, CHANNEL_USERNAME, WEBAPP_URL


bot_link_markup = InlineKeyboardBuilder()
bot_link_markup.button(text="Botga o'tish", url=BOT_URL)
bot_link_markup = bot_link_markup.as_markup()

def get_start_markup():
    from config import BOT_URL, SUPPORT_ADMIN, CHANNEL_USERNAME, WEBAPP_URL
    b_url = BOT_URL if (BOT_URL and BOT_URL.startswith("http")) else "https://t.me/test_empire_bot"
    w_url = WEBAPP_URL if (WEBAPP_URL and WEBAPP_URL.startswith("http")) else "https://empiremafiaweb.netlify.app"
    s_admin = SUPPORT_ADMIN if (SUPPORT_ADMIN and SUPPORT_ADMIN.startswith("http")) else "https://t.me/Yuldashev_01s"
    c_user = CHANNEL_USERNAME.lstrip("@") if CHANNEL_USERNAME else "Empire_yangiliklar"
    c_url = f"https://t.me/{c_user}"
    
    b = InlineKeyboardBuilder()
    b.button(text="🌐 Shaxsiy kabinet", web_app=WebAppInfo(url=w_url))
    b.button(text="🪂 Airdrop & Rol Spin", callback_data="refresh_airdrop_menu")
    b.button(text="✅ Guruhga qo'shish", url=f"{b_url}?startgroup=true")
    b.button(text="🌟 Premium guruhlar", callback_data="prem_groups_start")
    b.button(text="✍🏻 Savollar uchun", url=s_admin)
    b.button(text="📡 Kanal", url=c_url)
    b.adjust(1, 1, 1, 1, 2)
    return b.as_markup()

start_markup = get_start_markup()


def gender_keyboard(lang: str = "uz"):
    lang = (lang or "uz").lower()
    m = InlineKeyboardBuilder()
    if lang == "ru":
        m.button(text="👦 Мужчина", callback_data="gender_select_m")
        m.button(text="👧 Женщина", callback_data="gender_select_f")
    elif lang == "en":
        m.button(text="👦 Male", callback_data="gender_select_m")
        m.button(text="👧 Female", callback_data="gender_select_f")
    elif lang == "tr":
        m.button(text="👦 Erkek", callback_data="gender_select_m")
        m.button(text="👧 Kadın", callback_data="gender_select_f")
    elif lang == "kk":
        m.button(text="👦 Ер / Еркек", callback_data="gender_select_m")
        m.button(text="👧 Қыз / Әйел", callback_data="gender_select_f")
    else:
        m.button(text="👦 Yigit / Erkak", callback_data="gender_select_m")
        m.button(text="👧 Qiz / Ayol", callback_data="gender_select_f")
    m.adjust(2)
    return m.as_markup()

def get_onboard_lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="onboard_lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="onboard_lang_ru")
    builder.button(text="🇬🇧 English", callback_data="onboard_lang_en")
    builder.button(text="🇹🇷 Türkçe", callback_data="onboard_lang_tr")
    builder.button(text="🇰🇿 Qazaqsha", callback_data="onboard_lang_kk")
    builder.adjust(2, 2, 1)
    return builder.as_markup()