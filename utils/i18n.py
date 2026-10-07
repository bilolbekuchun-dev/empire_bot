"""
Multi-language (i18n) Support Module for Empire Mafia Bot.
Supports 4 languages: uz (O'zbekcha), ru (Русский), en (English), tr (Türkçe).
"""
from typing import Optional

LANGUAGES = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "tr": "🇹🇷 Türkçe"
}

DEFAULT_LANG = "uz"

def clean_lang(lang: Optional[str]) -> str:
    code = (lang or "").lower().strip()
    return code if code in LANGUAGES else DEFAULT_LANG

# --------------------------------------------------------------------------
# Start & Onboarding Texts
# --------------------------------------------------------------------------
START_TEXTS = {
    "uz": (
        "<b>Salom</b>\n"
        "Men mafiya botiman. Doʻstlar bilan mafiya oʻynash uchun meni guruhingizga qoʻshing va "
        "45 kishilik oʻyindan zavqlaning batafsil maʼlumot uchun {shop_user}\n\n"
        " Meni admin qilib qoʻyganingizdan soʻng, oʻyinni boshlashingiz mumkin.."
    ),
    "ru": (
        "<b>Привет</b>\n"
        "Я бот Мафия. Добавьте меня в вашу группу, чтобы играть в Мафию с друзьями до 45 человек! "
        "Подробная информация: {shop_user}\n\n"
        "После того как сделаете меня администратором, вы можете начать игру.."
    ),
    "en": (
        "<b>Hello</b>\n"
        "I am Mafia Bot. Add me to your group to play Mafia with up to 45 friends! "
        "For details check {shop_user}\n\n"
        "Once you grant me admin rights, you can start the game.."
    ),
    "tr": (
        "<b>Merhaba</b>\n"
        "Ben Mafya Botuyum. Arkadaşlarınızla 45 kişiye kadar Mafya oynamak için beni grubunuza ekleyin! "
        "Detaylar için: {shop_user}\n\n"
        "Beni yönetici yaptıktan sonra oyunu başlatabilirsiniz.."
    )
}

GENDER_PROMPT = {
    "uz": "Davom etishdan oldin jinsingizni tanlang:",
    "ru": "Выберите ваш пол перед продолжением:",
    "en": "Please select your gender before continuing:",
    "tr": "Devam etmeden önce cinsiyetinizi seçin:"
}

GENDER_MALE = {
    "uz": "👦 Yigit / Erkak",
    "ru": "👦 Парень / Мужчина",
    "en": "👦 Male / Man",
    "tr": "👦 Erkek"
}

GENDER_FEMALE = {
    "uz": "👧 Qiz / Ayol",
    "ru": "👧 Девушка / Женщина",
    "en": "👧 Female / Woman",
    "tr": "👧 Kadın"
}

# --------------------------------------------------------------------------
# Start Keyboard Buttons
# --------------------------------------------------------------------------
BTN_CABINET = {
    "uz": "🌐 Shaxsiy kabinet",
    "ru": "🌐 Личный кабинет",
    "en": "🌐 Profile Cabinet",
    "tr": "🌐 Kişisel Kabine"
}
BTN_ADD_GROUP = {
    "uz": "✅ Guruhga qo'shish",
    "ru": "✅ Добавить в группу",
    "en": "✅ Add to group",
    "tr": "✅ Gruba ekle"
}
BTN_PREM_GROUPS = {
    "uz": "🌟 Premium guruhlar",
    "ru": "🌟 Премиум группы",
    "en": "🌟 Premium groups",
    "tr": "🌟 Premium gruplar"
}
BTN_SUPPORT = {
    "uz": "✍🏻 Savollar uchun",
    "ru": "✍🏻 Вопросы/Поддержка",
    "en": "✍🏻 Support",
    "tr": "✍🏻 Destek için"
}
BTN_CHANNEL = {
    "uz": "📡 Kanal",
    "ru": "📡 Канал",
    "en": "📡 Channel",
    "tr": "📡 Kanal"
}

