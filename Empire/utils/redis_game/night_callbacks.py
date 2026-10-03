"""
Night/Day callback handlers (Redis).

Callback formatlari:
    na|{code}|{gid}|{ph}|{kind}|{target}   -> tungi harakat
    nv|{gid}|{day}|{target}                -> kunduzgi ovoz
    vl|{gid}|{day}|{target}|1/0            -> osish like/dislike
"""
import html

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.premium_emojis import role_display
from utils.role_names import RoleNames
from utils.redis_game.night_engine import (
    ROLE_CODE, ROLE_ACTION_TYPE, _name_map, lynch_confirm_kb
)
from utils.redis_game.services.action_service import ActionService
from utils.redis_game.services.vote_service import VoteService
from utils.redis_game.repositories.player_repository import player_repository as player_repo
from utils.redis_game.repositories.game_repository import game_repository as game_repo
from utils.database import redis_client as r

router = Router()
CODE_ROLE = {v: k for k, v in ROLE_CODE.items()}


def _redis_str(val):
    if val is None:
        return None
    return val.decode() if isinstance(val, bytes) else str(val)


def _choice_text(role: str, choice: str) -> str:
    header = role_display(role) if role else ""
    return f"{header}\nSizning tanlovingiz: {choice}"


async def _player_name(uid: int) -> str:
    names = await _name_map([int(uid)])
    return html.escape(names.get(int(uid)) or str(uid))


async def _player_mention(uid: int) -> str:
    name = await _player_name(uid)
    return f'<a href="tg://user?id={int(uid)}">{name}</a>'


