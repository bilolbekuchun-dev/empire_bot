"""
Night Engine (Redis) - Tungi harakatlarni yuborish va natijalarni qayta ishlash.

Bu modul hozirgi Redis-oqim (PlayerState/GameState) ustida ishlaydi.
Asosiy funksiyalar:
    - send_night_actions(...)      -> tunda har bir o'yinchiga rol bo'yicha tugma yuboradi
    - process_night_results(...)   -> tunda qilingan harakatlarni qo'llaydi (o'ldirish/davolash/...)
    - send_day_votes(...)          -> kunduzgi ovoz berish tugmalarini yuboradi
    - process_day_votes(...)       -> ovozlarni sanab, osishni qo'llaydi

Callback formati (<=64 bayt):
    na|{code}|{gid}|{ph}|{kind}|{target}
    - code   : rol kaliti (ko, do, dn, mf, qt, ...)
    - kind   : t=target, s=skip, c=check, k=kill, 1=first, 2=second, pul/jon (qaroqchi)
"""
import asyncio
import html
import random
from datetime import datetime, timezone
from typing import List, Optional, Dict

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from models.user import User
from models.game_data import Chat
from utils.role_names import RoleNames
from utils.roles_text import Roles
from utils.premium_emojis import role_display
from utils.redis_game.repositories.player_repository import player_repository as player_repo
from utils.redis_game.repositories.game_repository import game_repository as game_repo
from utils.redis_game.services.action_service import ActionService
from utils.redis_game.services.vote_service import VoteService
from utils.database import redis_client as r

# ------------------------------------------------------------------
# Rol -> qisqa kalit (callback uchun)
# ------------------------------------------------------------------
ROLE_CODE: Dict[str, str] = {
    RoleNames.KOMISSAR: "ko",
    RoleNames.DOKTOR: "do",
    RoleNames.DON: "dn",
    RoleNames.MAFIA: "mf",
    RoleNames.AYGOQCHI: "ay",
    RoleNames.QOTIL: "qt",
    RoleNames.OVCHI: "ov",
    RoleNames.DAYDI: "dy",
    RoleNames.KEZUVCHI: "kz",
    RoleNames.ZANJIR: "zj",
    RoleNames.XOYIN: "xy",
    RoleNames.QORIQCHI: "qr",
    RoleNames.ADVOKAT: "av",
    RoleNames.GAZABDOR: "ga",
    RoleNames.AFERIST: "af",
    RoleNames.SEHRGAR: "se",
    RoleNames.JURNALIST: "ju",
    RoleNames.SOTQIN: "so",
    RoleNames.KONCHI: "kn",
    RoleNames.QAROQCHI: "qa",
    RoleNames.JIN: "ji",
    RoleNames.REVERSER: "rv",
}

# Tungi harakati bor rollar (tugma oladi)
NIGHT_ACTION_ROLES = set(ROLE_CODE.keys())

# Har bir rol uchun harakat turi (ActionService.action_type)
ROLE_ACTION_TYPE: Dict[str, str] = {
    RoleNames.KOMISSAR: "investigate",
    RoleNames.DOKTOR: "heal",
    RoleNames.DON: "kill",
    RoleNames.MAFIA: "kill",
    RoleNames.AYGOQCHI: "investigate",
    RoleNames.QOTIL: "kill",
    RoleNames.OVCHI: "kill",
    RoleNames.DAYDI: "investigate",
    RoleNames.KEZUVCHI: "sleep",
    RoleNames.ZANJIR: "zanjir",
    RoleNames.XOYIN: "xoyin",
    RoleNames.QORIQCHI: "protect",
    RoleNames.ADVOKAT: "advokat",
    RoleNames.GAZABDOR: "gazabdor",
    RoleNames.AFERIST: "aferist",
    RoleNames.SEHRGAR: "sehrgar",
    RoleNames.JURNALIST: "investigate",
    RoleNames.SOTQIN: "sotqin",
    RoleNames.KONCHI: "konchi",
    RoleNames.QAROQCHI: "qaroqchi",
    RoleNames.JIN: "jin",
    RoleNames.REVERSER: "reverser",
}

# Qotillik harakatlari (uyqu/tegilmagan bo'lsa o'ldiradi)
KILL_ACTIONS = {"kill"}

MAFIA_ROLES = {RoleNames.DON, RoleNames.MAFIA, RoleNames.AYGOQCHI}

