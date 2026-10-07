from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from config import BOT_URL, SUPPORT_ADMIN, CHANNEL_USERNAME, WEBAPP_URL
from utils.i18n import (
    clean_lang, BTN_CABINET, BTN_ADD_GROUP, BTN_PREM_GROUPS,
    BTN_SUPPORT, BTN_CHANNEL, GENDER_MALE, GENDER_FEMALE
)

bot_link_markup = InlineKeyboardBuilder()
bot_link_markup.button(text="Botga o'tish", url=BOT_URL)
bot_link_markup = bot_link_markup.as_markup()


def get_start_markup(lang: str = "uz"):
    """Asosiy menyu tugmalari (tanlangan tilga moslashtirilgan)."""
    code = clean_lang(lang)
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_CABINET.get(code, BTN_CABINET["uz"]), web_app=WebAppInfo(url=WEBAPP_URL))
    builder.button(text=BTN_ADD_GROUP.get(code, BTN_ADD_GROUP["uz"]), url=BOT_URL + "?startgroup=true")
    builder.button(text=BTN_PREM_GROUPS.get(code, BTN_PREM_GROUPS["uz"]), callback_data="prem_groups_start")
    builder.button(text=BTN_SUPPORT.get(code, BTN_SUPPORT["uz"]), url=SUPPORT_ADMIN)
    builder.button(text=BTN_CHANNEL.get(code, BTN_CHANNEL["uz"]), url="https://t.me/" + CHANNEL_USERNAME[1:])
    builder.adjust(1, 1, 1, 2)
    return builder.as_markup()


start_markup = get_start_markup()


def gender_keyboard(lang: str = "uz"):
    code = clean_lang(lang)
    m = InlineKeyboardBuilder()
    m.button(text=GENDER_MALE.get(code, GENDER_MALE["uz"]), callback_data="gender_select_m")
    m.button(text=GENDER_FEMALE.get(code, GENDER_FEMALE["uz"]), callback_data="gender_select_f")
    m.adjust(2)
    return m.as_markup()

def get_onboard_lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="onboard_lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="onboard_lang_ru")
    builder.button(text="🇬🇧 English", callback_data="onboard_lang_en")
    builder.button(text="🇹🇷 Türkçe", callback_data="onboard_lang_tr")
    builder.adjust(2, 2)
    return builder.as_markup()

