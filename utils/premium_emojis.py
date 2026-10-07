import os
import json
import random
from utils.role_names import RoleNames

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "custom_emojis.json")

import re as _re
# Bot yubora OLMAYDIGAN custom emoji id'lar (o'chirilgan/yopiq sticker to'plami).
# Bular xabarga tushsa Telegram butun xabarni "DOCUMENT_INVALID" bilan rad etadi,
# shuning uchun ular manbada (get_custom_emoji) va yuborishdan oldin oddiy emojiga tozalanadi.
# Ro'yxat getCustomEmojiStickers + haqiqiy sendMessage sinovi bilan aniqlangan (2026-09-22).
DEAD_EMOJI_IDS = frozenset({
    "5206204505460354188","5206222058991690229","5206260563373498644","5206273375260943817",
    "5206305454371678131","5206324889098692371","5206347888648559947","5206412167129115072",
    "5206422084208598163","5206434148771737332","5206458501236303658","5206503967760095680",
    "5206575178317866664","5206577098168247863","5206591061106927786","5206600875107197380",
    "5206617518105468919","5206653969492910423","5206657684639626350","5206658719726741982",
    "5208442393874966946","5208509610113151865","5208540104380950496","5208625471150928649",
    "5208762824205052741","5208771985370297416","5208783972624018761","5208864043699318415",
    "5208949878620725501","5210941235912552228","5210993217901733758","5211062061932521090",
})

_DEAD_TAG_RE = _re.compile(r"<tg-emoji\s+emoji-id=['\"]?(\d{15,})['\"]?\s*>(.*?)</tg-emoji>", _re.DOTALL)

def strip_dead_emojis(text):
    """Yuborilmaydigan (o'lik) custom emoji teglarini ichidagi oddiy emojiga almashtiradi.
    Ishlaydigan premium emojilar (DEAD_EMOJI_IDS da yo'q) tegilmasdan qoladi."""
    if not text or "<tg-emoji" not in str(text):
        return text
    def _repl(m):
        return m.group(2) if m.group(1) in DEAD_EMOJI_IDS else m.group(0)
    return _DEAD_TAG_RE.sub(_repl, str(text))

DEFAULT_CONFIG = {
    "roles": {},
    "weapons": {
        "miltiq": None,
        "himoya": None,
        "doridan_himoya": None,
        "mask": None,
        "hujjat": None,
        "osishdan_himoya": None,
        "jon": None
    },
    "currency": {
        "diamond": None,
        "dollar": None
    }
}

WEAPON_NAMES = {
    "miltiq": ("🔫", "Miltiq"),
    "himoya": ("🛡", "Himoya"),
    "doridan_himoya": ("💊", "Doridan himoya"),
    "mask": ("🎭", "Niqob"),
    "hujjat": ("📜", "Hujjat"),
    "osishdan_himoya": ("🔒", "Osishdan himoya"),
    "jon": ("❤️", "Jon (Life)")
}

CURRENCY_NAMES = {
    "diamond": ("💎", "Olmos"),
    "dollar": ("💵", "Dollar")
}

ACTIVE_ROLES_TINCH = [
    RoleNames.KOMISSAR, RoleNames.SERJANT, RoleNames.FUQARO,
    RoleNames.DOKTOR, RoleNames.HAMSHIRA, RoleNames.DAYDI,
    RoleNames.KEZUVCHI, RoleNames.OMADLI, RoleNames.JANOB,
    RoleNames.SOTQIN, RoleNames.XOYIN, RoleNames.QORIQCHI,
    RoleNames.ZANJIR
]

ACTIVE_ROLES_MAFIA = [
    RoleNames.DON, RoleNames.MAFIA, RoleNames.ADVOKAT,
    RoleNames.OVCHI, RoleNames.JURNALIST, RoleNames.AYGOQCHI
]

