from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from config import BOT_URL, SUPPORT_ADMIN, CHANNEL_USERNAME, WEBAPP_URL


def get_bot_link_markup(lang: str = "uz"):
    b_url = BOT_URL if (BOT_URL and BOT_URL.startswith("http")) else "https://t.me/test_empire_bot"
    from utils.i18n import clean_lang
    c = clean_lang(lang)
    texts = {
        "uz": "Botga o'tish",
        "ru": "Перейти в бота",
        "en": "Go to bot",
        "tr": "Bota git",
        "kk": "Ботқа өту"
    }
    b = InlineKeyboardBuilder()
    b.button(text=texts.get(c, texts["uz"]), url=b_url)
    return b.as_markup()

bot_link_markup = get_bot_link_markup("uz")

def get_start_markup(lang: str = "uz"):
    from config import BOT_URL, SUPPORT_ADMIN, CHANNEL_USERNAME, WEBAPP_URL
    from utils.i18n import clean_lang
    c = clean_lang(lang)

    b_url = BOT_URL if (BOT_URL and BOT_URL.startswith("http")) else "https://t.me/test_empire_bot"
    w_url = WEBAPP_URL if (WEBAPP_URL and WEBAPP_URL.startswith("http")) else "https://empiremafiaweb.netlify.app"
    s_admin = SUPPORT_ADMIN if (SUPPORT_ADMIN and SUPPORT_ADMIN.startswith("http")) else "https://t.me/Yuldashev_01s"
    c_user = CHANNEL_USERNAME.lstrip("@") if CHANNEL_USERNAME else "Empire_yangiliklar"
    c_url = f"https://t.me/{c_user}"
    
    texts_cabinet = {
        "uz": "🌐 Shaxsiy kabinet",
        "ru": "🌐 Личный кабинет",
        "en": "🌐 Profile Cabinet",
        "tr": "🌐 Kişisel Kabine",
        "kk": "🌐 Жеке кабинет"
    }
    texts_airdrop = {
        "uz": "🪂 Airdrop & Rol Spin",
        "ru": "🪂 Airdrop & Вращение ролей",
        "en": "🪂 Airdrop & Role Spin",
        "tr": "🪂 Airdrop & Rol Çarkı",
        "kk": "🪂 Airdrop & Рөл айналдыру"
    }
    texts_add_group = {
        "uz": "✅ Guruhga qo'shish",
        "ru": "✅ Добавить в группу",
        "en": "✅ Add to group",
        "tr": "✅ Gruba ekle",
        "kk": "✅ Топқа қосу"
    }
    texts_prem_groups = {
        "uz": "🌟 Premium guruhlar",
        "ru": "🌟 Премиум группы",
        "en": "🌟 Premium groups",
        "tr": "🌟 Premium gruplar",
        "kk": "🌟 Премиум топтар"
    }
    texts_support = {
        "uz": "✍🏻 Savollar uchun",
        "ru": "✍🏻 Вопросы/Поддержка",
        "en": "✍🏻 Support",
        "tr": "✍🏻 Destek için",
        "kk": "✍🏻 Қолдау"
    }
    texts_channel = {
        "uz": "📡 Kanal",
        "ru": "📡 Канал",
        "en": "📡 Channel",
        "tr": "📡 Kanal",
        "kk": "📡 Канал"
    }

    import config
    b = InlineKeyboardBuilder()
    if getattr(config, "IS_WEBAPP_ACTIVE", False):
        b.button(text=texts_cabinet.get(c, texts_cabinet["uz"]), web_app=WebAppInfo(url=w_url))
    else:
        b.button(text=texts_cabinet.get(c, texts_cabinet["uz"]), callback_data="my_profile")
    b.button(text=texts_airdrop.get(c, texts_airdrop["uz"]), callback_data="refresh_airdrop_menu")
    b.button(text=texts_add_group.get(c, texts_add_group["uz"]), url=f"{b_url}?startgroup=true")
    b.button(text=texts_prem_groups.get(c, texts_prem_groups["uz"]), callback_data="prem_groups_start")
    b.button(text=texts_support.get(c, texts_support["uz"]), url=s_admin)
    b.button(text=texts_channel.get(c, texts_channel["uz"]), url=c_url)
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