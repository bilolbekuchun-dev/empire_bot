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
}

# Qotillik harakatlari (uyqu/tegilmagan bo'lsa o'ldiradi)
KILL_ACTIONS = {"kill"}

MAFIA_ROLES = {RoleNames.DON, RoleNames.MAFIA, RoleNames.AYGOQCHI}


# ------------------------------------------------------------------
# Yordamchi
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
    # Yangi tun boshlanishida uxlab yotganlarni uyg'otamiz
    for p in players:
        if getattr(p, "is_sleep", False):
            p.is_sleep = False
            await player_repo.save_player(p)

    names = await _name_map([p.user_id for p in players])
    alive = [p for p in players if p.is_alive]

    for p in alive:
        role = p.role
        uid = p.user_id
        code = ROLE_CODE.get(role)

        # Passiv rollar uchun oddiy xabar
        if code is None:
            await _send_private(
                bot, uid,
                f"🌙 <b>Kecha bo'ldi.</b>\nRolingiz: {role_display(role)}\n\n"
                f"Bu tunda maxsus harakatingiz yo'q — tonggacha kuting."
            )
            continue

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
            kb.button(text="🔍 Tekshirish", callback_data=_cb("ko", game_id, night_num, "c", 0))
            kb.button(text="🔫 O'ldirish", callback_data=_cb("ko", game_id, night_num, "k", 0))
            kb.button(text="🚷 O'tkazib yuborish", callback_data=_cb("ko", game_id, night_num, "s", 0))
            kb.adjust(2, 1)
            await _send_private(
                bot, uid,
                "🕵🏼 <b>Komissar</b>, nima qilasiz?",
                kb.as_markup()
            )
            continue

        # --- Konchi: kon tanlash ---
        if role == RoleNames.KONCHI:
            kb = InlineKeyboardBuilder()
            for i in range(1, 6):
                kb.button(text=f"⛏ Kon {i}", callback_data=_cb("kn", game_id, night_num, "t", i))
            kb.button(text="🚷 O'tkazib yuborish", callback_data=_cb("kn", game_id, night_num, "s", 0))
            kb.adjust(5, 1)
            await _send_private(
                bot, uid,
                "👷🏻‍♂️ <b>Konchi</b>, qaysi kondan qazasiz? (ba'zilarida tuzoq bor!)",
                kb.as_markup()
            )
            continue

        # --- Qaroqchi: nishon tanlash ---
        if role == RoleNames.QAROQCHI:
            await _send_private(bot, uid, "⚔️ <b>Qaroqchi</b>, kimni nishonga olasiz?",
                                _target_kb("qa", game_id, night_num, mk_targets))
            continue

        # --- Jin: tanlov menyusi (nishon keyin) ---
        if role == RoleNames.JIN:
            await _send_private(
                bot, uid,
                "🧞 <b>Jin</b>, nishonni tanlang — so'ng unga sovg'a turini berasiz.",
                _target_kb("ji", game_id, night_num, mk_targets)
            )
            continue

        # --- Zanjir / Sehrgar: 2 nishonli (1-qadam) ---
        if role in (RoleNames.ZANJIR, RoleNames.SEHRGAR):
            tcode = "zj" if role == RoleNames.ZANJIR else "se"
            label = "⛓ <b>Zanjir</b>: bog'lash uchun <b>1-nishon</b>ni tanlang." if role == RoleNames.ZANJIR \
                else "🧙 <b>Sehrgar</b>: almashtirish uchun <b>1-nishon</b>ni tanlang."
            await _send_private(bot, uid, label, _target_kb(tcode, game_id, night_num, mk_targets))
            continue

        # --- Oddiy bitta nishonli harakatlar ---
        label = f"🌙 {role_display(role)} — nishonni tanlang:"
        await _send_private(bot, uid, label, _target_kb(code, game_id, night_num, mk_targets))