NIGHT_STRINGS = {
    "uz": {
        "slept": "Ana, dori ta'sir qilishni boshladi, endi bir kun uxlaysan... dedi Kezuvchi.",
        "xoyin_win": "👺 Siz mafiyani topdingiz va endi mafiyaga aylandingiz!",
        "xoyin_miss": "👺 Topa olmadingiz ({miss}/3).",
        "investigate_res": "🔍 Natija: {name} → <b>{role}</b>",
        "jurnalist_res": "📰 Ma'lumot: {name} → <b>{role}</b>",
        "aygoqchi_res": "🦇 Ayg'oqchi: {name} → <b>{role}</b>",
        "konchi_kill_reason": "Kon tuzog'iga tushdi.",
        "konchi_win": "⛏ Kon {no}: {count} 💎 qazib oldingiz!",
        "day_vote_prompt": "Kimga ovoz berasiz?",
        "day_no_vote": "Bugun hech kim osilmadi.",
        "day_tie_vote": "Ovozlar teng bo'ldi — bugun hech kim osilmadi.",
        "advokat_protect": "⚖️ Advokat {name} ni himoya qildi — u osilmadi!",
        "lynched_msg": "🪢 {name} xalq tomonidan osildi!\nU edi — <b>{role}</b>",
        "actor_msg": "🎭 <b>Aktyor</b>: Siz bu tun <b>{role}</b> roliga kirdingiz!",
        "mimic_win": "🎭 <b>Taqlidchi</b>: Siz halok bo'lgan o'yinchining rolini egalladingiz!\nYangi rolingiz: <b>{role}</b>",
        "mimic_wait": "🎭 <b>Taqlidchi</b>: Hali hech kim halok bo'lmadi — birinchi o'lik o'yinchining rolini kuting.",
        "passive_msg": "🌙 <b>Tun bo'ldi.</b>\nRolingiz: {role}\n\nBu tunda maxsus harakatingiz yo'q — tonggacha kuting.",
        "target_prompt": "🌙 {role} — nishonni tanlang:",
        "skip_btn": "🚷 O'tkazib yuborish",
        "back_btn": "🔙 Ortga",
        "komissar_prompt": "🕵🏼 <b>Komissar</b>, nima qilasiz?",
        "komissar_check_btn": "🔍 Tekshirish",
        "komissar_shoot_btn": "🔫 O'ldirish",
        "konchi_prompt": "👷🏻‍♂️ <b>Konchi</b>, qaysi kondan qazasiz? (ba'zilarida tuzoq bor!)",
        "jin_prompt": "🧞 <b>Jin</b> keldi, tilagingizni tanlang:",
        "jin_life_btn": "✨ Hayot",
        "jin_money_btn": "💰 Pul",
        "jin_kill_btn": "💀 Qotillik",
        "zanjir_prompt": "⛓ <b>Zanjir</b>: bog'lash uchun <b>1-nishon</b>ni tanlang.",
        "sehrgar_prompt": "🧙 <b>Sehrgar</b>: almashtirish uchun <b>1-nishon</b>ni tanlang.",
        "reverser_prompt": "🔄 <b>Reverser</b>: harakatini burmoqchi bo'lgan <b>1-o'yinchi (Manba)</b>ni tanlang:",
        "death_pm_msg": "💀 <b>Siz o'yingdan chiqdingiz!</b>\n\n💬 Guruhingizga <b>oxirgi so'z</b>ingizni yuborish uchun shu yerga (bot shaxsiyiga) matningizni yuboring!",
    },
    "ru": {
        "slept": "💤 Вас усыпили снотворным — этой ночью вы спите.",
        "xoyin_win": "👺 Вы нашли мафию и присоединились к ней!",
        "xoyin_miss": "👺 Не угадали ({miss}/3).",
        "investigate_res": "🔍 Результат: {name} → <b>{role}</b>",
        "jurnalist_res": "📰 Информация: {name} → <b>{role}</b>",
        "aygoqchi_res": "🦇 Шпион: {name} → <b>{role}</b>",
        "konchi_kill_reason": "Попал в ловушку в шахте.",
        "konchi_win": "⛏ Шахта {no}: вы добыли {count} 💎!",
        "day_vote_prompt": "<b>День</b> — кого повесим?",
        "day_no_vote": "Сегодня никто не был повешен.",
        "day_tie_vote": "Голоса разделились поровну — никто не повешен.",
        "advokat_protect": "⚖️ Адвокат защитил {name} — его не повесили!",
        "lynched_msg": "🪢 {name} был повешен обществом!\nОн был — <b>{role}</b>",
        "actor_msg": "🎭 <b>Актер</b>: На эту ночь ваша роль — <b>{role}</b>!",
        "mimic_win": "🎭 <b>Мимик</b>: Вы приняли роль погибшего игрока!\nВаша новая роль: <b>{role}</b>",
        "mimic_wait": "🎭 <b>Мимик</b>: Еще никто не погиб — ждете первого погибшего игрока.",
        "passive_msg": "🌙 <b>Наступила ночь.</b>\nВаша роль: {role}\n\nУ вас нет ночных действий — ждите утра.",
        "target_prompt": "🌙 {role} — выберите цель:",
        "skip_btn": "🚷 Пропустить",
        "back_btn": "🔙 Назад",
        "komissar_prompt": "🕵🏼 <b>Комиссар</b>, что делаем?",
        "komissar_check_btn": "🔍 Проверить",
        "komissar_shoot_btn": "🔫 Убить",
        "konchi_prompt": "👷🏻‍♂️ <b>Шахтер</b>, какую шахту копаем? (в некоторых есть ловушки!)",
        "jin_prompt": "🧞 <b>Джинн</b> пришел, выберите желание:",
        "jin_life_btn": "✨ Жизнь",
        "jin_money_btn": "💰 Деньги",
        "jin_kill_btn": "💀 Убийство",
        "zanjir_prompt": "⛓ <b>Связной</b>: выберите <b>1-ю цель</b> для связывания.",
        "sehrgar_prompt": "🧙 <b>Волшебник</b>: выберите <b>1-ю цель</b> для обмена.",
        "reverser_prompt": "🔄 <b>Реверсер</b>: выберите <b>1-го игрока (Источник)</b>:",
        "death_pm_msg": "💀 <b>Вы выбыли из игры!</b>\n\n💬 Чтобы отправить <b>последнее слово</b> в группу, отправьте текст сюда (в личку бота)!",
    },
    "en": {
        "slept": "💤 You were put to sleep — you sleep through this night.",
        "xoyin_win": "👺 You found the mafia and became part of them!",
        "xoyin_miss": "👺 Missed ({miss}/3).",
        "investigate_res": "🔍 Result: {name} → <b>{role}</b>",
        "jurnalist_res": "📰 Info: {name} → <b>{role}</b>",
        "aygoqchi_res": "🦇 Spy: {name} → <b>{role}</b>",
        "konchi_kill_reason": "Fell into a mine trap.",
        "konchi_win": "⛏ Mine {no}: You mined {count} 💎!",
        "day_vote_prompt": "<b>Day</b> — Who shall we lynch?",
        "day_no_vote": "No one was lynched today.",
        "day_tie_vote": "Tie vote — no one was lynched today.",
        "advokat_protect": "⚖️ The Lawyer defended {name} — lynch prevented!",
        "lynched_msg": "🪢 {name} was lynched by the town!\nThey were — <b>{role}</b>",
        "actor_msg": "🎭 <b>Actor</b>: For tonight, your role is <b>{role}</b>!",
        "mimic_win": "🎭 <b>Mimic</b>: You inherited the dead player's role!\nNew role: <b>{role}</b>",
        "mimic_wait": "🎭 <b>Mimic</b>: No one has died yet — waiting for the first casualty.",
        "passive_msg": "🌙 <b>Night has fallen.</b>\nYour role: {role}\n\nYou have no night action — wait until morning.",
        "target_prompt": "🌙 {role} — choose a target:",
        "skip_btn": "🚷 Skip",
        "back_btn": "🔙 Back",
        "komissar_prompt": "🕵🏼 <b>Detective</b>, what is your move?",
        "komissar_check_btn": "🔍 Investigate",
        "komissar_shoot_btn": "🔫 Shoot",
        "konchi_prompt": "👷🏻‍♂️ <b>Miner</b>, which mine to dig? (some contain deadly traps!)",
        "jin_prompt": "🧞 <b>Genie</b> has arrived, make a wish:",
        "jin_life_btn": "✨ Life",
        "jin_money_btn": "💰 Money",
        "jin_kill_btn": "💀 Murder",
        "zanjir_prompt": "⛓ <b>Linker</b>: select <b>target 1</b> to link.",
        "sehrgar_prompt": "🧙 <b>Sorcerer</b>: select <b>target 1</b> to swap.",
        "reverser_prompt": "🔄 <b>Reverser</b>: select <b>Player 1 (Source)</b>:",
        "death_pm_msg": "💀 <b>You are out of the game!</b>\n\n💬 To send your <b>last words</b> to the group, type your message here!",
    },
    "tr": {
        "slept": "💤 Uyku hapı verildi — bu gece uyuyorsunuz.",
        "xoyin_win": "👺 Mafyayı buldunuz ve mafya oldunuz!",
        "xoyin_miss": "👺 Bulamadınız ({miss}/3).",
        "investigate_res": "🔍 Sonuç: {name} → <b>{role}</b>",
        "jurnalist_res": "📰 Bilgi: {name} → <b>{role}</b>",
        "aygoqchi_res": "🦇 Ajan: {name} → <b>{role}</b>",
        "konchi_kill_reason": "Maden tuzağına düştü.",
        "konchi_win": "⛏ Maden {no}: {count} 💎 çıkardınız!",
        "day_vote_prompt": "<b>Gündüz</b> — Kimi asıyoruz?",
        "day_no_vote": "Bugün kimse asılmadı.",
        "day_tie_vote": "Oylar eşit — bugün kimse asılmadı.",
        "advokat_protect": "⚖️ Avukat {name} kişisini savundu — asılmadı!",
        "lynched_msg": "🪢 {name} halk tarafından asıldı!\nRolü: <b>{role}</b>",
        "actor_msg": "🎭 <b>Aktör</b>: Bu geceki rolünüz: <b>{role}</b>!",
        "mimic_win": "🎭 <b>Taklitçi</b>: Ölen oyuncunun rolünü aldınız!\nYangi rolünüz: <b>{role}</b>",
        "mimic_wait": "🎭 <b>Taklitçi</b>: Henüz kimse ölmedi — ilk ölen oyuncuyu bekliyorsunuz.",
        "passive_msg": "🌙 <b>Gece oldu.</b>\nRolünüz: {role}\n\nGece eyleminiz yok — sabaha kadar bekleyin.",
        "target_prompt": "🌙 {role} — hedef seçin:",
        "skip_btn": "🚷 Pas geç",
        "back_btn": "🔙 Geri",
        "komissar_prompt": "🕵🏼 <b>Komiser</b>, ne yapacaksınız?",
        "komissar_check_btn": "🔍 Kontrol",
        "komissar_shoot_btn": "🔫 Öldür",
        "konchi_prompt": "👷🏻‍♂️ <b>Madenci</b>, hangi madenden kazacaksınız?",
        "jin_prompt": "🧞 <b>Cin</b> geldi, dileğinizi seçin:",
        "jin_life_btn": "✨ Yaşam",
        "jin_money_btn": "💰 Para",
        "jin_kill_btn": "💀 Cinayet",
        "zanjir_prompt": "⛓ <b>Zincir</b>: bağlamak için <b>1. hedefi</b> seçin.",
        "sehrgar_prompt": "🧙 <b>Büyücü</b>: değiştirmek için <b>1. hedefi</b> seçin.",
        "reverser_prompt": "🔄 <b>Reverser</b>: <b>1. oyuncuyu (Kaynak)</b> seçin:",
        "death_pm_msg": "💀 <b>Oyundan elendiniz!</b>\n\n💬 Gruba <b>son sözünüzü</b> göndermek için buraya yazın!",
    },
    "kk": {
        "slept": "💤 Ұйқы дәрісі берілді — бұл түнде ұйықтайсыз.",
        "xoyin_win": "👺 Сіз мафияны таптыңыз және мафияға айналдыңыз!",
        "xoyin_miss": "👺 Таба алмадыңыз ({miss}/3).",
        "investigate_res": "🔍 Нәтиже: {name} → <b>{role}</b>",
        "jurnalist_res": "📰 Ақпарат: {name} → <b>{role}</b>",
        "aygoqchi_res": "🦇 Тыңшы: {name} → <b>{role}</b>",
        "konchi_kill_reason": "Шахта тұзағына түсті.",
        "konchi_win": "⛏ Шахта {no}: {count} 💎 қазып алдыңыз!",
        "day_vote_prompt": "Кімге дауыс бересіз?",
        "day_no_vote": "Бүгін ешкім асылған жоқ.",
        "day_tie_vote": "Дауыстар тең түсті — бүгін ешкім асылған жоқ.",
        "advokat_protect": "⚖️ Адвокат {name} қорғады — ол асылған жоқ!",
        "lynched_msg": "🪢 {name} халық тарапынан асылды!\nОның ролі — <b>{role}</b>",
        "actor_msg": "🎭 <b>Актер</b>: Бұл түнде сіз <b>{role}</b> роліне кірдіңіз!",
        "mimic_win": "🎭 <b>Еліктеуші</b>: Сіз қаза тапқан ойыншының ролін алдыңыз!\nЖаңа роліңіз: <b>{role}</b>",
        "mimic_wait": "🎭 <b>Еліктеуші</b>: Әлі ешкім қаза тапқан жоқ — бірінші өлі ойыншыны күтіңіз.",
        "passive_msg": "🌙 <b>Түн басталды.</b>\nРоліңіз: {role}\n\nБұл түнде арнайы әрекетіңіз жоқ — таңға дейін күтіңіз.",
        "target_prompt": "🌙 {role} — нысананы таңдаңыз:",
        "skip_btn": "🚷 Өткізіп жіберу",
        "back_btn": "🔙 Артқа",
        "komissar_prompt": "🕵🏼 <b>Комиссар</b>, не істейсіз?",
        "komissar_check_btn": "🔍 Тексеру",
        "komissar_shoot_btn": "🔫 Өлтіру",
        "konchi_prompt": "👷🏻‍♂️ <b>Шахтер</b>, қай шахтадан қазасыз? (кейбірінде тұзақ бар!)",
        "jin_prompt": "🧞 <b>Жын</b> келді, тілегіңізді таңдаңыз:",
        "jin_life_btn": "✨ Өмір",
        "jin_money_btn": "💰 Ақша",
        "jin_kill_btn": "💀 Өлтіру",
        "zanjir_prompt": "⛓ <b>Шынжыр</b>: байлау үшін <b>1-нысананы</b> таңдаңыз.",
        "sehrgar_prompt": "🧙 <b>Сиқыршы</b>: ауыстыру үшін <b>1-нысананы</b> таңдаңыз.",
        "reverser_prompt": "🔄 <b>Реверсер</b>: әрекетін бұрғыңыз келетін <b>1-ойыншыны (Дереккөз)</b> таңдаңыз:",
        "death_pm_msg": "💀 <b>Сіз ойыннан шықтыңыз!</b>\n\n💬 Тобыңызға <b>соңғы сөзіңізді</b> жіберу үшін осы жерге (бот жекесіне) мәтініңізді жіберіңіз!",
    }
}
# ------------------------------------------------------------------
async def _name_map(user_ids: List[int]) -> Dict[int, str]:
    """user_id -> ko'rsatiladigan ism"""
    result = {}
    users = await User.filter(user_id__in=list({int(u) for u in user_ids}))
    for u in users:
        result[u.user_id] = u.full_name or (u.username or str(u.user_id))
    for uid in user_ids:
        result.setdefault(uid, str(uid))
    return result


