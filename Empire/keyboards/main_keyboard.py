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
    b.button(text="✅ Guruhga qo'shish", url=f"{b_url}?startgroup=true")
    b.button(text="🌟 Premium guruhlar", callback_data="prem_groups_start")
    b.button(text="✍🏻 Savollar uchun", url=s_admin)
    b.button(text="📡 Kanal", url=c_url)
    b.adjust(1, 1, 1, 2)
    return b.as_markup()


def gender_keyboard():
    m = InlineKeyboardBuilder()
    m.button(text="👦 Yigit / Erkak", callback_data="gender_select_m")
    m.button(text="👧 Qiz / Ayol", callback_data="gender_select_f")
    m.adjust(2)
    return m.as_markup()