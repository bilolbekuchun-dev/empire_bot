from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
from models.game_data import GamePlayer, Action, GamePhase
from config import BOT_URL
from utils.role_names import RoleNames 
from random import shuffle
from random import choice, randint
from utils.vsgame import TeamCOlors

def join_vsgame_button(game_id, team_count=2):
    markup = InlineKeyboardBuilder()
    i = 1
    for color_name, color_value in TeamCOlors.all_colors_dict().items():
        if i > team_count:
            break
        markup.button(text=color_value, url=f"{BOT_URL}?&start=vsgame_{game_id}_{color_name}")
        i += 1
    markup.adjust(2)
    return markup.as_markup()

async def join_game_button(game_id):
    markup = InlineKeyboardBuilder()
    markup.button(text="🤵 Qo'shilish", url=f"{BOT_URL}?&start=game_{game_id}")
    markup.adjust(1)
    return markup.as_markup()

async def jin_choice_buttons(phase_id, target_user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✨ Hayot", callback_data=f"jin_choice_hayot_{target_user_id}_{phase_id}")
    builder.button(text="💰 Pul", callback_data=f"jin_choice_pul_{target_user_id}_{phase_id}")
    builder.button(text="💀 Qotillik", callback_data=f"jin_choice_qotil_{target_user_id}_{phase_id}")
    builder.adjust(1)
    return builder.as_markup()

async def konchi_button(role, phase_id, konlar=[]):
    markup = InlineKeyboardBuilder()
    if not konlar:
        markup.button(text="Konlar tugadi!", callback_data="no_kon")
    for i in konlar:
        markup.button(text=f"⛏ {i}", callback_data=f"{role}_{i}_{phase_id}")
    markup.adjust(5)
    return markup.as_markup()

async def kom_upgrade_buttons(user_id, phase_id):
    """Komissar menyusi — faqat Tekshirish, O'ldirish va O'tkazib yuborish"""
    def _cb(action):
        return f"kom_upgrade_{action}_{phase_id}"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Tekshirish", callback_data=_cb("tanla_tek"))
    builder.button(text="🔫 O'ldirish", callback_data=_cb("tanla_otish"))
    builder.button(text="⏭ O'tkazib yuborish", callback_data=_cb("skype"))
    builder.adjust(2, 1)
    return builder.as_markup()

async def kom_target_buttons(user_id, action_key, phase_id, players, exclude_uids=None, nik=None, vsgame=False):
    """Bosh Komissar qobiliyatlari uchun nishon tanlash klaviaturasi"""
    if exclude_uids is None:
        exclude_uids = []
    builder = InlineKeyboardBuilder()
    count = 0
    colors = TeamCOlors.all_colors_dict() if vsgame else {}
    for p in players:
        await p.fetch_related("user")
        if p.user.user_id == user_id or not p.is_alive or p.user.user_id in exclude_uids:
            continue
        count += 1
        name = p.user.full_name if not nik else nik
        if vsgame:
            name = f"{colors.get(p.team, '')}{name}"
        builder.button(text=name, callback_data=f"kom_upgrade_{action_key}_{p.user.user_id}_{phase_id}")
    if count == 0:
        return None
    builder.button(text="⬅️ Orqaga", callback_data=f"kom_upgrade_menu_{phase_id}")
    builder.adjust(1)
    return builder.as_markup()

SAVDOGAR_ITEM_NAMES = {
    "miltiq": "😀 Miltiq",
    "himoya": "🛡 Himoya",
    "hujjat": "📁 Hujjat",
    "qotildan_himoya": "🔪 Qotildan himoya",
    "osishdan_himoya": "⚖️ Osishdan himoya",
    "doridan_himoya": "➕ Doridan himoya",
    "maska": "🎭 Maska",
    "slip_himoya": "🪤 Sirpanishdan himoya",
    "geroy_himoya": "🔰 Geroydan himoya",
    "role_don": "🤵🏻 Don roli",
    "role_mafia": "🤵🏼 Mafia roli",
    "role_qotil": "🔪 Qotil roli",
    "role_doktor": "👨🏼‍⚕️ Doktor roli",
    "role_komissar": "🕵🏼 Komissar roli",
}

async def savdogar_item_buttons(role, phase_id):
    """Savdogar — sotiladigan anjomlar ro'yxati"""
    markup = InlineKeyboardBuilder()
    for item_key, label in SAVDOGAR_ITEM_NAMES.items():
        markup.button(text=label, callback_data=f"{role}_item_{item_key}_{phase_id}")
    markup.button(text="🚷 O'tkazib yuborish", callback_data=f"{role}_skype_{phase_id}")
    markup.adjust(2)
    return markup.as_markup()

async def savdogar_target_buttons(user_id, item_key, phase_id, players, nik=None, vsgame=False):
    """Savdogar — anjomni kimga taklif qilishni tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()
    count = 0
    colors = TeamCOlors.all_colors_dict() if vsgame else {}
    for p in players:
        await p.fetch_related("user")
        if p.user.user_id == user_id or not p.is_alive:
            continue
        count += 1
        name = p.user.full_name if not nik else nik
        if vsgame:
            name = f"{colors.get(p.team, '')}{name}"
        builder.button(text=name, callback_data=f"{RoleNames.SAVDOGAR}_target_{item_key}_{p.user.user_id}_{phase_id}")
    if count == 0:
        return None
    builder.adjust(1)
    return builder.as_markup()

async def savdogar_confirm_buttons(game_id, actor_id, item_key, price, currency_type):
    """Taklifni oluvchi uchun ha/yo'q tugmalari"""
    markup = InlineKeyboardBuilder()
    markup.button(text="✅ Ha", callback_data=f"savdogar_buy_ha_{game_id}_{actor_id}_{item_key}_{price}_{currency_type}")
    markup.button(text="❌ Yo'q", callback_data=f"savdogar_buy_no_{game_id}_{actor_id}_{item_key}")
    markup.adjust(2)
    return markup.as_markup()

async def action_buttons(user_id, role, players: List[GamePlayer], phase_id, vsgame=False,
                         otish=False, davo=False, tek=False, kom=False, nik=None,
                         daydi=False, kezuv=False, adv=False, kimyo=False, hayot=False, miltiq=False, adv_no=False):

    builder = InlineKeyboardBuilder()
    phase = await GamePhase.get(id=phase_id).prefetch_related("game")
    prefix = role + "_"
    if otish:
        prefix += "otish_"
    elif davo:
        prefix += "davo_"
    elif tek:
        prefix += "tek_"
    elif kezuv:
        prefix += "kezuv_"
    elif hayot:
        prefix += "hayot_"
    elif role == RoleNames.JIN:
        prefix += "choice_"

    if kom:
        builder.button(text="🔍 Tekshirish", callback_data=f"{prefix}tanla_tek_{phase_id}")
        builder.button(text="🔫 O'ldirish",  callback_data=f"{prefix}tanla_otish_{phase_id}")
        current_player = await GamePlayer.filter(user__user_id=user_id, is_alive=True).first()
        if current_player and not getattr(current_player, "kom_is_upgraded", False):
            checks = getattr(current_player, "kom_success_checks", 0)
            learn_label = "📚 O'rganish (Bosh Kom)" if checks == 0 else f"📚 O'rganish (Bosh Kom) ({checks}/3)"
            builder.button(text=learn_label, callback_data=f"learnbosh_{phase_id}")
            builder.adjust(2, 1)
        else:
            builder.adjust(2)
        return builder.as_markup()
    if miltiq:
        builder.button(text="Ha", callback_data=f"{prefix}miltiq_ha_{phase_id}")
        builder.button(text="Yo'q",  callback_data=f"{prefix}miltiq_no_{phase_id}")
        builder.adjust(2)
        return builder.as_markup()
    if kimyo:
        builder.button(text="Himoyalash", callback_data=f"{prefix}tanla_hayot_{phase_id}")
        builder.button(text="O'ldirish",  callback_data=f"{prefix}tanla_otish_{phase_id}")
        builder.adjust(2)
        return builder.as_markup()
    for player in players:
        await player.fetch_related("user")
        targ_id = player.user.user_id
        targ_role = player.role
        if targ_id == user_id:
            if role == RoleNames.GAZABDOR or "Gazabdor" in str(role) or "G'azabkor" in str(role):
                pass
            elif role == RoleNames.ZANJIR or "Zanjir" in str(role):
                pass
            elif role == RoleNames.DOKTOR or davo or "Doktor" in str(role):
                if not getattr(player, "can_heal_self", True):
                    continue
            elif adv:
                if not getattr(player, "can_osishdan_himoya_adv", False):
                    continue
            else:
                continue
        if kezuv and targ_id == getattr(player, "last_visited_user_id", None):
            continue
        if role in [RoleNames.DAYDI, RoleNames.QOTIL, RoleNames.AFERIST, RoleNames.QORIQCHI] and targ_id == getattr(player, "last_visited_user_id", None):
            continue
        if role == RoleNames.JURNALIST and targ_id == getattr(player, "last_visited_user_id", None):
            continue 

        if role == RoleNames.KOMISSAR and targ_role == RoleNames.SERJANT:
            continue

        if role in (RoleNames.DON, RoleNames.MAFIA, RoleNames.AYGOQCHI) and targ_role in (RoleNames.DON, RoleNames.MAFIA, RoleNames.AYGOQCHI):
            continue

        if role in (RoleNames.OVCHI,) and targ_role in (RoleNames.DON, RoleNames.MAFIA):
            continue
        if vsgame:
            colors_dct = TeamCOlors.all_colors_dict()
            text = f"{colors_dct.get(player.team, '')}{player.user.full_name if not nik else nik}"
        else:
            text = player.user.full_name if not nik else nik
        if targ_role == RoleNames.ADVOKAT and role in (RoleNames.DON, RoleNames.MAFIA) and not adv_no:
            text = "👨🏼‍💼 " + text

        builder.button(
            text=text,
            callback_data=f"{prefix}{targ_id}_{phase_id}"
        )
    builder.button(text="🚷 O'tkazib yuborish", callback_data=f"{prefix}skype_{phase_id}")
    builder.adjust(1)
    if role == RoleNames.KOMISSAR:
        builder.button(text="Orqaga", callback_data=f"{prefix}orqaga_{phase_id}")
    return builder.as_markup()

async def vote_buttons(user_id, role, players: List[GamePlayer], phease_id, vsgame=False, kom=False, serj=False, maf=False, don=False, adv_no=False, nik=None):
    markup = InlineKeyboardBuilder()
    for player in players:
        await player.fetch_related("user")
        if player.user.user_id == user_id:
            continue
        emoji = ""
        if vsgame:
            colors_dct = TeamCOlors.all_colors_dict()
            emoji = colors_dct.get(player.team, "")
        if player.role == RoleNames.SERJANT and role in [RoleNames.KOMISSAR, RoleNames.SERJANT]:
            emoji = "👮🏼 "
        elif player.role == RoleNames.KOMISSAR and serj and role in [RoleNames.SERJANT]:
            emoji = "🕵🏼 "
        elif player.role == RoleNames.MAFIA and role == [RoleNames.ADVOKAT, RoleNames.DON, RoleNames.MAFIA]:
            emoji = "🤵🏼 "
        elif player.role == RoleNames.DON and role == [RoleNames.ADVOKAT, RoleNames.MAFIA]:
            emoji = "🤵🏻 "

        markup.button(
            text=emoji + ( player.user.full_name if not nik else nik),
            callback_data=f"vote_{phease_id}_{player.user.user_id}"
        )
    markup.button(text="🚷 O'tkazib yuborish", callback_data=f"vote_{phease_id}_skype")
    markup.adjust(1)
    return markup.as_markup()


async def sehr_action_button(game_id, target_id):
    markup = InlineKeyboardBuilder()
    markup.button(text="Kechirish", callback_data=f'sehrgar_ha_{game_id}_{target_id}')
    markup.button(text="O'ldirish", callback_data=f'sehrgar_no_{game_id}_{target_id}')
    markup.adjust(2)
    return markup.as_markup()

def go_group_button(url):
    if not url:
        return None
    markup = InlineKeyboardBuilder()
    markup.button(text="Guruhga o'tish", url=url)
    return markup.as_markup()

def joker_buttons(phase_id, death_number):
    markup = InlineKeyboardBuilder()

    markup.button(text="♠️", callback_data=f"karta_{phase_id}_1_{death_number}")
    markup.button(text="♣️", callback_data=f"karta_{phase_id}_2_{death_number}")
    markup.button(text="♥️", callback_data=f"karta_{phase_id}_3_{death_number}")
    markup.button(text="♦️", callback_data=f"karta_{phase_id}_4_{death_number}")
    markup.adjust(2)
    return markup.as_markup()

def joker_death_select_buttons(phase_id):
    markup = InlineKeyboardBuilder()

    markup.button(text="♠️", callback_data=f"death-karta_{phase_id}_1")
    markup.button(text="♣️", callback_data=f"death-karta_{phase_id}_2")
    markup.button(text="♥️", callback_data=f"death-karta_{phase_id}_3")
    markup.button(text="♦️", callback_data=f"death-karta_{phase_id}_4")
    markup.adjust(2)
    return markup.as_markup()

def geroy_action_type_btn(phase_id, attack=False):
    markup = InlineKeyboardBuilder()
    if attack: markup.button(text="🥷 Hujum qilish", callback_data=f"game-geroy_attack_{phase_id}")
    markup.button(text="⚜️ Himoyalanish", callback_data=f"game-geroy_shield_{phase_id}")
    markup.button(text="🚷 O'tkazib yuborish", callback_data=f"game-geroy_skype_{phase_id}")
    markup.adjust(1)
    return markup.as_markup()

def geroy_action_btn(players, phase_id, action, vsgame=False, nik=None):
    markup = InlineKeyboardBuilder()
    for player in players:
        if player.role == RoleNames.KOMISSAR:
            continue
        if vsgame:
            colors_dct = TeamCOlors.all_colors_dict()
            text = f"{colors_dct.get(player.team, '')}{player.user.full_name if not nik else nik}"
        else:
            text = player.user.full_name if not nik else nik
        markup.button(text=text, callback_data=f"game-geroy-{action}_{player.user.user_id}_{phase_id}")
    markup.button(text="Ortga", callback_data="game-geroy-action-menu")
    markup.adjust(1)
    return markup.as_markup()

async def qaroqchi_action_button(role, phase_id):
    markup = InlineKeyboardBuilder()
    markup.button(text="Pul olish", callback_data=f"{role}_pul_{phase_id}")
    markup.button(text="Jon olish", callback_data=f"{role}_jon_{phase_id}")
    markup.button(text="🚷 O'tkazib yuborish", callback_data=f"{role}_skype_{phase_id}")
    markup.adjust(2)
    return markup.as_markup()