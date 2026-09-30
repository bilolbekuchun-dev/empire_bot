from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from config import BOT_URL, SUPPORT_ADMIN, CHANNEL_USERNAME, WEBAPP_URL


bot_link_markup = InlineKeyboardBuilder()
bot_link_markup.button(text="Botga o'tish", url=BOT_URL)
bot_link_markup = bot_link_markup.as_markup()

start_markup = InlineKeyboardBuilder()
start_markup.button(text="🌐 Shaxsiy kabinet", web_app=WebAppInfo(url=WEBAPP_URL))
start_markup.button(text="✅ Guruhga qo'shish", url=BOT_URL + "?startgroup=true")
start_markup.button(text="🌟 Premium guruhlar", callback_data="prem_groups_start")
start_markup.button(text="✍🏻 Savollar uchun", url=SUPPORT_ADMIN)
start_markup.button(text="📡 Kanal", url="https://T.me/" + CHANNEL_USERNAME[1:])
start_markup.adjust(1,1,1,2)
start_markup = start_markup.as_markup()

def get_start_markup():
    return start_markup


def gender_keyboard():
    m = InlineKeyboardBuilder()
    m.button(text="👦 Yigit / Erkak", callback_data="gender_select_m")
    m.button(text="👧 Qiz / Ayol", callback_data="gender_select_f")
    m.adjust(2)
    return m.as_markup()