def _cb(code: str, gid: int, ph: int, kind: str, target) -> str:
    return f"na|{code}|{gid}|{ph}|{kind}|{target}"


def _target_kb(code: str, gid: int, ph: int, targets: List[tuple], skip_label="🚷 O'tkazib yuborish"):
    """targets: [(uid, label), ...]"""
    kb = InlineKeyboardBuilder()
    for uid, label in targets:
        kb.button(text=label, callback_data=_cb(code, gid, ph, "t", uid))
    if skip_label:
        kb.button(text=skip_label, callback_data=_cb(code, gid, ph, "s", 0))
    kb.adjust(1)
    return kb.as_markup()


async def _send_private(bot: Bot, uid: int, text: str, kb=None) -> bool:
    try:
        await bot.send_message(uid, text, parse_mode="HTML", reply_markup=kb)
        return True
    except Exception:
        return False


def _targets_list(players: List, exclude: set) -> List[tuple]:
    return [(p.user_id, None) for p in players if p.user_id not in exclude]


async def send_night_actions(
    game_id: int,
    night_num: int,
    players: List,
    bot: Bot,
    chat: Chat,
) -> None:
    """Tunda har bir tirik o'yinchiga rol bo'yicha harakat tugmasini yuboradi."""
    from utils.i18n import get_chat_lang
    chat_lang = await get_chat_lang(chat.chat_id)
    ns = NIGHT_STRINGS.get(chat_lang, NIGHT_STRINGS["uz"])
    skip_label = ns.get("skip_btn", "🚷 O'tkazib yuborish")

    # Yangi tun boshlanishida uxlab yotganlarni uyg'otamiz
    for p in players:
        if getattr(p, "is_sleep", False):
            p.is_sleep = False
            await player_repo.save_player(p)

    names = await _name_map([p.user_id for p in players])
    alive = [p for p in players if p.is_alive]
    expected_uids = set()

    for p in alive:
        role = p.role
        uid = p.user_id

        # Aktyor har tunda yangi (tasodifiy) faol rolga kiradi
        if role == RoleNames.AKTYOR:
            possible_actor_roles = [r for r in ROLE_CODE.keys() if r != RoleNames.AKTYOR]
            actor_night_role = random.choice(possible_actor_roles)
            await r.set(f"game:{game_id}:night:{night_num}:actor_role:{uid}", actor_night_role, ex=3600)
            await r.set(f"game:{game_id}:player:{uid}:actor_role", actor_night_role, ex=3600)
            actor_fmt = ns.get("actor_msg", "🎭 <b>Aktyor</b>: Siz bu tun <b>{role}</b> roliga kirdingiz!")
            await _send_private(
                bot, uid,
                actor_fmt.format(role=role_display(actor_night_role))
            )
            role = actor_night_role

        # Taqlidchi (Mimic): Birinchi halok bo'lgan o'yinchining rolini egallaydi
        if role == RoleNames.TAQLIDCHI:
            copied = await r.get(f"game:{game_id}:player:{uid}:copied_role")
            if copied:
                role = copied.decode() if isinstance(copied, bytes) else copied
            else:
                all_pl = await player_repo.get_all_players(game_id)
                dead = [q for q in all_pl if not q.is_alive and q.role != RoleNames.TAQLIDCHI]
                if dead:
                    new_role = dead[-1].role
                    await r.set(f"game:{game_id}:player:{uid}:copied_role", new_role)
                    p.role = new_role
                    await player_repo.save_player(p)
                    mimic_fmt = ns.get("mimic_win", "🎭 <b>Taqlidchi</b>: Siz halok bo'lgan o'yinchining rolini egalladingiz!\nYangi rolingiz: <b>{role}</b>")
                    await _send_private(
                        bot, uid,
                        mimic_fmt.format(role=role_display(new_role))
                    )
                    role = new_role
                else:
                    await _send_private(
                        bot, uid,
                        ns.get("mimic_wait", "🎭 <b>Taqlidchi</b>: Hali hech kim halok bo'lmadi — birinchi o'lik o'yinchining rolini kuting.")
                    )
                    continue

        code = ROLE_CODE.get(role)

        # Passiv rollar uchun oddiy xabar
        if code is None:
            passive_fmt = ns.get("passive_msg", "🌙 <b>Tun bo'ldi.</b>\nRolingiz: {role}\n\nBu tunda maxsus harakatingiz yo'q — tonggacha kuting.")
            await _send_private(
                bot, uid,
                passive_fmt.format(role=role_display(role))
            )
            continue

        # Harakati bor tirik rol foydalanuvchisi
        expected_uids.add(uid)

        # Nishon ro'yxati (o'zini istisno qilish)
        others = [q for q in alive if q.user_id != uid]
        if role in (RoleNames.DOKTOR, RoleNames.GAZABDOR, RoleNames.ZANJIR):
            target_pool = alive[:]
        elif role in MAFIA_ROLES:
            target_pool = [q for q in others if q.role not in MAFIA_ROLES]
        elif role == RoleNames.OVCHI:
            target_pool = [q for q in others if q.role not in (RoleNames.DON, RoleNames.MAFIA)]
        elif role == RoleNames.KOMISSAR:
            target_pool = [q for q in others if q.role != RoleNames.SERJANT]
        else:
            target_pool = others

        mk_targets = [(q.user_id, f"{names.get(q.user_id)}") for q in target_pool]

        # --- Komissar: avval rejim tanlash (tekshirish / o'ldirish / skip) ---
        if role == RoleNames.KOMISSAR:
            kb = InlineKeyboardBuilder()
            kb.button(text=ns.get("komissar_check_btn", "🔍 Tekshirish"), callback_data=_cb("ko", game_id, night_num, "c", 0))
            kb.button(text=ns.get("komissar_shoot_btn", "🔫 O'ldirish"), callback_data=_cb("ko", game_id, night_num, "k", 0))
            kb.button(text=skip_label, callback_data=_cb("ko", game_id, night_num, "s", 0))
            kb.adjust(2, 1)
            await _send_private(
                bot, uid,
                ns.get("komissar_prompt", "🕵🏼 <b>Komissar</b>, nima qilasiz?"),
                kb.as_markup()
            )
            continue

        # --- Konchi: kon tanlash ---
        if role == RoleNames.KONCHI:
            kb = InlineKeyboardBuilder()
            for i in range(1, 6):
                kb.button(text=f"⛏ Kon {i}", callback_data=_cb("kn", game_id, night_num, "t", i))
            kb.button(text=skip_label, callback_data=_cb("kn", game_id, night_num, "s", 0))
            kb.adjust(5, 1)
            await _send_private(
                bot, uid,
                ns.get("konchi_prompt", "👷🏻‍♂️ <b>Konchi</b>, qaysi kondan qazasiz? (ba'zilarida tuzoq bor!)"),
                kb.as_markup()
            )
            continue

        # --- Qaroqchi: nishon tanlash ---
        if role == RoleNames.QAROQCHI:
            await _send_private(bot, uid, f"⚔️ {role_display(role)}",
                                _target_kb("qa", game_id, night_num, mk_targets, skip_label=skip_label))
            continue

        # --- Jin: tilak tanlash menyusi ---
        if role == RoleNames.JIN:
            kb = InlineKeyboardBuilder()
            kb.button(text=ns.get("jin_life_btn", "✨ Hayot"), callback_data=_cb("ji", game_id, night_num, "jh_menu", 0))
            kb.button(text=ns.get("jin_money_btn", "💰 Pul"), callback_data=_cb("ji", game_id, night_num, "jp_menu", 0))
            kb.button(text=ns.get("jin_kill_btn", "💀 Qotillik"), callback_data=_cb("ji", game_id, night_num, "jq_menu", 0))
            kb.button(text=skip_label, callback_data=_cb("ji", game_id, night_num, "s", 0))
            kb.adjust(1)
            await _send_private(
                bot, uid,
                ns.get("jin_prompt", "🧞 <b>Jin</b> keldi, tilagingizni tanlang:"),
                kb.as_markup()
            )
            continue

        # --- Zanjir / Sehrgar / Reverser: 2 nishonli (1-qadam) ---
        if role in (RoleNames.ZANJIR, RoleNames.SEHRGAR, RoleNames.REVERSER):
            if role == RoleNames.ZANJIR:
                tcode, label = "zj", ns.get("zanjir_prompt", "⛓ <b>Zanjir</b>: bog'lash uchun <b>1-nishon</b>ni tanlang.")
            elif role == RoleNames.SEHRGAR:
                tcode, label = "se", ns.get("sehrgar_prompt", "🧙 <b>Sehrgar</b>: almashtirish uchun <b>1-nishon</b>ni tanlang.")
            else:
                tcode, label = "rv", ns.get("reverser_prompt", "🔄 <b>Reverser</b>: harakatini burmoqchi bo'lgan <b>1-o'yinchi (Manba)</b>ni tanlang:")
            await _send_private(bot, uid, label, _target_kb(tcode, game_id, night_num, mk_targets, skip_label=skip_label))
            continue

        # --- Oddiy bitta nishonli harakatlar ---
        target_fmt = ns.get("target_prompt", "🌙 {role} — nishonni tanlang:")
        label = target_fmt.format(role=role_display(role))
        await _send_private(bot, uid, label, _target_kb(code, game_id, night_num, mk_targets, skip_label=skip_label))

    # Tungi kutilayotgan harakatlarni Redis keshiga saqlaymiz
    key_exp = f"game:{game_id}:night:{night_num}:expected_users"
    key_comp = f"game:{game_id}:night:{night_num}:completed_users"
    try:
        await r.delete(key_exp, key_comp)
        if expected_uids:
            await r.sadd(key_exp, *[str(u) for u in expected_uids])
            await r.expire(key_exp, 3600)
        await r.expire(key_comp, 3600)
    except Exception:
        pass