ACTIVE_ROLES_YAKKA = [
    RoleNames.QOTIL, RoleNames.BORI, RoleNames.AFERIST,
    RoleNames.GAZABDOR, RoleNames.SEHRGAR, RoleNames.SUIDSID,
    RoleNames.QASOSKOR, RoleNames.QAROQCHI, RoleNames.AKTYOR,
    RoleNames.JIN, RoleNames.KONCHI, RoleNames.TAQLIDCHI,
    RoleNames.REVERSER
]

ALL_ACTIVE_ROLES = ACTIVE_ROLES_TINCH + ACTIVE_ROLES_MAFIA + ACTIVE_ROLES_YAKKA

def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))

def _save_config(data: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving custom emojis config: {e}")

def reload_emojis():
    pass

def set_custom_emoji(category: str, key: str, emoji_html: str | None):
    config = _load_config()
    if category not in config:
        config[category] = {}
    config[category][key] = emoji_html
    _save_config(config)

def get_custom_emoji(category: str, key: str) -> str | None:
    config = _load_config()
    val = config.get(category, {}).get(key)
    # Bot yubora olmaydigan (o'lik) emoji bo'lsa — yo'q deb hisoblaymiz, chaqiruvchi oddiy nomga/emojiga qaytadi
    if val:
        m = _re.search(r"emoji-id=['\"]?(\d{15,})", str(val)) or _re.search(r"^(\d{15,})$", str(val).strip())
        if m and m.group(1) in DEAD_EMOJI_IDS:
            return None
    return val

def get_custom_emoji_id(category: str, key: str) -> str | None:
    """Extract 64-bit Telegram custom_emoji_id from tag or string"""
    val = get_custom_emoji(category, key)
    if not val:
        return None
    val = str(val).strip()
    if "emoji-id=" in val:
        try:
            part = val.split("emoji-id=")[1]
            quote = part[0]
            return part[1:].split(quote)[0]
        except Exception:
            pass
    if val.isdigit() and len(val) >= 10:
        return val
    return None

def get_custom_emoji_char(category: str, key: str, default: str = "") -> str:
    val = get_custom_emoji(category, key)
    if not val:
        return default
    if "<tg-emoji" in val and "</tg-emoji>" in val:
        try:
            return val.split(">")[1].split("<")[0]
        except Exception:
            pass
    return default

def reset_all_custom_emojis():
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    _save_config(config)

def kezuvchi_display_name(gender: str = None) -> str:
    return role_display(RoleNames.KEZUVCHI)

ROLE_CLEAN_MAP = {
    "don": RoleNames.DON,
    "mafia": RoleNames.MAFIA,
    "komissar": RoleNames.KOMISSAR,
    "komissar katani": RoleNames.KOMISSAR,
    "doktor": RoleNames.DOKTOR,
    "serjant": RoleNames.SERJANT,
    "fuqaro": RoleNames.FUQARO,
    "tinch axoli": RoleNames.FUQARO,
    "daydi": RoleNames.DAYDI,
    "kezuvchi": RoleNames.KEZUVCHI,
    "advokat": RoleNames.ADVOKAT,
    "suidsid": RoleNames.SUIDSID,
    "omadli": RoleNames.OMADLI,
    "janob": RoleNames.JANOB,
    "bori": RoleNames.BORI,
    "bo'ri": RoleNames.BORI,
    "qotil": RoleNames.QOTIL,
    "ovchi": RoleNames.OVCHI,
    "yollanma qotil": RoleNames.OVCHI,
    "qasoskor": RoleNames.QASOSKOR,
    "aferist": RoleNames.AFERIST,
    "gazabdor": RoleNames.GAZABDOR,
    "g'azabkor": RoleNames.GAZABDOR,
    "sehrgar": RoleNames.SEHRGAR,
    "jurnalist": RoleNames.JURNALIST,
    "sotqin": RoleNames.SOTQIN,
    "qoriqchi": RoleNames.QORIQCHI,
    "qo'riqchi": RoleNames.QORIQCHI,
    "xoyin": RoleNames.XOYIN,
    "zanjir": RoleNames.ZANJIR,
    "aktyor": RoleNames.AKTYOR,
    "jin": RoleNames.JIN,
    "konchi": RoleNames.KONCHI,
    "aygoqchi": RoleNames.AYGOQCHI,
    "ayg'oqchi": RoleNames.AYGOQCHI,
    "qaroqchi": RoleNames.QAROQCHI,
    "hamshira": RoleNames.HAMSHIRA,
    "taqlidchi": RoleNames.TAQLIDCHI,
    "mimic": RoleNames.TAQLIDCHI,
    "reverser": RoleNames.REVERSER,
}

ROLE_NAMES_BY_LANG = {
    "uz": {
        RoleNames.DON: "🤵🏻 Don",
        RoleNames.MAFIA: "🤵🏼 Mafia",
        RoleNames.KOMISSAR: "🕵🏼 Komissar katani",
        RoleNames.DOKTOR: "👨🏼‍⚕️ Doktor",
        RoleNames.SERJANT: "👮🏼 Serjant",
        RoleNames.FUQARO: "👨🏼 Tinch axoli",
        RoleNames.DAYDI: "🧙‍♂️ Daydi",
        RoleNames.KEZUVCHI: "💃 Kezuvchi",
        RoleNames.ADVOKAT: "👨🏼‍💼 Advokat",
        RoleNames.SUIDSID: "🤦🏼 Suidsid",
        RoleNames.OMADLI: "🤞🏼 Omadli",
        RoleNames.JANOB: "🎖 Janob",
        RoleNames.BORI: "🐺 Bo'ri",
        RoleNames.QOTIL: "🔪 Qotil",
        RoleNames.OVCHI: "🥷 Yollanma qotil",
        RoleNames.QASOSKOR: "🧨 Qasoskor",
        RoleNames.AFERIST: "🤹🏻 Aferist",
        RoleNames.GAZABDOR: "🧌 G'azabkor",
        RoleNames.SEHRGAR: "🧙‍ Sehrgar",
        RoleNames.JURNALIST: "👩🏼‍💻 Jurnalist",
        RoleNames.SOTQIN: "🤓 Sotqin",
        RoleNames.AYGOQCHI: "🦇 Ayg'oqchi",
        RoleNames.KONCHI: "👷🏻‍♂️ Konchi",
        RoleNames.QAROQCHI: "⚔️ Qaroqchi",
        RoleNames.HAMSHIRA: "👩🏻‍⚕️ Hamshira",
        RoleNames.QORIQCHI: "🛡 Qo'riqchi",
        RoleNames.XOYIN: "👺 Xoyin",
        RoleNames.ZANJIR: "⛓ Zanjir",
        RoleNames.AKTYOR: "🎭 Aktyor",
        RoleNames.JIN: "🧞 Jin",
        RoleNames.TAQLIDCHI: "🎭 Taqlidchi",
        RoleNames.REVERSER: "🔄 Reverser",
    },
    "ru": {
        RoleNames.DON: "🤵🏻 Дон",
        RoleNames.MAFIA: "🤵🏼 Мафия",
        RoleNames.KOMISSAR: "🕵🏼 Комиссар",
        RoleNames.DOKTOR: "👨🏼‍⚕️ Доктор",
        RoleNames.SERJANT: "👮🏼 Сержант",
        RoleNames.FUQARO: "👨🏼 Мирный житель",
        RoleNames.DAYDI: "🧙‍♂️ Бродяга",
        RoleNames.KEZUVCHI: "💃 Кутила",
        RoleNames.ADVOKAT: "👨🏼‍💼 Адвокат",
        RoleNames.SUIDSID: "🤦🏼 Самоубийца",
        RoleNames.OMADLI: "🤞🏼 Везунчик",
        RoleNames.JANOB: "🎖 Дворянин",
        RoleNames.BORI: "🐺 Оборотень",
        RoleNames.QOTIL: "🔪 Маньяк",
        RoleNames.OVCHI: "🥷 Охотник",
        RoleNames.QASOSKOR: "🧨 Мститель",
        RoleNames.AFERIST: "🤹🏻 Аферист",
        RoleNames.GAZABDOR: "🧌 Каратель",
        RoleNames.SEHRGAR: "🧙‍ Волшебник",
        RoleNames.JURNALIST: "👩🏼‍💻 Журналист",
        RoleNames.SOTQIN: "🤓 Предатель",
        RoleNames.AYGOQCHI: "🦇 Шпион",
        RoleNames.KONCHI: "👷🏻‍♂️ Шахтер",
        RoleNames.QAROQCHI: "⚔️ Грабитель",
        RoleNames.HAMSHIRA: "👩🏻‍⚕️ Медсестра",
        RoleNames.QORIQCHI: "🛡 Телохранитель",
        RoleNames.XOYIN: "👺 Отступник",
        RoleNames.ZANJIR: "⛓ Связной",
        RoleNames.AKTYOR: "🎭 Актер",
        RoleNames.JIN: "🧞 Джинн",
        RoleNames.TAQLIDCHI: "🎭 Мимик",
        RoleNames.REVERSER: "🔄 Реверсер",
    },
    "en": {
        RoleNames.DON: "🤵🏻 Don",
        RoleNames.MAFIA: "🤵🏼 Mafia",
        RoleNames.KOMISSAR: "🕵🏼 Detective",
        RoleNames.DOKTOR: "👨🏼‍⚕️ Doctor",
        RoleNames.SERJANT: "👮🏼 Sergeant",
        RoleNames.FUQARO: "👨🏼 Civilian",
        RoleNames.DAYDI: "🧙‍♂️ Tracker",
        RoleNames.KEZUVCHI: "💃 Sleeper",
        RoleNames.ADVOKAT: "👨🏼‍💼 Lawyer",
        RoleNames.SUIDSID: "🤦🏼 Jester",
        RoleNames.OMADLI: "🤞🏼 Lucky One",
        RoleNames.JANOB: "🎖 Nobleman",
        RoleNames.BORI: "🐺 Werewolf",
        RoleNames.QOTIL: "🔪 Serial Killer",
        RoleNames.OVCHI: "🥷 Hunter",
        RoleNames.QASOSKOR: "🧨 Vigilante",
        RoleNames.AFERIST: "🤹🏻 Trickster",
        RoleNames.GAZABDOR: "🧌 Avenger",
        RoleNames.SEHRGAR: "🧙‍ Sorcerer",
        RoleNames.JURNALIST: "👩🏼‍💻 Journalist",
        RoleNames.SOTQIN: "🤓 Traitor",
        RoleNames.AYGOQCHI: "🦇 Spy",
        RoleNames.KONCHI: "👷🏻‍♂️ Miner",
        RoleNames.QAROQCHI: "⚔️ Robber",
        RoleNames.HAMSHIRA: "👩🏻‍⚕️ Nurse",
        RoleNames.QORIQCHI: "🛡 Bodyguard",
        RoleNames.XOYIN: "👺 Renegade",
        RoleNames.ZANJIR: "⛓ Linker",
        RoleNames.AKTYOR: "🎭 Actor",
        RoleNames.JIN: "🧞 Genie",
        RoleNames.TAQLIDCHI: "🎭 Mimic",
        RoleNames.REVERSER: "🔄 Reverser",
    },
    "tr": {
        RoleNames.DON: "🤵🏻 Don",
        RoleNames.MAFIA: "🤵🏼 Mafya",
        RoleNames.KOMISSAR: "🕵🏼 Komiser",
        RoleNames.DOKTOR: "👨🏼‍⚕️ Doktor",
        RoleNames.SERJANT: "👮🏼 Çavuş",
        RoleNames.FUQARO: "👨🏼 Sivil",
        RoleNames.DAYDI: "🧙‍♂️ Gezgin",
        RoleNames.KEZUVCHI: "💃 Uykucu",
        RoleNames.ADVOKAT: "👨🏼‍💼 Avukat",
        RoleNames.SUIDSID: "🤦🏼 İntiharсı",
        RoleNames.OMADLI: "🤞🏼 Şanslı",
        RoleNames.JANOB: "🎖 Asilzade",
        RoleNames.BORI: "🐺 Kurt Adam",
        RoleNames.QOTIL: "🔪 Katil",
        RoleNames.OVCHI: "🥷 Avcı",
        RoleNames.QASOSKOR: "🧨 İntikamcı",
        RoleNames.AFERIST: "🤹🏻 Sahtekar",
        RoleNames.GAZABDOR: "🧌 Cezalandırıcı",
        RoleNames.SEHRGAR: "🧙‍ Büyücü",
        RoleNames.JURNALIST: "👩🏼‍💻 Gazeteci",
        RoleNames.SOTQIN: "🤓 Hain",
        RoleNames.AYGOQCHI: "🦇 Ajan",
        RoleNames.KONCHI: "👷🏻‍♂️ Madenci",
        RoleNames.QAROQCHI: "⚔️ Soyguncu",
        RoleNames.HAMSHIRA: "👩🏻‍⚕️ Hemşire",
        RoleNames.QORIQCHI: "🛡 Koruma",
        RoleNames.XOYIN: "👺 İsyankar",
        RoleNames.ZANJIR: "⛓ Zincirci",
        RoleNames.AKTYOR: "🎭 Aktör",
        RoleNames.JIN: "🧞 Cin",
        RoleNames.TAQLIDCHI: "🎭 Taklitçi",
        RoleNames.REVERSER: "🔄 Reverser",
    },
    "kk": {
        RoleNames.DON: "🤵🏻 Дон",
        RoleNames.MAFIA: "🤵🏼 Мафия",
        RoleNames.KOMISSAR: "🕵🏼 Комиссар",
        RoleNames.DOKTOR: "👨🏼‍⚕️ Дәрігер",
        RoleNames.SERJANT: "👮🏼 Сержант",
        RoleNames.FUQARO: "👨🏼 Бейбіт тұрғын",
        RoleNames.DAYDI: "🧙‍♂️ Қаңғыбас",
        RoleNames.KEZUVCHI: "💃 Кезбе",
        RoleNames.ADVOKAT: "👨🏼‍💼 Адвокат",
        RoleNames.SUIDSID: "🤦🏼 Суицидші",
        RoleNames.OMADLI: "🤞🏼 Жолы болғыш",
        RoleNames.JANOB: "🎖 Мырза",
        RoleNames.BORI: "🐺 Қасқыр",
        RoleNames.QOTIL: "🔪 Қаныпезер",
        RoleNames.OVCHI: "🥷 Аңшы",
        RoleNames.QASOSKOR: "🧨 Кек алушы",
        RoleNames.AFERIST: "🤹🏻 Аферист",
        RoleNames.GAZABDOR: "🧌 Жазалаушы",
        RoleNames.SEHRGAR: "🧙‍ Сиқыршы",
        RoleNames.JURNALIST: "👩🏼‍💻 Журналист",
        RoleNames.SOTQIN: "🤓 Сатқын",
        RoleNames.AYGOQCHI: "🦇 Тыңшы",
        RoleNames.KONCHI: "👷🏻‍♂️ Шахтер",
        RoleNames.QAROQCHI: "⚔️ Қарақшы",
        RoleNames.HAMSHIRA: "👩🏻‍⚕️ Медбике",
        RoleNames.QORIQCHI: "🛡 Оққағар",
        RoleNames.XOYIN: "👺 Бүлікші",
        RoleNames.ZANJIR: "⛓ Байланыстырушы",
        RoleNames.AKTYOR: "🎭 Актер",
        RoleNames.JIN: "🧞 Жын",
        RoleNames.TAQLIDCHI: "🎭 Еліктеуші",
        RoleNames.REVERSER: "🔄 Реверсер",
    }
}

def role_display(role: str, lang: str = "uz") -> str:
    """
    Xabarda ko'rsatish uchun rol nomi.
    lang parametriga qarab 5 xil tilda (uz, ru, en, tr, kk) tarjima qiladi.
    """
    if not role or str(role).strip() in ("", "None", "null", "Noma'lum rol", "noma'lum rol"):
        raw_canonical = RoleNames.FUQARO
    else:
        role_str = str(role).strip()
        raw_canonical = role_str
        clean_key = role_str.lower()
        
        for prefix in ["🤵🏻", "🤵🏼", "🕵🏼", "👨🏼‍⚕️", "👮🏼", "👨🏼", "🧙‍♂️", "💃", "👨🏼‍💼", "🤦🏼", "🤞🏼", "🎖", "🐺", "🔪", "🥷", "🧨", "🤹🏻", "🧌", "🧙‍", "👩🏼‍💻", "🤓", "🛡", "👺", "⛓", "🎭", "🧞", "👷🏻‍♂️", "🦇", "⚔️", "👩🏻‍⚕️"]:
            clean_key = clean_key.replace(prefix.lower(), "").strip()
        
        if clean_key in ROLE_CLEAN_MAP:
            raw_canonical = ROLE_CLEAN_MAP[clean_key]

    lang_code = (lang or "uz").lower()
    if lang_code not in ("uz", "ru", "en", "tr", "kk"):
        lang_code = "uz"

    translated = ROLE_NAMES_BY_LANG.get(lang_code, {}).get(raw_canonical, raw_canonical)

    custom = get_custom_emoji("roles", raw_canonical) or get_custom_emoji("roles", str(role))
    if custom:
        parts = translated.split(" ", 1)
        role_text = parts[1] if len(parts) == 2 else translated
        return f"{custom} {role_text}"
    
    return translated

def get_item_display(key: str) -> str:
    """Qurol-aslaha emojisi"""
    custom = get_custom_emoji("weapons", key)
    if custom:
        return custom
    info = WEAPON_NAMES.get(key)
    return info[0] if info else "📦"

def get_diamond_display() -> str:
    """Olmos emojisi"""
    custom = get_custom_emoji("currency", "diamond")
    return custom if custom else "💎"

def get_dollar_display() -> str:
    """Dollar emojisi"""
    custom = get_custom_emoji("currency", "dollar")
    return custom if custom else "💵"

# VIP foydalanuvchilar uchun default premium emoji
DEFAULT_VIP_EMOJI_ID = "5400087962086028460"
DEFAULT_VIP_EMOJI_CHAR = "✅"

def build_vip_prefix(emoji_id: str = None, emoji_char: str = None) -> str:
    return f'<tg-emoji emoji-id="{emoji_id or DEFAULT_VIP_EMOJI_ID}">{emoji_char or DEFAULT_VIP_EMOJI_CHAR}</tg-emoji> '

def get_vip_prefix(vip_user) -> str:
    if not vip_user:
        return ""
    return build_vip_prefix(getattr(vip_user, "emoji_id", None), getattr(vip_user, "emoji_char", None))

def parse_emoji_from_message(message) -> str | None:
    """Xabardan premium emoji (custom_emoji_id) yoki matnli emoji tegi/belgisini ajratib oladi"""
    text = (message.text or message.caption or "").strip()
    if message.entities:
        for ent in message.entities:
            if ent.type == "custom_emoji" and getattr(ent, "custom_emoji_id", None):
                char = text[ent.offset : ent.offset + ent.length] if text else "✨"
                return f'<tg-emoji emoji-id="{ent.custom_emoji_id}">{char}</tg-emoji>'
    if "<tg-emoji" in text and "</tg-emoji>" in text:
        return text
    if text.isdigit() and len(text) >= 10:
        return f'<tg-emoji emoji-id="{text}">✨</tg-emoji>'
    if text:
        return text
    return None