# --------------------------------------------------------------------------
# Profile Labels & UI Buttons
# --------------------------------------------------------------------------
PROFILE_LABELS = {
    "uz": {
        "user": "Foydalanuvchi",
        "dollar": "Dollar",
        "diamond": "Olmos",
        "himoya": "Himoya",
        "hujjat": "Hujjat",
        "osishdan_himoya": "Osishdan himoya qilish",
        "qotildan_himoya": "Qotildan himoya",
        "miltiq": "Miltiq",
        "doridan_himoya": "Doridan himoya",
        "maska": "Maska",
        "slip_himoya": "Sirpanishdan himoya",
        "geroy_himoya": "Geroydan himoya",
        "wins": "G'alaba",
        "games": "Barcha o'yinlar",
        "partner": "Sizning parangiz",
        "active_roles": "Faol rollar",
        "none": "Yo'q",
        "btn_protections": "🛡 Himoyalar",
        "btn_shop": "Do'kon",
        "btn_para": "Mening param",
        "btn_buy_diamond": "💎 Xarid qilish",
        "btn_buy_dollar": "💵 Xarid qilish",
        "btn_buy": "Xarid qilish",
        "btn_hero": "🥷 Mening geroyim",
        "btn_prem_groups": "🎲 Premium guruhlar",
        "btn_news": "Yangiliklar",
        "btn_back": "⬅️ Orqaga"
    },
    "ru": {
        "user": "Пользователь",
        "dollar": "Доллар",
        "diamond": "Алмаз",
        "himoya": "Защита",
        "hujjat": "Документ",
        "osishdan_himoya": "Защита от повешения",
        "qotildan_himoya": "Защита от киллера",
        "miltiq": "Винтовка",
        "doridan_himoya": "Защита от лекарства",
        "maska": "Маска",
        "slip_himoya": "Защита от скольжения",
        "geroy_himoya": "Защита от героя",
        "wins": "Победы",
        "games": "Всего игр",
        "partner": "Ваша пара",
        "active_roles": "Активные роли",
        "none": "Нет",
        "btn_protections": "🛡 Защиты",
        "btn_shop": "Магазин",
        "btn_para": "Моя пара",
        "btn_buy_diamond": "💎 Купить",
        "btn_buy_dollar": "💵 Купить",
        "btn_buy": "Купить",
        "btn_hero": "🥷 Мой герой",
        "btn_prem_groups": "🎲 Премиум группы",
        "btn_news": "Новости",
        "btn_back": "⬅️ Назад"
    },
    "en": {
        "user": "User",
        "dollar": "Dollar",
        "diamond": "Diamond",
        "himoya": "Protection",
        "hujjat": "Document",
        "osishdan_himoya": "Hang Protection",
        "qotildan_himoya": "Killer Protection",
        "miltiq": "Rifle",
        "doridan_himoya": "Medicine Protection",
        "maska": "Mask",
        "slip_himoya": "Slip Protection",
        "geroy_himoya": "Hero Protection",
        "wins": "Wins",
        "games": "Total games",
        "partner": "Your partner",
        "active_roles": "Active roles",
        "none": "None",
        "btn_protections": "🛡 Protections",
        "btn_shop": "Shop",
        "btn_para": "My partner",
        "btn_buy_diamond": "💎 Buy",
        "btn_buy_dollar": "💵 Buy",
        "btn_buy": "Buy",
        "btn_hero": "🥷 My hero",
        "btn_prem_groups": "🎲 Premium groups",
        "btn_news": "News",
        "btn_back": "⬅️ Back"
    },
    "tr": {
        "user": "Kullanıcı",
        "dollar": "Dolar",
        "diamond": "Elmas",
        "himoya": "Koruma",
        "hujjat": "Belge",
        "osishdan_himoya": "Asılma koruması",
        "qotildan_himoya": "Katil koruması",
        "miltiq": "Tüfek",
        "doridan_himoya": "İlaç koruması",
        "maska": "Maske",
        "slip_himoya": "Kayma koruması",
        "geroy_himoya": "Kahraman koruması",
        "wins": "Galibiyet",
        "games": "Toplam oyun",
        "partner": "Eşiniz",
        "active_roles": "Aktif roller",
        "none": "Yok",
        "btn_protections": "🛡 Korumalar",
        "btn_shop": "Mağaza",
        "btn_para": "Benim eşim",
        "btn_buy_diamond": "💎 Satın al",
        "btn_buy_dollar": "💵 Satın al",
        "btn_buy": "Satın al",
        "btn_hero": "🥷 Benim kahramanım",
        "btn_prem_groups": "🎲 Premium gruplar",
        "btn_news": "Haberler",
        "btn_back": "⬅️ Geri"
    }
}