async def _confirm_choice(call: CallbackQuery, role: str, choice: str) -> None:
    text = _choice_text(role, choice)
    await call.answer()
    try:
        await call.message.edit_text(text, parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(text)
        except Exception:
            pass


NIGHT_ACTION_ANNOUNCE = {
    RoleNames.DOKTOR: "{role} tungi navbatchilikka ketdi...",
    RoleNames.KOMISSAR: "{role} kimnidir tekshirishga ketdi...",
    RoleNames.DON: "{role} o'ljasini tanladi...",
    RoleNames.MAFIA: "{role} ovga chiqdi...",
    RoleNames.AYGOQCHI: "{role} kuzatuvga chiqdi...",
    RoleNames.QOTIL: "{role} qurbon izlab ketdi...",
    RoleNames.OVCHI: "{role} nishon oldi...",
    RoleNames.DAYDI: "{role} ko'chalarni kezmoqda...",
    RoleNames.KEZUVCHI: "{role} tungi sayrga chiqdi...",
    RoleNames.ZANJIR: "{role} zanjirlarini tashladi...",
    RoleNames.XOYIN: "{role} qidiruvga chiqdi...",
    RoleNames.QORIQCHI: "{role} postga chiqdi...",
    RoleNames.ADVOKAT: "{role} ish qog'ozlarini ochdi...",
    RoleNames.GAZABDOR: "{role} g'azabini yashirdi...",
    RoleNames.AFERIST: "{role} tungi rejasini tuzdi...",
    RoleNames.SEHRGAR: "{role} sehr tayyorlamoqda...",
    RoleNames.JURNALIST: "{role} ma'lumot yig'ishga chiqdi...",
    RoleNames.SOTQIN: "{role} jimjit harakat qildi...",
    RoleNames.KONCHI: "{role} shaxtaga tushdi...",
    RoleNames.QAROQCHI: "{role} o'lja izlab ketdi...",
    RoleNames.JIN: "{role} lampa yonida paydo bo'ldi...",
    RoleNames.REVERSER: "{role} taqdirni burishga chiqdi...",
}


async def _announce_night_action(call: CallbackQuery, gid: int, ph: int, uid: int, role: str, *, skipped: bool = False) -> None:
    """Guruhga tungi harakat e'lonini bir marta yuborish (nishon ochilmaydi)."""
    key = f"game:{gid}:night:{ph}:announced:{uid}"
    try:
        if not await r.set(key, "1", nx=True, ex=7200):
            return
        game_state = await game_repo.load_game(gid)
        if not game_state:
            return
        shown = role_display(role)
        if skipped:
            text = f"{shown} bugun dam oladi!"
        else:
            tmpl = NIGHT_ACTION_ANNOUNCE.get(role, "{role} tungi ishga chiqdi...")
            text = tmpl.format(role=shown)
        await call.bot.send_message(game_state.chat_id, text, parse_mode="HTML")
    except Exception:
        pass


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


async def _ensure_night_phase(call: CallbackQuery, gid: int, ph: int) -> bool:
    """Tungi tugmalar faqat joriy tun davomida ishlasin."""
    game_state = await game_repo.load_game(gid)
    if not game_state or not game_state.is_active or game_state.phase != "night":
        await call.answer("Bu harakat faqat tunda ishlaydi. Kunduzi oddiy ovoz bering.", show_alert=True)
        try:
            await call.message.edit_text("🌙 Tun tugadi. Kunduzi lichkadagi ovoz tugmalaridan foydalaning.")
        except Exception:
            try:
                await call.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        return False
    cur = await r.get(f"game:{gid}:night_num")
    if cur is not None and int(cur) != int(ph):
        await call.answer("Bu tun allaqachon tugagan.", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return False
    return True


@router.callback_query(F.data.startswith("na|"))
async def night_action_cb(call: CallbackQuery, bot=None):
    try:
        _, code, gid, ph, kind, target = call.data.split("|")
        gid, ph = int(gid), int(ph)
    except ValueError:
        await call.answer()
        return

    if not await _ensure_night_phase(call, gid, ph):
        return

    uid = call.from_user.id
    role = CODE_ROLE.get(code)
    if role is None:
        await call.answer()
        return

    if kind == "s":
        await _announce_night_action(call, gid, ph, uid, role, skipped=True)
        await _confirm_choice(call, role, "O'tkazib yuborish")
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
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, await _player_name(int(target)))
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
        first = _redis_str(await r.get(f"game:{gid}:tmp:{uid}:first"))
        if code == "rv":
            if first:
                await ActionService.save_action(gid, ph, uid, int(first), "reverser_source")
            await ActionService.save_action(gid, ph, uid, int(target), "reverser_target")
        else:
            atype = "zanjir" if code == "zj" else "sehrgar"
            if first:
                await ActionService.save_action(gid, ph, uid, int(first), atype)
            await ActionService.save_action(gid, ph, uid, int(target), atype)
        n1 = await _player_name(int(first)) if first else "?"
        n2 = await _player_name(int(target))
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, f"{n1}, {n2}")
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
        first = _redis_str(await r.get(f"game:{gid}:tmp:{uid}:first"))
        atype = {"jh": "jin_hayot", "jp": "jin_pul", "jq": "jin_qotil"}[kind]
        if first:
            await ActionService.save_action(gid, ph, uid, int(first), atype)
        gift = {"jh": "Hayot", "jp": "Pul", "jq": "Qotillik"}[kind]
        name = await _player_name(int(first)) if first else "?"
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, f"{name} ({gift})")
        return

    # Oddiy nishonli harakat
    if kind == "t":
        atype = ROLE_ACTION_TYPE.get(role, "action")
        await ActionService.save_action(gid, ph, uid, int(target), atype)
        await _set_last_visited(gid, uid, int(target))
        if code == "kn":
            choice = f"Kon {int(target)}"
        else:
            choice = await _player_name(int(target))
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, choice)
        return

    await call.answer()