# ==================================================================
# NATIJALARNI QAYTA ISHLASH
# ==================================================================
async def _kill(game_id: int, uid: int, by_uid: Dict, bot: Bot, chat: Chat, names: Dict,
                reason: str = "", killer_role: Optional[str] = None, custom_text: Optional[str] = None) -> Optional[object]:
    p = by_uid.get(uid)
    if not p or not p.is_alive:
        return None
    p.is_alive = False
    p.deaded_at = datetime.now(timezone.utc)
    await player_repo.save_player(p)
    try:
        if custom_text:
            text = custom_text
        else:
            victim_name = html.escape(str(names.get(uid) or uid))
            mention = f'<a href="tg://user?id={int(uid)}">{victim_name}</a>'
            text = f"Tunda {role_display(p.role)} {mention} vaxshiylarcha o'ldirildi!"
            if killer_role:
                text += f"\nAytishlaricha unikiga {role_display(killer_role)} kelgan ekan..."
            elif reason:
                text += f"\n{reason}"
        # Xabar darhol emas, TONGDAN KEYIN yuboriladi (navbatga qo'yiladi).
        await queue_death_message(game_id, text)
        try:
            from utils.i18n import get_chat_lang
            c_lang = await get_chat_lang(chat.chat_id)
            d_msg = NIGHT_STRINGS.get(c_lang, NIGHT_STRINGS["uz"]).get("death_pm_msg", NIGHT_STRINGS["uz"]["death_pm_msg"])
            await bot.send_message(
                int(uid),
                d_msg,
                parse_mode="HTML"
            )
        except Exception:
            pass
    except Exception:
        pass
    return p