# --------------------------------------------------------------------------
# Game Over Messages
# --------------------------------------------------------------------------
GAME_OVER_WINNER = {
    "uz": "🎉 <b>O'yin tugadi!</b>\n🏆 <b>Siz yutdingiz!</b> Yutganingiz uchun <b>{reward}{dollar_icon}</b> berildi!\n\n",
    "ru": "🎉 <b>Игра окончена!</b>\n🏆 <b>Вы выиграли!</b> Вам начислено <b>{reward}{dollar_icon}</b>!\n\n",
    "en": "🎉 <b>Game over!</b>\n🏆 <b>You won!</b> You received <b>{reward}{dollar_icon}</b>!\n\n",
    "tr": "🎉 <b>Oyun bitti!</b>\n🏆 <b>Kazandınız!</b> Ödül olarak <b>{reward}{dollar_icon}</b> kazandınız!\n\n"
}

GAME_OVER_LOSER = {
    "uz": "💀 <b>O'yin tugadi!</b>\n❌ <b>Siz mag'lub bo'ldingiz!</b> Mag'lubiyat uchun <b>{reward}{dollar_icon}</b> berildi!\n\n",
    "ru": "💀 <b>Игра окончена!</b>\n❌ <b>Вы проиграли!</b> За участие начислено <b>{reward}{dollar_icon}</b>!\n\n",
    "en": "💀 <b>Game over!</b>\n❌ <b>You lost!</b> For participating you received <b>{reward}{dollar_icon}</b>!\n\n",
    "tr": "💀 <b>Oyun bitti!</b>\n❌ <b>Kaybettiniz!</b> Katılımınız için <b>{reward}{dollar_icon}</b> aldınız!\n\n"
}

# --------------------------------------------------------------------------
# Mandatory Subscription
# --------------------------------------------------------------------------
SUB_REQUIRED_TEXT = {
    "uz": "Iltimos, quyidagi kanal(lar) ga obuna boling va pastdagi \"tekshirish\" tugmasini bosing",
    "ru": "Пожалуйста, подпишитесь на канал(ы) ниже и нажмите кнопку \"Проверить\"",
    "en": "Please subscribe to the channel(s) below and click the \"Check\" button",
    "tr": "Lütfen aşağıdaki kanala/kanallara abone olun ve \"Kontrol et\" butonuna basın"
}

SUB_CHECK_BTN = {
    "uz": "✅ Tekshirish",
    "ru": "✅ Проверить",
    "en": "✅ Check",
    "tr": "✅ Kontrol et"
}

# --------------------------------------------------------------------------
# Language Switch Prompt
# --------------------------------------------------------------------------
LANG_SELECT_PROMPT = {
    "uz": "🌐 <b>Bot tilini tanlang / Choose language:</b>",
    "ru": "🌐 <b>Выберите язык бота / Choose language:</b>",
    "en": "🌐 <b>Choose bot language / Select language:</b>",
    "tr": "🌐 <b>Bot dilini seçin / Choose language:</b>"
}

LANG_CONFIRM = {
    "uz": "✅ Bot tili O'zbek tiliga o'zgartirildi!",
    "ru": "✅ Язык бота изменен на Русский!",
    "en": "✅ Bot language changed to English!",
    "tr": "✅ Bot dili Türkçe olarak değiştirildi!"
}