async def _announce_day_vote(call: CallbackQuery, gid: int, uid: int, target_uid=None, *, skipped: bool = False) -> None:
    """Kunduzgi ovoz e'loni — har bir ovozchi kuniga faqat 1 marta e'lon qiladi."""
    try:
        game_state = await game_repo.load_game(gid)
        if not game_state:
            return
        day_raw = await r.get(f"game:{gid}:day_num")
        day_num = int(day_raw) if day_raw is not None else 0
        # Dedup: qayta-qayta bosganda guruhga spam ketmasin
        dup_key = f"game:{gid}:day:{day_num}:vote_announced:{uid}"
        try:
            first_time = await r.set(dup_key, "1", nx=True, ex=7200)
            if not first_time:
                return
        except Exception:
            pass
        voter = await _player_mention(uid)
        if skipped:
            text = f"🚷 {voter} hech kimni tanlamaslikka qaror qildi!"
        else:
            # KUNDUZI: faqat ismlar — rol nomi chiqmasligi shart.
            # Masalan: "Diyorbek - Valiga ovoz berdi"
            # (Tunda esa _announce_night_action rol nomi bilan e'lon qiladi:
            #  "Don o'ljasini tanladi...")
            target = await _player_mention(int(target_uid))
            text = f"{voter} - {target}ga ovoz berdi"
        await call.bot.send_message(
            game_state.chat_id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def _ensure_day_phase(call: CallbackQuery, gid: int, day: int) -> bool:
    """Kunduzgi ovoz faqat joriy kun davomida va tirik o'yinchidan qabul qilinadi."""
    game_state = await game_repo.load_game(gid)
    if not game_state or not game_state.is_active or game_state.phase != "day":
        await call.answer("Ovoz berish vaqti emas.", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return False
    cur = await r.get(f"game:{gid}:day_num")
    if cur is not None and int(cur) != int(day):
        await call.answer("Bu kun allaqachon tugagan.", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return False
    player = await player_repo.load_player(gid, call.from_user.id)
    if not player or not player.is_alive:
        await call.answer("Siz ovoz bera olmaysiz.", show_alert=True)
        return False
    return True


@router.callback_query(F.data.startswith("nv|"))
async def day_vote_cb(call: CallbackQuery, bot=None):
    try:
        _, gid, day, target = call.data.split("|")
        gid, day = int(gid), int(day)
    except ValueError:
        await call.answer()
        return

    if not await _ensure_day_phase(call, gid, day):
        return

    uid = call.from_user.id
    if target == "s":
        await VoteService.save_vote(gid, day, uid, 0)
        await _announce_day_vote(call, gid, uid, skipped=True)
        await call.answer("O'tkazib yuborildi")
        try:
            await call.message.edit_text("Kimga ovoz berasiz?\n\nSizning tanlovingiz: 🚷 O'tkazib yuborish")
        except Exception:
            pass
        return

    try:
        target_id = int(target)
    except (TypeError, ValueError):
        await call.answer()
        return

    if target_id == uid:
        await call.answer("O'zingizga ovoz bera olmaysiz.", show_alert=True)
        return

    try:
        target_player = await player_repo.load_player(gid, target_id)
        if not target_player or not target_player.is_alive:
            await call.answer("Bu o'yinchi allaqachon o'yindan chiqqan.", show_alert=True)
            return
    except Exception:
        pass

    await VoteService.save_vote(gid, day, uid, target_id)
    name = await _player_name(target_id)
    await _announce_day_vote(call, gid, uid, target_id)
    await call.answer(f"Siz {name}ga ovoz berdingiz")
    text = f"Kimga ovoz berasiz?\n\nSizning tanlovingiz: {name}"
    try:
        await call.message.edit_text(text, parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(text)
        except Exception:
            pass


@router.callback_query(F.data.startswith("vl|"))
async def vote_like_cb(call: CallbackQuery, bot=None):
    try:
        _, gid, day, tid, flag = call.data.split("|")
        gid, day, tid = int(gid), int(day), int(tid)
        is_like = flag == "1"
    except ValueError:
        await call.answer()
        return

    uid = call.from_user.id
    player = await player_repo.load_player(gid, uid)
    if not player or not player.is_alive:
        await call.answer("Siz ovoz bera olmaysiz.", show_alert=True)
        return

    expected = await r.get(f"game:{gid}:phase:{day}:like_target")
    if expected is not None and int(expected) != tid:
        await call.answer()
        return

    await VoteService.save_vote_like(gid, day, uid, tid, is_like)
    tally = await VoteService.get_vote_like_results(gid, day, tid)
    likes = tally.get("likes", 0)
    dislikes = tally.get("dislikes", 0)
    try:
        await call.message.edit_reply_markup(
            reply_markup=lynch_confirm_kb(gid, day, tid, likes, dislikes)
        )
    except Exception:
        pass
    await call.answer("👍" if is_like else "👎")

