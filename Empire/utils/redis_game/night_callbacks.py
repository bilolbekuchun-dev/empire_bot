"""
Night/Day callback handlers (Redis).

Callback formatlari:
    na|{code}|{gid}|{ph}|{kind}|{target}   -> tungi harakat
    nv|{gid}|{day}|{target}                -> kunduzgi ovoz
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.redis_game.night_engine import (
    ROLE_CODE, ROLE_ACTION_TYPE, _name_map
)
from utils.redis_game.services.action_service import ActionService
from utils.redis_game.services.vote_service import VoteService
from utils.redis_game.repositories.player_repository import player_repository as player_repo
from utils.database import redis_client as r

router = Router()
CODE_ROLE = {v: k for k, v in ROLE_CODE.items()}


async def _alive_targets(gid: int, exclude_uid=None):
    players = await player_repo.get_alive_players(gid)
    names = await _name_map([p.user_id for p in players])
    if isinstance(exclude_uid, (list, tuple, set)):
        excludes = {int(x) for x in exclude_uid if x is not None}
    elif exclude_uid is not None:
        excludes = {int(exclude_uid)}
    else:
        excludes = set()
    return players, [(p.user_id, names.get(p.user_id)) for p in players if p.user_id not in excludes]


async def _set_last_visited(gid, uid, target):
    try:
        await player_repo.update_player_field(gid, uid, "last_visited_user_id", int(target))
    except Exception:
        pass


@router.callback_query(F.data.startswith("na|"))
async def night_action_cb(call: CallbackQuery, bot=None):
    try:
        _, code, gid, ph, kind, target = call.data.split("|")
        gid, ph = int(gid), int(ph)
    except ValueError:
        await call.answer()
        return

    uid = call.from_user.id
    role = CODE_ROLE.get(code)
    if role is None:
        await call.answer()
        return

    if kind == "s":
        await call.answer("O'tkazib yuborildi")
        try:
            await call.message.edit_text("🚷 O'tkazib yubordingiz.")
        except Exception:
            pass
        return

    # Komissar: rejim tugmasi (target==0) -> nishon ro'yxati
    if code == "ko" and kind in ("c", "k") and int(target) == 0:
        _p, tg = await _alive_targets(gid, exclude_uid=uid)
        kb = InlineKeyboardBuilder()
        for tuid, label in tg:
            kb.button(text=label, callback_data=f"na|ko|{gid}|{ph}|{kind}|{tuid}")
        kb.button(text="🚷 O'tkazib yuborish", callback_data=f"na|ko|{gid}|{ph}|s|0")
        kb.adjust(1)
        title = "🔍 Tekshirish uchun nishon:" if kind == "c" else "🔫 O'ldirish uchun nishon:"
        try:
            await call.message.edit_text(title, reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return

    # Komissar: nishon tanlandi
    if code == "ko" and kind in ("c", "k") and int(target) != 0:
        atype = "investigate" if kind == "c" else "kill"
        await ActionService.save_action(gid, ph, uid, int(target), atype)
        await _set_last_visited(gid, uid, int(target))
        await call.answer("✅ Qabul qilindi")
        try:
            await call.message.edit_text("✅ Tanlov qabul qilindi")
        except Exception:
            pass
        return

    # Zanjir / Sehrgar / Reverser: 1-nishon -> 2-nishon
    if code in ("zj", "se", "rv") and kind == "t":
        await ActionService.clear_player_actions(gid, ph, uid)
        await r.set(f"game:{gid}:tmp:{uid}:first", str(target), ex=3600)
        exclude = {uid, int(target)} if code == "rv" else None
        _p, tg = await _alive_targets(gid, exclude_uid=exclude)
        kb = InlineKeyboardBuilder()
        for tuid, label in tg:
            kb.button(text=label, callback_data=f"na|{code}|{gid}|{ph}|2|{tuid}")
        kb.button(text="🚷 O'tkazib yuborish", callback_data=f"na|{code}|{gid}|{ph}|s|0")
        kb.adjust(1)
        title = "Endi 2-o'yinchi (yangi nishon)ni tanlang:" if code == "rv" else "Endi 2-nishonni tanlang:"
        try:
            await call.message.edit_text(title, reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return
    if code in ("zj", "se", "rv") and kind == "2":
        await ActionService.clear_player_actions(gid, ph, uid)
        first = await r.get(f"game:{gid}:tmp:{uid}:first")
        if code == "rv":
            if first:
                await ActionService.save_action(gid, ph, uid, int(first), "reverser_source")
            await ActionService.save_action(gid, ph, uid, int(target), "reverser_target")
        else:
            atype = "zanjir" if code == "zj" else "sehrgar"
            if first:
                await ActionService.save_action(gid, ph, uid, int(first), atype)
            await ActionService.save_action(gid, ph, uid, int(target), atype)
        await call.answer("✅ Qabul qilindi")
        try:
            await call.message.edit_text("✅ Tanlov qabul qilindi")
        except Exception:
            pass
        return


    # Jin: nishon -> sovg'a turi
    if code == "ji" and kind == "t":
        await ActionService.clear_player_actions(gid, ph, uid)
        await r.set(f"game:{gid}:tmp:{uid}:first", str(target), ex=3600)
        kb = InlineKeyboardBuilder()
        kb.button(text="✨ Hayot", callback_data=f"na|ji|{gid}|{ph}|jh|0")
        kb.button(text="💰 Pul", callback_data=f"na|ji|{gid}|{ph}|jp|0")
        kb.button(text="💀 Qotillik", callback_data=f"na|ji|{gid}|{ph}|jq|0")
        kb.adjust(1)
        try:
            await call.message.edit_text("Sovg'a turini tanlang:", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return
    if code == "ji" and kind in ("jh", "jp", "jq"):
        await ActionService.clear_player_actions(gid, ph, uid)
        first = await r.get(f"game:{gid}:tmp:{uid}:first")
        atype = {"jh": "jin_hayot", "jp": "jin_pul", "jq": "jin_qotil"}[kind]
        if first:
            await ActionService.save_action(gid, ph, uid, int(first), atype)
        await call.answer("✅ Qabul qilindi")
        try:
            await call.message.edit_text("✅ Tanlov qabul qilindi")
        except Exception:
            pass
        return

    # Oddiy nishonli harakat
    if kind == "t":
        atype = ROLE_ACTION_TYPE.get(role, "action")
        await ActionService.save_action(gid, ph, uid, int(target), atype)
        await _set_last_visited(gid, uid, int(target))
        await call.answer("✅ Qabul qilindi")
        try:
            await call.message.edit_text("✅ Tanlov qabul qilindi")
        except Exception:
            pass
        return

    await call.answer()


@router.callback_query(F.data.startswith("nv|"))
async def day_vote_cb(call: CallbackQuery, bot=None):
    try:
        _, gid, day, target = call.data.split("|")
        gid, day = int(gid), int(day)
    except ValueError:
        await call.answer()
        return

    uid = call.from_user.id
    if target == "s":
        await call.answer("O'tkazib yuborildi")
        try:
            await call.message.edit_text("🚷 O'kazib yubordingiz.")
        except Exception:
            pass
        return

    await VoteService.save_vote(gid, day, uid, int(target))
    await call.answer("✅ Ovoz qabul qilindi")
    try:
        await call.message.edit_text("✅ Ovozingiz qabul qilindi.")
    except Exception:
        pass