# --------------------------------------------------------------------------
# Group Game Announcements & Messages (Multi-language)
# --------------------------------------------------------------------------
GAME_TEXTS = {
    "title_alive": {
        "uz": "<b>Tirik o'yinchilar:</b>",
        "ru": "<b>Живые игроки:</b>",
        "en": "<b>Alive players:</b>",
        "tr": "<b>Hayatta olan oyuncular:</b>"
    },
    "title_dead_none": {
        "uz": "<b>Tirik o'yinchi qolmadi!</b>\n",
        "ru": "<b>Живых игроков не осталось!</b>\n",
        "en": "<b>No alive players left!</b>\n",
        "tr": "<b>Hayatta kalan oyuncu kalmadı!</b>\n"
    },
    "time_night_left": {
        "uz": "Tonggacha ⏳ {time} sekund qoldi",
        "ru": "До утра осталось ⏳ {time} сек.",
        "en": "⏳ {time} seconds left until morning",
        "tr": "Sabaha ⏳ {time} saniye kaldı"
    },
    "time_day_left": {
        "uz": "Kun tugashiga ⏳ {time} sekund qoldi",
        "ru": "До конца дня осталось ⏳ {time} сек.",
        "en": "⏳ {time} seconds left until end of day",
        "tr": "Günün bitmesine ⏳ {time} saniye kaldı"
    },
    "time_vote_left": {
        "uz": "Ovoz berish tugashiga ⏳ {time} sekund qoldi",
        "ru": "До конца голосования осталось ⏳ {time} сек.",
        "en": "⏳ {time} seconds left until end of voting",
        "tr": "Oylamanın bitmesine ⏳ {time} saniye kaldı"
    },
    "night_start": {
        "uz": "🌃 <b>Tun tushdi. Qorong'u tushib, shahar ahl uxlashga ketdi...</b>",
        "ru": "🌃 <b>Наступила ночь. Город заснул...</b>",
        "en": "🌃 <b>Night has fallen. The city has fallen asleep...</b>",
        "tr": "🌃 <b>Gece oldu. Şehir uykuya daldı...</b>"
    },
    "day_start": {
        "uz": "☀️ <b>Kun boshlandi!</b>",
        "ru": "☀️ <b>Наступил день!</b>",
        "en": "☀️ <b>Day has started!</b>",
        "tr": "☀️ <b>Gündüz başladı!</b>"
    },
    "vote_start": {
        "uz": "<b>Kimga ovoz berasiz?</b>",
        "ru": "<b>За кого вы голосуете?</b>",
        "en": "<b>Who do you vote for?</b>",
        "tr": "<b>Kime oy veriyorsunuz?</b>"
    },
    "vote_result_hung": {
        "uz": "🪢 Sud qaroriga ko'ra {mention} osildi! Rol: <b>{role}</b>",
        "ru": "🪢 По решению суда {mention} был(а) повешен(а)! Роль: <b>{role}</b>",
        "en": "🪢 By court decision, {mention} was hanged! Role: <b>{role}</b>",
        "tr": "🪢 Mahkeme kararıyla {mention} asıldı! Rol: <b>{role}</b>"
    },
    "vote_result_tie": {
        "uz": "🤝 Ovozlar teng kelib qoldi! Bugun hech kim osilmadi.",
        "ru": "🤝 Голоса равны! Сегодня никто не повешен.",
        "en": "🤝 Votes are tied! Nobody was hanged today.",
        "tr": "🤝 Oylar eşit çıktı! Bugün kimse asılmadı."
    },
    "night_death": {
        "uz": "💀 Tunda {mention} halok bo'ldi. Rol: <b>{role}</b>",
        "ru": "💀 Ночью погиб(ла) {mention}. Роль: <b>{role}</b>",
        "en": "💀 {mention} died during the night. Role: <b>{role}</b>",
        "tr": "💀 Gece {mention} hayatını kaybetti. Rol: <b>{role}</b>"
    },
    "night_no_deaths": {
        "uz": "🎉 Tunda hech kim halok bo'lmadi! Har kim omon qoldi.",
        "ru": "🎉 Ночью никто не погиб! Все остались живы.",
        "en": "🎉 Nobody died during the night! Everyone survived.",
        "tr": "🎉 Gece kimse ölmedi! Herkes hayatta kaldı."
    },
    "kom_shoot_announcement": {
        "uz": "🔫 Komissar katani pistoletini o'qladi...",
        "ru": "🔫 Комиссар взвел курок своего пистолета...",
        "en": "🔫 The Detective loaded his gun...",
        "tr": "🔫 Komiser tabancasını doldurdu..."
    },
    "kom_check_announcement": {
        "uz": "🔍 Komissar shubheli odamni tekshirdi...",
        "ru": "🔍 Комиссар проверил подозрительного человека...",
        "en": "🔍 The Detective investigated a suspect...",
        "tr": "🔍 Komiser şüpheli bir kişiyi inceledi..."
    }
}

def get_game_text(key: str, lang: str = "uz", **kwargs) -> str:
    code = clean_lang(lang)
    item = GAME_TEXTS.get(key, {})
    text = item.get(code, item.get("uz", ""))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

async def get_chat_lang(chat_id: int) -> str:
    try:
        from models.game_data import Chat
        chat = await Chat.filter(chat_id=chat_id).first()
        if chat and getattr(chat, "lang", None):
            return clean_lang(chat.lang)
    except Exception:
        pass
    return "uz"