# ==================================================================
# NATIJALARNI QAYTA ISHLASH
# ==================================================================
async def _kill(game_id: int, uid: int, by_uid: Dict, bot: Bot, chat: Chat, names: Dict,
                reason: str = "") -> Optional[object]:
    p = by_uid.get(uid)
    if not p or not p.is_alive:
        return None
    p.is_alive = False
    p.deaded_at = datetime.now(timezone.utc)
    await player_repo.save_player(p)
    try:
        suffix = f"\n{reason}" if reason else ""
        await bot.send_message(
            chat.chat_id,
            f"💀 {names.get(uid)} o'ldirildi.{suffix}\nU edi — <b>{role_display(p.role)}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return p


async def process_night_results(game_id: int, night_num: int, players: List, bot: Bot, chat: Chat) -> None:
    """Tungi harakatlarni qo'llash: o'ldirish, davolash, himoya, tekshiruv va h.k."""
    names = await _name_map([p.user_id for p in players])
    by_uid = {p.user_id: p for p in players}
    actions = await ActionService.get_phase_actions(game_id, night_num)

    mafia_votes: Dict[int, int] = {}
    qotil_target = None
    ovchi_target = None
    healed, protected, slept = set(), set(), set()
    zanjir: Dict[int, list] = {}
    swaps: Dict[int, list] = {}
    xoyin: Dict[int, int] = {}
    investigates = []
    jin_kill = []
    jin_protect = []
    qaroqchi = []
    konchi = []
    gazabdor_targets = []

    for a in actions:
        actor = by_uid.get(a["actor_id"])
        if not actor:
            continue
        role = actor.role
        tgt = a["target_id"]
        atype = a["action_type"]

        if role in MAFIA_ROLES and atype == "kill" and tgt:
            mafia_votes[tgt] = mafia_votes.get(tgt, 0) + 1
        elif role == RoleNames.QOTIL and atype == "kill" and tgt:
            qotil_target = tgt
        elif role == RoleNames.OVCHI and atype == "kill" and tgt:
            ovchi_target = tgt
        elif atype == "heal" and tgt:
            healed.add(tgt)
        elif atype == "protect" and tgt:
            protected.add(tgt)
        elif atype == "sleep" and tgt:
            slept.add(tgt)
        elif atype == "zanjir" and tgt:
            zanjir.setdefault(actor.user_id, []).append(tgt)
        elif atype == "sehrgar" and tgt:
            swaps.setdefault(actor.user_id, []).append(tgt)
        elif atype == "xoyin" and tgt:
            xoyin[actor.user_id] = tgt
        elif atype == "investigate" and tgt:
            investigates.append((actor.user_id, tgt))
        elif atype == "advokat" and tgt:
            await r.set(f"game:{game_id}:adv_osish:{tgt}", 1, ex=3600)
        elif atype == "gazabdor" and tgt:
            gazabdor_targets.append(tgt)
        elif atype == "jin_hayot" and tgt:
            jin_protect.append(tgt)
        elif atype == "jin_qotil" and tgt:
            jin_kill.append(tgt)
        elif atype == "qaroqchi":
            qaroqchi.append((actor.user_id, tgt))
        elif atype == "konchi":
            konchi.append((actor.user_id, tgt))

    mafia_target = None
    if mafia_votes:
        mx = max(mafia_votes.values())
        top = [t for t, c in mafia_votes.items() if c == mx]
        mafia_target = top[0] if len(top) == 1 else None

    protected |= set(jin_protect)

    # --- Sehrgar: ikki nishon rolini almashtirish ---
    for actor_uid, tgts in swaps.items():
        if len(tgts) >= 2:
            x, y = by_uid.get(tgts[0]), by_uid.get(tgts[1])
            if x and y:
                x.role, y.role = y.role, x.role
                await player_repo.save_player(x)
                await player_repo.save_player(y)

    # --- Kezuvchi: uxlash ---
    for uid in slept:
        sp = by_uid.get(uid)
        if sp:
            sp.is_sleep = True
            await player_repo.save_player(sp)
            await _send_private(bot, uid, "💤 Sizni uyqu dorisi bilan uxlatishdi — bu tun uxlaysiz.")

    # --- O'lim nomzodlari ---
    dead_uids = []
    for target in (mafia_target, qotil_target, ovchi_target):
        if target and target not in healed and target not in protected:
            dead_uids.append(target)

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
            await _send_private(bot, actor_uid, "👺 Siz mafiyani topdingiz va endi mafiyaga aylandingiz!")
        else:
            actor.missed_nights = (getattr(actor, "missed_nights", 0) or 0) + 1
            await player_repo.save_player(actor)
            await _send_private(bot, actor_uid, f"👺 Topa olmadingiz ({actor.missed_nights}/3).")
            if actor.missed_nights >= 3:
                dead_uids.append(actor_uid)

    # --- Jin qotillik ---
    for target in jin_kill:
        if target not in healed and target not in protected:
            dead_uids.append(target)

    # --- Qotilliklarni qo'llash ---
    for uid in dict.fromkeys(dead_uids):
        await _kill(game_id, uid, by_uid, bot, chat, names)

    # --- Tekshiruv natijalari ---
    for actor_uid, tgt in investigates:
        actor = by_uid.get(actor_uid)
        t = by_uid.get(tgt)
        if not actor or not t:
            continue
        shown = RoleNames.MAFIA if t.role == RoleNames.SOTQIN else t.role
        if actor.role == RoleNames.KOMISSAR:
            await _send_private(bot, actor_uid, f"🔍 Natija: {names.get(tgt)} → <b>{role_display(shown)}</b>")
        elif actor.role == RoleNames.JURNALIST:
            await _send_private(bot, actor_uid, f"📰 Ma'lumot: {names.get(tgt)} → <b>{role_display(shown)}</b>")
        elif actor.role == RoleNames.AYGOQCHI:
            don = next((p for p in players if p.role == RoleNames.DON and p.is_alive), None)
            if don:
                await _send_private(bot, don.user_id, f"🦇 Ayg'oqchi: {names.get(tgt)} → <b>{role_display(shown)}</b>")

    # --- Konchi ---
    for actor_uid, kon_no in konchi:
        actor = by_uid.get(actor_uid)
        if not actor or not actor.is_alive:
            continue
        if random.random() < 0.25:
            await _kill(game_id, actor_uid, by_uid, bot, chat, names, reason="Kon tuzog'iga tushdi.")
        else:
            await _send_private(bot, actor_uid, f"⛏ Kon {kon_no}: {random.choice([1, 2, 3])} 💎 qazib oldingiz!")

    # --- Gazabdor ogohlantirishi ---
    for uid in gazabdor_targets:
        if by_uid.get(uid):
            await _send_private(bot, uid, "🧌 Sizni G'azabkor nishonga oldi!")

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
        await _send_private(bot, p.user_id, "🗳 <b>Kun</b> — kimni osamiz?", kb.as_markup())


async def process_day_votes(game_id: int, day_num: int, players: List, bot: Bot, chat: Chat) -> None:
    all_players = await player_repo.get_all_players(game_id)
    names = await _name_map([p.user_id for p in all_players])
    by_uid = {p.user_id: p for p in all_players}
    votes = await VoteService.get_all_votes(game_id, day_num)

    counts: Dict[int, int] = {}
    for voter, target in votes.items():
        counts[target] = counts.get(target, 0) + 1

    if not counts:
        await bot.send_message(chat.chat_id, "🗳 Bugun hech kim osilmadi.")
        return

    mx = max(counts.values())
    top = [t for t, c in counts.items() if c == mx]
    if len(top) != 1:
        await bot.send_message(chat.chat_id, "🗳 Ovozlar teng bo'ldi — bugun hech kim osilmadi.")
        return

    victim = by_uid.get(top[0])
    if not victim or not victim.is_alive:
        return

    if await r.get(f"game:{game_id}:adv_osish:{victim.user_id}"):
        await bot.send_message(chat.chat_id, f"⚖️ Advokat {names.get(victim.user_id)} ni himoya qildi — u osilmadi!")
        return

    victim.is_alive = False
    victim.osildi = True
    victim.deaded_at = datetime.now(timezone.utc)
    await player_repo.save_player(victim)
    await bot.send_message(
        chat.chat_id,
        f"🪢 {names.get(victim.user_id)} xalq tomonidan osildi!\nU edi — <b>{role_display(victim.role)}</b>",
        parse_mode="HTML"
    )