# ==================================================================
# TUNGA KECHIKTIRILGAN O'LIM XABARLARI (tongdan keyin chiqadi)
# ==================================================================
async def queue_death_message(game_id: int, text: str) -> None:
    """O'lim xabarini navbatga qo'yish — tong habaridan KEYIN yuboriladi."""
    try:
        key = f"game:{game_id}:pending_deaths"
        await r.rpush(key, text)
        await r.expire(key, 3600)
    except Exception:
        pass


async def flush_pending_deaths(game_id: int, bot: Bot, chat: Chat) -> None:
    """Yig'ilgan o'lim xabarlarini guruhga yuborish (tongdan keyin, ro'yxatdan oldin)."""
    try:
        key = f"game:{game_id}:pending_deaths"
        items = await r.lrange(key, 0, -1)
        if not items:
            return
        await r.delete(key)
    except Exception:
        return
    for raw in items:
        text = raw.decode() if isinstance(raw, bytes) else raw
        try:
            await bot.send_message(
                chat.chat_id, text, parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception:
            pass


async def _user_lang_map(uids: List[int], chat_id: int = 0) -> Dict[int, str]:
    try:
        if chat_id:
            from utils.i18n import get_chat_lang
            chat_lang = await get_chat_lang(chat_id)
            return {uid: chat_lang for uid in uids}
        users = await User.filter(user_id__in=uids).all()
        return {u.user_id: (u.lang or "uz").lower() for u in users}
    except Exception:
        return {}


async def process_night_results(game_id: int, night_num: int, players: List, bot: Bot, chat: Chat) -> None:
    """Tungi harakatlarni qo'llash: o'ldirish, davolash, himoya, tekshiruv va h.k."""
    all_uids = [p.user_id for p in players]
    names = await _name_map(all_uids)
    lang_map = await _user_lang_map(all_uids, chat_id=chat.chat_id)
    by_uid = {p.user_id: p for p in players}
    actions = await ActionService.get_phase_actions(game_id, night_num)

    def get_msg(uid: int, key: str, **kwargs) -> str:
        code = lang_map.get(uid, "uz")
        if code not in ("uz", "ru", "en", "tr"):
            code = "uz"
        msg = NIGHT_STRINGS.get(code, NIGHT_STRINGS["uz"]).get(key, NIGHT_STRINGS["uz"].get(key, ""))
        return msg.format(**kwargs) if kwargs else msg

    # --- Reverser: 3-Pass Deterministik harakatni burish va Nishon Validatsiyasi ---
    reverser_actions = [a for a in actions if a.get("action_type") in ("reverser_source", "reverser_target")]
    rev_actors = sorted(list({a["actor_id"] for a in reverser_actions}))
    
    # 1-Pass: Reverser meta-redireksiyalari (Reverser boshqa Reverserni nishonga olganda)
    for rev_uid in rev_actors:
        src_act = next((a for a in reverser_actions if a["actor_id"] == rev_uid and a["action_type"] == "reverser_source"), None)
        tgt_act = next((a for a in reverser_actions if a["actor_id"] == rev_uid and a["action_type"] == "reverser_target"), None)
        if src_act and tgt_act and src_act.get("target_id") and tgt_act.get("target_id"):
            src_id = src_act["target_id"]
            dst_id = tgt_act["target_id"]
            if src_id in rev_actors:
                for other_act in reverser_actions:
                    if other_act["actor_id"] == src_id and other_act["action_type"] == "reverser_target":
                        other_act["target_id"] = dst_id

    # 2-Pass: Asosiy tungi harakatlarni yo'naltirish
    for rev_uid in rev_actors:
        src_act = next((a for a in reverser_actions if a["actor_id"] == rev_uid and a["action_type"] == "reverser_source"), None)
        tgt_act = next((a for a in reverser_actions if a["actor_id"] == rev_uid and a["action_type"] == "reverser_target"), None)
        if src_act and tgt_act and src_act.get("target_id") and tgt_act.get("target_id"):
            src_id = src_act["target_id"]
            dst_id = tgt_act["target_id"]
            for act in actions:
                if act["actor_id"] == src_id and act.get("action_type") not in ("reverser_source", "reverser_target"):
                    act["target_id"] = dst_id

    # 3-Pass: Burilgan nishonlarni validatsiya qilish (tiriklik va noqonuniy o'ziga qaratish)
    for act in actions:
        if act.get("action_type") in ("reverser_source", "reverser_target"):
            continue
        tgt_id = act.get("target_id")
        if tgt_id is not None:
            target_player = by_uid.get(tgt_id)
            if not target_player or not target_player.is_alive:
                act["target_id"] = None
            elif target_player.user_id == act["actor_id"]:
                actor_player = by_uid.get(act["actor_id"])
                if actor_player and actor_player.role in (RoleNames.DON, RoleNames.MAFIA, RoleNames.QOTIL, RoleNames.OVCHI, RoleNames.KOMISSAR):
                    act["target_id"] = None

    # --- Kezuvchi (Sleep) aniqlash ---
    slept = set()
    for a in actions:
        if a.get("action_type") == "sleep" and a.get("target_id"):
            slept.add(a["target_id"])

    # Kezuvchi tomonidan uxlatilganlar tungi harakat bajara olmaydi
    valid_actions = [a for a in actions if a["actor_id"] not in slept or a.get("action_type") == "sleep"]

    mafia_votes: Dict[int, int] = {}
    mafia_voters: Dict[int, int] = {}
    don_target = None
    don_actor_id = None
    qotil_target = None
    qotil_actor_id = None
    ovchi_target = None
    ovchi_actor_id = None
    komissar_target = None
    komissar_actor_id = None
    healed, protected = set(), set()
    zanjir: Dict[int, list] = {}
    swaps: Dict[int, list] = {}
    xoyin: Dict[int, int] = {}
    investigates = []
    jin_kill = []
    jin_protect = []
    jin_pul = []
    qaroqchi = []
    konchi = []
    gazabdor_targets = []

    for a in valid_actions:
        actor = by_uid.get(a["actor_id"])
        if not actor or not actor.is_alive:
            continue
        actor_role_raw = await r.get(f"game:{game_id}:night:{night_num}:actor_role:{actor.user_id}")
        if not actor_role_raw:
            actor_role_raw = await r.get(f"game:{game_id}:player:{actor.user_id}:actor_role")
        role = actor_role_raw.decode() if isinstance(actor_role_raw, bytes) else actor_role_raw if actor_role_raw else actor.role
        tgt = a["target_id"]
        atype = a["action_type"]

        if atype == "komissar_shoot" and tgt:
            komissar_target = tgt
            komissar_actor_id = actor.user_id
        elif atype == "kill" and tgt:
            if role == RoleNames.DON:
                don_target = tgt
                don_actor_id = actor.user_id
            elif role == RoleNames.MAFIA:
                mafia_votes[tgt] = mafia_votes.get(tgt, 0) + 1
                mafia_voters[tgt] = actor.user_id
            elif role == RoleNames.QOTIL:
                qotil_target = tgt
                qotil_actor_id = actor.user_id
            elif role == RoleNames.OVCHI:
                ovchi_target = tgt
                ovchi_actor_id = actor.user_id
            elif role == RoleNames.KOMISSAR:
                komissar_target = tgt
                komissar_actor_id = actor.user_id
        elif atype == "investigate" and tgt:
            investigates.append((actor.user_id, tgt))
        elif atype == "heal" and tgt:
            healed.add(tgt)
        elif atype == "protect" and tgt:
            protected.add(tgt)
        elif atype == "zanjir" and tgt:
            zanjir.setdefault(actor.user_id, []).append(tgt)
        elif atype == "sehrgar" and tgt:
            swaps.setdefault(actor.user_id, []).append(tgt)
        elif atype == "xoyin" and tgt:
            xoyin[actor.user_id] = tgt
        elif atype == "advokat" and tgt:
            await r.set(f"game:{game_id}:adv_osish:{tgt}", 1, ex=3600)
        elif atype == "gazabdor" and tgt:
            gazabdor_targets.append(tgt)
        elif atype == "jin_hayot" and tgt:
            jin_protect.append(tgt)
        elif atype == "jin_pul" and tgt:
            jin_pul.append(tgt)
        elif atype == "jin_qotil" and tgt:
            jin_kill.append((tgt, actor.user_id))
        elif atype == "qaroqchi":
            qaroqchi.append((actor.user_id, tgt))
        elif atype == "konchi":
            konchi.append((actor.user_id, tgt))

    # Don tanlovi mafia ovozlaridan ustun. Don yurmasa — eng ko'p mafia ovozi.
    family_target = None
    family_killer = None
    family_actor_id = None
    if don_target:
        family_target = don_target
        family_killer = RoleNames.DON
        family_actor_id = don_actor_id
    elif mafia_votes:
        mx = max(mafia_votes.values())
        top = [t for t, c in mafia_votes.items() if c == mx]
        if len(top) == 1:
            family_target = top[0]
            family_killer = RoleNames.MAFIA
            family_actor_id = mafia_voters.get(top[0])

    protected |= set(jin_protect)

    # --- Jin pul in'omi ---
    for target in jin_pul:
        try:
            from models.user import User, Profile
            t_user = await User.filter(user_id=target).first()
            if t_user:
                t_prof = await Profile.filter(user=t_user).first()
                if t_prof:
                    # Yoki pul (85%) YOKI 1 olmos (15%)
                    if random.random() < 0.15:
                        t_prof.diamond += 1
                        await t_prof.save()
                        msg = "🧞 <b>Jin sizga 💎 1 olmos in'om etdi!</b>"
                    else:
                        # 1$ - 500$ random pul, 150$ dan baland pul olish imkoniyati pastroq (20%)
                        if random.random() < 0.80:
                            money_given = random.randint(1, 150)
                        else:
                            money_given = random.randint(151, 500)
                        t_prof.money += money_given
                        await t_prof.save()
                        msg = f"🧞 <b>Jin sizga 💰 {money_given}$ pul in'om etdi!</b>"
                    await _send_private(bot, target, msg)
        except Exception:
            pass

    # --- Jin hayot (himoya) xabari ---
    for target in jin_protect:
        try:
            await _send_private(bot, target, "🧞 <b>Jin sizni bu tun 🛡️ o'limdan saqlab qoldi!</b>")
        except Exception:
            pass

    # --- Sehrgar: ikki nishon rolini almashtirish ---
    for actor_uid, tgts in swaps.items():
        if len(tgts) >= 2:
            x, y = by_uid.get(tgts[0]), by_uid.get(tgts[1])
            if x and y:
                x.role, y.role = y.role, x.role
                await player_repo.save_player(x)
                await player_repo.save_player(y)

    # --- Kezuvchi: uxlash belgisini o'rnatish ---
    for uid in slept:
        sp = by_uid.get(uid)
        if sp:
            sp.is_sleep = True
            await player_repo.save_player(sp)
            await _send_private(bot, uid, get_msg(uid, "slept"))

    # --- O'lim nomzodlari ---
    dead_uids = []
    kill_sources: Dict[int, str] = {}
    qasoskor_revenge_queue = []

    kill_attempts = [
        (family_target, family_killer, family_actor_id),
        (qotil_target, RoleNames.QOTIL, qotil_actor_id),
        (ovchi_target, RoleNames.OVCHI, ovchi_actor_id),
        (komissar_target, RoleNames.KOMISSAR, komissar_actor_id),
    ]
    for jt, jactor in jin_kill:
        kill_attempts.append((jt, RoleNames.JIN, jactor))

    for target, killer, attacker_id in kill_attempts:
        if target and target not in healed and target not in protected:
            if target not in dead_uids:
                dead_uids.append(target)
            if killer:
                kill_sources[target] = killer

            # Qasoskor roli bo'lsa - hujum qilgan odamni qasosga yozib qo'yamiz
            target_p = by_uid.get(target)
            if target_p and target_p.role == RoleNames.QASOSKOR and attacker_id:
                qasoskor_revenge_queue.append((attacker_id, target))

    # --- Qasoskor qasosi: o'ziga hujum qilgan odamni o'ldiradi ---
    for attacker_id, qasoskor_id in qasoskor_revenge_queue:
        if attacker_id and attacker_id not in healed and attacker_id not in protected:
            if attacker_id not in dead_uids:
                dead_uids.append(attacker_id)
            kill_sources[attacker_id] = RoleNames.QASOSKOR

    # --- Zanjir: juftlikdan biri o'lsa, ikkinchisi ham ---
    for actor_uid, tgts in zanjir.items():
        if len(tgts) >= 2 and any(t in dead_uids for t in tgts[:2]):
            for t in tgts[:2]:
                if t not in dead_uids:
                    dead_uids.append(t)

    # --- Xoyin ---
    for actor_uid, tgt in xoyin.items():
        actor = by_uid.get(actor_uid)
        t = by_uid.get(tgt)
        if not actor or not t:
            continue
        if t.role in MAFIA_ROLES:
            actor.role = RoleNames.MAFIA
            await player_repo.save_player(actor)
            await _send_private(bot, actor_uid, get_msg(actor_uid, "xoyin_win"))
        else:
            actor.missed_nights = (getattr(actor, "missed_nights", 0) or 0) + 1
            await player_repo.save_player(actor)
            await _send_private(bot, actor_uid, get_msg(actor_uid, "xoyin_miss", miss=actor.missed_nights))
            if actor.missed_nights >= 3:
                dead_uids.append(actor_uid)

    # --- Jin qotillik ---
    for target in jin_kill:
        if target not in healed and target not in protected:
            dead_uids.append(target)
            kill_sources.setdefault(target, RoleNames.JIN)

    # --- Faol rollarning harakatsizligini tekshirish (Inactivity: 2 tun harakat qilmasa uxlab qolib vafot etadi) ---
    completed_key = f"game:{game_id}:night:{night_num}:completed_users"
    try:
        completed_uids_raw = await r.smembers(completed_key) or []
    except Exception:
        completed_uids_raw = []

    completed_uids = {int(x.decode() if isinstance(x, bytes) else x) for x in completed_uids_raw}
    for act in actions:
        if act.get("actor_id"):
            completed_uids.add(int(act["actor_id"]))

    inactivity_custom_texts = {}
    for p in players:
        # Faqat o'yinda tirik bo'lgan va tungi faol roli bor o'yinchilar
        if not p.is_alive or p.role not in NIGHT_ACTION_ROLES:
            continue

        # Kezuvchi yoki Jin tomonidan majburiy uxlatilgan bo'lsa uxlash hisoblanmaydi
        if getattr(p, "is_sleep", False):
            continue

        if p.user_id in completed_uids:
            p.missed_nights = 0
            await player_repo.save_player(p)
        else:
            p.missed_nights = (getattr(p, "missed_nights", 0) or 0) + 1
            await player_repo.save_player(p)

            if p.missed_nights >= 2:
                dead_uids.append(p.user_id)
                v_name = html.escape(names.get(p.user_id) or str(p.user_id))
                mention = f'<a href="tg://user?id={p.user_id}">{v_name}</a>'
                disp_role = role_display(p.role)
                inactivity_custom_texts[p.user_id] = (
                    f'Tunda kimdir {disp_role} {mention} ning "Men o\'yin payti boshqa uxlama-a-a-a-a-a-a-a-an!" deb qichqirganini eshitdi...'
                )

    # --- Qotilliklarni qo'llash ---
    for uid in dict.fromkeys(dead_uids):
        custom_txt = inactivity_custom_texts.get(uid)
        await _kill(game_id, uid, by_uid, bot, chat, names, killer_role=kill_sources.get(uid), custom_text=custom_txt)


    # --- Vorislik (Role succession) ---
    await _check_role_succession(by_uid, lang_map, bot)

    # --- Tekshiruv natijalari ---
    for actor_uid, tgt in investigates:
        actor = by_uid.get(actor_uid)
        t = by_uid.get(tgt)
        if not actor or not t:
            continue
        actor_role_raw = await r.get(f"game:{game_id}:night:{night_num}:actor_role:{actor.user_id}")
        if not actor_role_raw:
            actor_role_raw = await r.get(f"game:{game_id}:player:{actor.user_id}:actor_role")
        act_role = actor_role_raw.decode() if isinstance(actor_role_raw, bytes) else actor_role_raw if actor_role_raw else actor.role

        # Soxta Hujjat tekshiruvi
        shown = t.role
        try:
            from models.user import User, Profile
            target_db = await User.filter(user_id=t.user_id).first()
            if target_db:
                target_prof = await Profile.filter(user=target_db).first()
                if target_prof and target_prof.hujjat > 0 and target_prof.on_hujjat:
                    target_prof.hujjat -= 1
                    await target_prof.save()

                    tinch_pool = (
                        RoleNames.DAYDI, RoleNames.KEZUVCHI, RoleNames.DOKTOR,
                        RoleNames.FUQARO, RoleNames.HAMSHIRA, RoleNames.OMADLI,
                        RoleNames.JANOB, RoleNames.SERJANT, RoleNames.QORIQCHI, RoleNames.ZANJIR
                    )
                    alive_tinch_roles = [
                        p.role for p in players 
                        if p.is_alive and p.role in tinch_pool
                    ]
                    if alive_tinch_roles:
                        shown = random.choice(alive_tinch_roles)
                    else:
                        shown = RoleNames.FUQARO
                elif t.role == RoleNames.SOTQIN:
                    shown = RoleNames.MAFIA
            elif t.role == RoleNames.SOTQIN:
                shown = RoleNames.MAFIA
        except Exception:
            if t.role == RoleNames.SOTQIN:
                shown = RoleNames.MAFIA

        disp_shown = role_display(shown)
        if act_role == RoleNames.KOMISSAR:
            await _send_private(bot, actor_uid, get_msg(actor_uid, "investigate_res", name=names.get(tgt), role=disp_shown))
        elif act_role == RoleNames.JURNALIST:
            await _send_private(bot, actor_uid, get_msg(actor_uid, "jurnalist_res", name=names.get(tgt), role=disp_shown))
        elif act_role == RoleNames.AYGOQCHI:
            don = next((p for p in players if p.role == RoleNames.DON and p.is_alive), None)
            if don:
                await _send_private(bot, don.user_id, get_msg(don.user_id, "aygoqchi_res", name=names.get(tgt), role=disp_shown))

    # --- Konchi ---
    for actor_uid, kon_no in konchi:
        actor = by_uid.get(actor_uid)
        if not actor or not actor.is_alive:
            continue
        if random.random() < 0.25:
            await _kill(game_id, actor_uid, by_uid, bot, chat, names, reason=get_msg(actor_uid, "konchi_kill_reason"))
        else:
            await _send_private(bot, actor_uid, get_msg(actor_uid, "konchi_win", no=kon_no, count=random.choice([1, 2, 3])))

    # --- Gazabdor ogohlantirishi O'CHIRILGAN ---
    # Qoida: nishondagi odam G'azabkor uni nishonga olganini BILMASLIGI kerak.
    # Shuning uchun hech qanday warn xabar yuborilmaydi.
    # gazabdor_targets ro'yxati yig'iladi, lekin hech kimga xabar ketmaydi.

    # --- Himoyalarni tozalash ---
    await ActionService.clear_protections(game_id)


# ==================================================================
# KUNDUZGI OVOZ BERISH
# ==================================================================
async def send_day_votes(game_id: int, day_num: int, players: List, bot: Bot, chat: Chat) -> None:
    alive = await player_repo.get_alive_players(game_id)
    names = await _name_map([p.user_id for p in alive])
    for p in alive:
        if p.is_sleep:
            continue
        kb = InlineKeyboardBuilder()
        for q in alive:
            if q.user_id == p.user_id:
                continue
            kb.button(text=names.get(q.user_id), callback_data=f"nv|{game_id}|{day_num}|{q.user_id}")
        kb.button(text="🚷 O'tkazib yuborish", callback_data=f"nv|{game_id}|{day_num}|s")
        kb.adjust(1)
        day_head = "Kimga ovoz berasiz?"
        await _send_private(bot, p.user_id, day_head, kb.as_markup())


async def _check_role_succession(by_uid: Dict, lang_map: Dict, bot: Bot) -> None:
    """O'limlardan so'ng vorislik zanjirini tekshirish (Serjant, Hamshira, Mafia Don)."""
    alive_pl = [p for p in by_uid.values() if p.is_alive]
    don_alive = any(p.role == RoleNames.DON for p in alive_pl)
    kom_alive = any(p.role == RoleNames.KOMISSAR for p in alive_pl)
    dok_alive = any(p.role == RoleNames.DOKTOR for p in alive_pl)
    mafia_alive = any(p.role == RoleNames.MAFIA for p in alive_pl)
    serjant_alive = any(p.role == RoleNames.SERJANT for p in alive_pl)
    hamshira_alive = any(p.role == RoleNames.HAMSHIRA for p in alive_pl)

    if not don_alive and mafia_alive:
        suc = next(p for p in alive_pl if p.role == RoleNames.MAFIA)
        suc.role = RoleNames.DON
        await player_repo.save_player(suc)
        l_code = lang_map.get(suc.user_id, "uz")
        suc_msg = {
            "uz": f"🤵🏼 <b>Siz endi {role_display(RoleNames.DON)} bo'ldingiz!</b>",
            "ru": f"🤵🏼 <b>Теперь вы — {role_display(RoleNames.DON)}!</b>",
            "en": f"🤵🏼 <b>You are now the {role_display(RoleNames.DON)}!</b>",
            "tr": f"🤵🏼 <b>Artık {role_display(RoleNames.DON)} oldunuz!"
        }
        await _send_private(bot, suc.user_id, suc_msg.get(l_code, suc_msg["uz"]))

    if not kom_alive and serjant_alive:
        suc = next(p for p in alive_pl if p.role == RoleNames.SERJANT)
        suc.role = RoleNames.KOMISSAR
        await player_repo.save_player(suc)
        l_code = lang_map.get(suc.user_id, "uz")
        suc_msg = {
            "uz": f"👮‍♂️ <b>Siz endi {role_display(RoleNames.KOMISSAR)} bo'ldingiz!</b>",
            "ru": f"👮‍♂️ <b>Теперь вы — {role_display(RoleNames.KOMISSAR)}!</b>",
            "en": f"👮‍♂️ <b>You are now the {role_display(RoleNames.KOMISSAR)}!</b>",
            "tr": f"👮‍♂️ <b>Artık {role_display(RoleNames.KOMISSAR)} oldunuz!"
        }
        await _send_private(bot, suc.user_id, suc_msg.get(l_code, suc_msg["uz"]))

    if not dok_alive and hamshira_alive:
        suc = next(p for p in alive_pl if p.role == RoleNames.HAMSHIRA)
        suc.role = RoleNames.DOKTOR
        await player_repo.save_player(suc)
        l_code = lang_map.get(suc.user_id, "uz")
        suc_msg = {
            "uz": f"👨‍⚕️ <b>Siz endi {role_display(RoleNames.DOKTOR)} bo'ldingiz!</b>",
            "ru": f"👨‍⚕️ <b>Теперь вы — {role_display(RoleNames.DOKTOR)}!</b>",
            "en": f"👨‍⚕️ <b>You are now the {role_display(RoleNames.DOKTOR)}!</b>",
            "tr": f"👨‍⚕️ <b>Artık {role_display(RoleNames.DOKTOR)} oldunuz!"
        }
        await _send_private(bot, suc.user_id, suc_msg.get(l_code, suc_msg["uz"]))


def _mention_html(uid: int, names: Dict) -> str:
    name = html.escape(str(names.get(uid) or uid))
    return f'<a href="tg://user?id={int(uid)}">{name}</a>'


def lynch_confirm_kb(game_id: int, day_num: int, target_id: int, likes: int = 0, dislikes: int = 0):
    kb = InlineKeyboardBuilder()
    kb.button(text=f"👍 {likes}", callback_data=f"vl|{game_id}|{day_num}|{target_id}|1")
    kb.button(text=f"👎 {dislikes}", callback_data=f"vl|{game_id}|{day_num}|{target_id}|0")
    kb.adjust(2)
    return kb.as_markup()


async def process_day_votes(game_id: int, day_num: int, players: List, bot: Bot, chat: Chat, like_time: int = 30) -> None:
    all_players = await player_repo.get_all_players(game_id)
    names = await _name_map([p.user_id for p in all_players])
    from utils.i18n import get_chat_lang
    c_lang = await get_chat_lang(chat.chat_id)
    lang_map = await _user_lang_map([p.user_id for p in all_players], chat_id=chat.chat_id)
    by_uid = {p.user_id: p for p in all_players}
    votes = await VoteService.get_all_votes(game_id, day_num)

    counts: Dict[int, int] = {}
    for voter, target in votes.items():
        counts[target] = counts.get(target, 0) + 1

    no_vote_text = {
        "uz": "Bugun hech kim osilmadi.",
        "ru": "Сегодня никто не был повешен.",
        "en": "No one was lynched today.",
        "tr": "Bugün kimse asılmadı.",
        "kk": "Бүгін ешкім асылған жоқ."
    }.get(c_lang, "Bugun hech kim osilmadi.")

    tie_vote_text = {
        "uz": "Ovozlar teng bo'ldi — bugun hech kim osilmadi.",
        "ru": "Голоса разделились поровну — никто не повешен.",
        "en": "Tie vote — no one was lynched today.",
        "tr": "Oylar eşit — bugün kimse asılmadı.",
        "kk": "Дауыстар тең түсті — бүгін ешкім асылған жоқ."
    }.get(c_lang, "Ovozlar teng bo'ldi — bugun hech kim osilmadi.")

    if not counts:
        await bot.send_message(chat.chat_id, no_vote_text)
        return

    mx = max(counts.values())
    top = [t for t, c in counts.items() if c == mx]
    if len(top) != 1:
        await bot.send_message(chat.chat_id, tie_vote_text)
        return

    victim = by_uid.get(top[0])
    if not victim or not victim.is_alive:
        return

    mention = _mention_html(victim.user_id, names)
    confirm_text = {
        "uz": f"Rostdan ham {mention}ni osmoqchimisiz?",
        "ru": f"Вы действительно хотите повесить {mention}?",
        "en": f"Do you really want to lynch {mention}?",
        "tr": f"Gerçekten {mention} kişisini asmak istiyor musunuz?",
        "kk": f"Шынымен {mention} асуды қалайсыз ба?"
    }.get(c_lang, f"Rostdan ham {mention}ni osmoqchimisiz?")

    msg = await bot.send_message(
        chat.chat_id,
        confirm_text,
        parse_mode="HTML",
        reply_markup=lynch_confirm_kb(game_id, day_num, victim.user_id),
        disable_web_page_preview=True,
    )
    await r.set(f"game:{game_id}:phase:{day_num}:like_msg", str(msg.message_id), ex=7200)
    await r.set(f"game:{game_id}:phase:{day_num}:like_target", str(victim.user_id), ex=7200)

    await asyncio.sleep(max(0, int(like_time or 0)))

    game_state = await game_repo.load_game(game_id)
    if not game_state or not game_state.is_active:
        return

    # Tugmalarni yig'ish
    try:
        await bot.edit_message_reply_markup(chat.chat_id, msg.message_id, reply_markup=None)
    except Exception:
        pass

    tally = await VoteService.get_vote_like_results(game_id, day_num, victim.user_id)
    likes = tally.get("likes", 0)
    dislikes = tally.get("dislikes", 0)

    if likes <= dislikes:
        disagree_text = {
            "uz": f"Aholi kelisha olmadi ({likes} 👍 | {dislikes} 👎 )... Kelisha olmagani uchun hech kim osilmadi.",
            "ru": f"Жители не договорились ({likes} 👍 | {dislikes} 👎 )... Никто не повешен.",
            "en": f"Town couldn't agree ({likes} 👍 | {dislikes} 👎 )... No one was lynched.",
            "tr": f"Halk anlaşamadı ({likes} 👍 | {dislikes} 👎 )... Kimse asılmadı.",
            "kk": f"Тұрғындар келісе алмады ({likes} 👍 | {dislikes} 👎 )... Ешкім асылған жоқ."
        }.get(c_lang, f"Aholi kelisha olmadi ({likes} 👍 | {dislikes} 👎 )... Kelisha olmagani uchun hech kim osilmadi.")
        await bot.send_message(chat.chat_id, disagree_text)
        return

    if await r.get(f"game:{game_id}:adv_osish:{victim.user_id}"):
        adv_text = {
            "uz": f"⚖️ Advokat {mention} ni himoya qildi — u osilmadi!",
            "ru": f"⚖️ Адвокат защитил {mention} — его не повесили!",
            "en": f"⚖️ The Lawyer defended {mention} — lynch prevented!",
            "tr": f"⚖️ Avukat {mention} kişisini savundu — asılmadı!",
            "kk": f"⚖️ Адвокат {mention} қорғады — ол асылған жоқ!"
        }.get(c_lang, f"⚖️ Advokat {mention} ni himoya qildi — u osilmadi!")
        await bot.send_message(chat.chat_id, adv_text, parse_mode="HTML")
        return

    victim.is_alive = False
    victim.osildi = True
    victim.deaded_at = datetime.now(timezone.utc)
    await player_repo.save_player(victim)

    v_role_str = role_display(victim.role, lang=c_lang)
    lynch_res_text = {
        "uz": f"Ovoz berish natijalari:\n{likes} 👍  |  {dislikes} 👎\n\n{mention} kunduzgi yig'ilishda osildi!\nU edi {v_role_str}.",
        "ru": f"Результаты голосования:\n{likes} 👍  |  {dislikes} 👎\n\n{mention} был(а) повешен(а) на дневном собрании!\nОн(а) был(а) {v_role_str}.",
        "en": f"Vote results:\n{likes} 👍  |  {dislikes} 👎\n\n{mention} was lynched at the day meeting!\nThey were {v_role_str}.",
        "tr": f"Oylama sonuçları:\n{likes} 👍  |  {dislikes} 👎\n\n{mention} gündüz toplantısında asıldı!\nRolü {v_role_str}.",
        "kk": f"Дауыс беру нәтижелері:\n{likes} 👍  |  {dislikes} 👎\n\n{mention} күндізгі жиналыста асылды!\nОның ролі {v_role_str}."
    }.get(c_lang, f"Ovoz berish natijalari:\n{likes} 👍  |  {dislikes} 👎\n\n{mention} kunduzgi yig'ilishda osildi!\nU edi {v_role_str}.")

    await bot.send_message(
        chat.chat_id,
        lynch_res_text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    try:
        d_pm_msg = NIGHT_STRINGS.get(c_lang, NIGHT_STRINGS["uz"]).get("lynch_death_pm_msg", NIGHT_STRINGS["uz"]["death_pm_msg"])
        await bot.send_message(
            victim.user_id,
            d_pm_msg,
            parse_mode="HTML"
        )
    except Exception:
        pass
    await _check_role_succession(by_uid, lang_map, bot)

