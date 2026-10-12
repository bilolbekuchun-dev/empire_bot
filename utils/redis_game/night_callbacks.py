"""
Night/Day callback handlers (Redis).

Callback formatlari:
    na|{code}|{gid}|{ph}|{kind}|{target}   -> tungi harakat
    nv|{gid}|{day}|{target}                -> kunduzgi ovoz
    vl|{gid}|{day}|{target}|1/0            -> osish like/dislike
"""
import html
import asyncio
from typing import Optional

from aiogram import Router, F, Bot
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


def _choice_text(role: str, choice: str, lang: str = "uz") -> str:
    header = role_display(role) if role else ""
    fmt = {
        "uz": "Sizning tanlovingiz: {choice}",
        "ru": "Ваш выбор: {choice}",
        "en": "Your choice: {choice}",
        "tr": "Seçiminiz: {choice}",
        "kk": "Сіздің таңдауыңыз: {choice}"
    }.get(lang, "Sizning tanlovingiz: {choice}")
    return f"{header}\n{fmt.format(choice=choice)}"


async def _player_name(uid: int) -> str:
    names = await _name_map([int(uid)])
    return html.escape(names.get(int(uid)) or str(uid))


async def _player_mention(uid: int) -> str:
    name = await _player_name(uid)
    return f'<a href="tg://user?id={int(uid)}">{name}</a>'


async def _get_go_group_markup(bot: Bot, gid: int, lang: str = "uz"):
    if not gid or not bot:
        return None
    try:
        from utils.telegram_utils import get_chat_join_link
        from keyboards.game_keyboard import go_group_button
        link = await get_chat_join_link(bot, gid)
        if link:
            return go_group_button(link, lang=lang)
    except Exception:
        pass
    return None


async def _confirm_choice(call: CallbackQuery, role: str, choice: str, lang: str = "uz", gid: int = None) -> None:
    text = _choice_text(role, choice, lang=lang)
    await call.answer()
    reply_markup = await _get_go_group_markup(call.bot, gid, lang=lang)

    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception:
        try:
            await call.message.edit_text(text, reply_markup=reply_markup)
        except Exception:
            pass


NIGHT_ACTION_ANNOUNCE = {
    "uz": {
        RoleNames.DOKTOR: "{role} tungi navbatchilikka ketdi...",
        RoleNames.KOMISSAR: "{role} kimnidir tekshirishga ketdi...",
        RoleNames.DON: "{role} o'ljasini tanladi...",
        RoleNames.MAFIA: "{role} ovga chiqdi...",
        RoleNames.QOTIL: "{role} qurbon izlab ketdi...",
        RoleNames.OVCHI: "{role} nishon oldi...",
        RoleNames.DAYDI: "{role} ko'chalarni kezmoqda...",
        RoleNames.KEZUVCHI: "{role} tungi sayrga chiqdi...",
        RoleNames.ZANJIR: "{role} zanjirlarini tashladi...",
        RoleNames.QORIQCHI: "{role} postga chiqdi...",
        RoleNames.ADVOKAT: "{role} ish qog'ozlarini ochdi...",
        RoleNames.GAZABDOR: "{role} g'azabini yashirdi...",
        RoleNames.AFERIST: "{role} tungi rejasini tuzdi...",
        RoleNames.SEHRGAR: "{role} sehr tayyorlamoqda...",
        RoleNames.KONCHI: "{role} shaxtaga tushdi...",
        RoleNames.QAROQCHI: "{role} o'lja izlab ketdi...",
        RoleNames.JIN: "{role} o'z chirog'idan tashqariga chiqdi!",
    },
    "ru": {
        RoleNames.DOKTOR: "{role} отправился(лась) на ночное дежурство...",
        RoleNames.KOMISSAR: "{role} отправился(лась) на проверку...",
        RoleNames.DON: "{role} выбрал(а) жертву...",
        RoleNames.MAFIA: "{role} вышел(ла) на охоту...",
        RoleNames.QOTIL: "{role} ищет жертву...",
        RoleNames.OVCHI: "{role} взял(а) на прицел...",
        RoleNames.DAYDI: "{role} бродит по улицам...",
        RoleNames.KEZUVCHI: "{role} вышел(ла) на ночную прогулку...",
        RoleNames.ZANJIR: "{role} раскинул(а) цепи...",
        RoleNames.QORIQCHI: "{role} встал(а) на пост...",
        RoleNames.ADVOKAT: "{role} открыл(а) материалы дела...",
        RoleNames.GAZABDOR: "{role} затаил(а) злобу...",
        RoleNames.AFERIST: "{role} строит ночные планы...",
        RoleNames.SEHRGAR: "{role} готовит заклинание...",
        RoleNames.KONCHI: "{role} спустился(лась) в шахту...",
        RoleNames.QAROQCHI: "{role} отправился(лась) на поиски добычи...",
        RoleNames.JIN: "{role} вышел(ла) из своей лампы!",
    },
    "en": {
        RoleNames.DOKTOR: "{role} went on night duty...",
        RoleNames.KOMISSAR: "{role} went to investigate...",
        RoleNames.DON: "{role} chose a target...",
        RoleNames.MAFIA: "{role} went hunting...",
        RoleNames.QOTIL: "{role} is looking for a victim...",
        RoleNames.OVCHI: "{role} locked target...",
        RoleNames.DAYDI: "{role} is roaming the streets...",
        RoleNames.KEZUVCHI: "{role} went for a night walk...",
        RoleNames.ZANJIR: "{role} cast the chains...",
        RoleNames.QORIQCHI: "{role} stood guard...",
        RoleNames.ADVOKAT: "{role} opened the case files...",
        RoleNames.GAZABDOR: "{role} harbored anger...",
        RoleNames.AFERIST: "{role} is scheming...",
        RoleNames.SEHRGAR: "{role} is preparing a spell...",
        RoleNames.KONCHI: "{role} went into the mine...",
        RoleNames.QAROQCHI: "{role} went searching for loot...",
        RoleNames.JIN: "{role} emerged from the lamp!",
    },
    "tr": {
        RoleNames.DOKTOR: "{role} gece nöbetine çıktı...",
        RoleNames.KOMISSAR: "{role} birini kontrol etmeye gitti...",
        RoleNames.DON: "{role} kurbanını seçti...",
        RoleNames.MAFIA: "{role} ava çıktı...",
        RoleNames.QOTIL: "{role} kurban arıyor...",
        RoleNames.OVCHI: "{role} hedef aldı...",
        RoleNames.DAYDI: "{role} sokaklarda geziyor...",
        RoleNames.KEZUVCHI: "{role} gece yürüyüşüne çıktı...",
        RoleNames.ZANJIR: "{role} zincirlerini attı...",
        RoleNames.QORIQCHI: "{role} nöbete durdu...",
        RoleNames.ADVOKAT: "{role} dava dosyasını açtı...",
        RoleNames.GAZABDOR: "{role} öfkesini gizledi...",
        RoleNames.AFERIST: "{role} gece planını yaptı...",
        RoleNames.SEHRGAR: "{role} büyü hazırlıyor...",
        RoleNames.KONCHI: "{role} madene indi...",
        RoleNames.QAROQCHI: "{role} ganimet aramaya gitti...",
        RoleNames.JIN: "{role} lambasından dışarı çıktı!",
    },
    "kk": {
        RoleNames.DOKTOR: "{role} түнгі кезекшілікке кетті...",
        RoleNames.KOMISSAR: "{role} біреуді тексеруге кетті...",
        RoleNames.DON: "{role} олжасын таңдады...",
        RoleNames.MAFIA: "{role} аңшылыққа шықты...",
        RoleNames.QOTIL: "{role} құрбан іздеп кетті...",
        RoleNames.OVCHI: "{role} нысанаға алды...",
        RoleNames.DAYDI: "{role} көше аралап жүр...",
        RoleNames.KEZUVCHI: "{role} түнгі серуенге шықты...",
        RoleNames.ZANJIR: "{role} шынжырларын тастады...",
        RoleNames.QORIQCHI: "{role} бекетке тұрды...",
        RoleNames.ADVOKAT: "{role} іс қағаздарын ашты...",
        RoleNames.GAZABDOR: "{role} ашуын жасырды...",
        RoleNames.AFERIST: "{role} түнгі жоспарын құрды...",
        RoleNames.SEHRGAR: "{role} сиқыр дайындауда...",
        RoleNames.KONCHI: "{role} шахтаға түсті...",
        RoleNames.QAROQCHI: "{role} олжа іздеп кетті...",
        RoleNames.JIN: "{role} өз шамынан сыртқа шықты!",
    }
}


async def _announce_night_action(call: CallbackQuery, gid: int, ph: int, uid: int, role: str, *, skipped: bool = False, kind: str = None) -> None:
    """Guruhga tungi harakat e'lonini bir marta yuborish (nishon ochilmaydi)."""
    if role == RoleNames.MAFIA or ("mafia" in str(role).lower() and "don" not in str(role).lower()):
        return

    key = f"game:{gid}:night:{ph}:announced:{uid}"
    try:
        if not await r.set(key, "1", nx=True, ex=7200):
            return
        game_state = await game_repo.load_game(gid)
        if not game_state:
            return
        from utils.i18n import get_chat_lang
        chat_lang = await get_chat_lang(game_state.chat_id)
        shown = role_display(role)
        dict_by_lang = NIGHT_ACTION_ANNOUNCE.get(chat_lang, NIGHT_ACTION_ANNOUNCE["uz"])
        if skipped:
            skip_ann = {
                "uz": f"{shown} bugun dam oladi!",
                "ru": f"{shown} сегодня отдыхает!",
                "en": f"{shown} is resting tonight!",
                "tr": f"{shown} bugün dinleniyor!",
                "kk": f"{shown} бүгін демалады!"
            }
            text = skip_ann.get(chat_lang, skip_ann["uz"])
        elif role == RoleNames.KOMISSAR and kind in ("k", "otish", "komissar_shoot"):
            shoot_ann = {
                "uz": f"{shown} pistoletini o'qladi...",
                "ru": f"{shown} зарядил(а) пистолет...",
                "en": f"{shown} loaded the gun...",
                "tr": f"{shown} silahını doldurdu...",
                "kk": f"{shown} тапаншасын оқтады..."
            }
            text = shoot_ann.get(chat_lang, shoot_ann["uz"])
        elif role == RoleNames.KOMISSAR and kind in ("c", "tek", "investigate"):
            check_ann = {
                "uz": f"{shown} kimnidir tekshirishga ketdi...",
                "ru": f"{shown} отправился(лась) на проверку...",
                "en": f"{shown} went to investigate...",
                "tr": f"{shown} birini kontrol etmeye gitti...",
                "kk": f"{shown} біреуді тексеруге кетті..."
            }
            text = check_ann.get(chat_lang, check_ann["uz"])
        else:
            tmpl = dict_by_lang.get(role, "{role} tungi ishga chiqdi...")
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


async def _mark_action_completed(gid: int, ph: int, uid: int):
    try:
        key = f"game:{gid}:night:{ph}:completed_users"
        await r.sadd(key, str(uid))
        await r.expire(key, 3600)
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


async def _notify_mafia_team_vote(bot: Bot, gid: int, voter_uid: int, target_uid: int):
    try:
        from utils.redis_game.night_engine import MAFIA_ROLES
        players = await player_repo.get_alive_players(gid)
        mafia_team = [p for p in players if p.role in MAFIA_ROLES]

        voter_name = await _player_name(voter_uid)
        target_name = await _player_name(target_uid)

        vote_msg = f"<b>{voter_name}</b> - <b>{target_name}</b> ga ovoz berdi"

        for m_player in mafia_team:
            try:
                await bot.send_message(m_player.user_id, vote_msg, parse_mode="HTML")
            except Exception:
                pass
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

    if not await _ensure_night_phase(call, gid, ph):
        return

    uid = call.from_user.id
    role = CODE_ROLE.get(code)
    if role is None:
        await call.answer()
        return

    game_state = await game_repo.load_game(gid)
    from utils.i18n import get_chat_lang
    chat_lang = await get_chat_lang(game_state.chat_id) if game_state else "uz"

    skip_text = {
        "uz": "O'tkazib yuborish",
        "ru": "Пропустить",
        "en": "Skip",
        "tr": "Pas geç",
        "kk": "Өткізіп жіберу"
    }.get(chat_lang, "O'tkazib yuborish")

    if kind == "s":
        await _announce_night_action(call, gid, ph, uid, role, skipped=True)
        await _confirm_choice(call, role, skip_text, lang=chat_lang, gid=gid)
        await _mark_action_completed(gid, ph, uid)
        return

    # Komissar: Ortga qaytish (rejim tanlash menyusi)
    if code == "ko" and kind == "b":
        history_key = f"game:{gid}:komissar_history"
        history_raw = await r.lrange(history_key, 0, -1) or []
        hist_lines = [h.decode() if isinstance(h, bytes) else str(h) for h in history_raw]

        check_btn = {"uz": "🔍 Tekshirish", "ru": "🔍 Проверить", "en": "🔍 Investigate", "tr": "🔍 Kontrol", "kk": "🔍 Тексеру"}.get(chat_lang, "🔍 Tekshirish")
        shoot_btn = {"uz": "🔫 O'ldirish", "ru": "🔫 Убить", "en": "🔫 Shoot", "tr": "🔫 Öldür", "kk": "🔫 Өлтіру"}.get(chat_lang, "🔫 O'ldirish")
        skip_btn = {"uz": "🚷 O'tkazib yuborish", "ru": "🚷 Пропустить", "en": "🚷 Skip", "tr": "🚷 Pas geç", "kk": "🚷 Өткізіп жіберу"}.get(chat_lang, "🚷 O'tkazib yuborish")
        kb = InlineKeyboardBuilder()
        kb.button(text=check_btn, callback_data=f"na|ko|{gid}|{ph}|c|0")
        kb.button(text=shoot_btn, callback_data=f"na|ko|{gid}|{ph}|k|0")
        kb.button(text=skip_btn, callback_data=f"na|ko|{gid}|{ph}|s|0")
        kb.adjust(2, 1)
        kom_head = {"uz": "🕵🏼 <b>Komissar</b>, nima qilasiz?", "ru": "🕵🏼 <b>Комиссар</b>, что делаем?", "en": "🕵🏼 <b>Detective</b>, what is your move?", "tr": "🕵🏼 <b>Komiser</b>, ne yapacaksınız?", "kk": "🕵🏼 <b>Комиссар</b>, не істейсіз?"}.get(chat_lang, "🕵🏼 <b>Komissar</b>, nima qilasiz?")
        if hist_lines:
            kom_head = "📋 <b>Tekshiruv tarixi:</b>\n" + "\n".join(hist_lines) + "\n\n" + kom_head

        try:
            await call.message.edit_text(kom_head, parse_mode="HTML", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return

    # Komissar: rejim tugmasi (target==0) -> nishon ro'yxati va "🔙 Ortga" tugmasi
    if code == "ko" and kind in ("c", "k") and int(target) == 0:
        all_alive_p = await player_repo.get_alive_players(gid)
        team_uids = {p.user_id for p in all_alive_p if p.role in (RoleNames.SERJANT, RoleNames.KOMISSAR)}
        exclude_set = team_uids | {uid}
        _p, tg = await _alive_targets(gid, exclude_uid=exclude_set)
        back_btn = {"uz": "🔙 Ortga", "ru": "🔙 Назад", "en": "🔙 Back", "tr": "🔙 Geri", "kk": "🔙 Артқа"}.get(chat_lang, "🔙 Ortga")
        skip_btn = {"uz": "🚷 O'tkazib yuborish", "ru": "🚷 Пропустить", "en": "🚷 Skip", "tr": "🚷 Pas geç", "kk": "🚷 Өткізіп жіберу"}.get(chat_lang, "🚷 O'tkazib yuborish")
        kb = InlineKeyboardBuilder()
        for tuid, label in tg:
            kb.button(text=label, callback_data=f"na|ko|{gid}|{ph}|{kind}|{tuid}")
        kb.button(text=back_btn, callback_data=f"na|ko|{gid}|{ph}|b|0")
        kb.button(text=skip_btn, callback_data=f"na|ko|{gid}|{ph}|s|0")
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
        atype = "investigate" if kind == "c" else "komissar_shoot"
        await ActionService.save_action(gid, ph, uid, int(target), atype)
        await _set_last_visited(gid, uid, int(target))
        await _announce_night_action(call, gid, ph, uid, role, kind=kind)
        action_name = "Tekshirish" if kind == "c" else "O'ldirish"
        target_name = await _player_name(int(target))
        await _confirm_choice(call, role, f"{action_name} ➔ {target_name}", lang=chat_lang, gid=gid)
        await _mark_action_completed(gid, ph, uid)
        return

    # Zanjir / Sehrgar: 1-nishon -> 2-nishon
    if code in ("zj", "se") and kind == "t":
        await ActionService.clear_player_actions(gid, ph, uid)
        await r.set(f"game:{gid}:tmp:{uid}:first", str(target), ex=3600)
        _p, tg = await _alive_targets(gid)
        skip_btn = {"uz": "🚷 O'tkazib yuborish", "ru": "🚷 Пропустить", "en": "🚷 Skip", "tr": "🚷 Pas geç", "kk": "🚷 Өткізіп жіберу"}.get(chat_lang, "🚷 O'tkazib yuborish")
        kb = InlineKeyboardBuilder()
        for tuid, label in tg:
            kb.button(text=label, callback_data=f"na|{code}|{gid}|{ph}|2|{tuid}")
        kb.button(text=skip_btn, callback_data=f"na|{code}|{gid}|{ph}|s|0")
        kb.adjust(1)
        title = "Endi 2-nishonni tanlang:"
        try:
            await call.message.edit_text(title, reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return
    if code in ("zj", "se") and kind == "2":
        await ActionService.clear_player_actions(gid, ph, uid)
        first = _redis_str(await r.get(f"game:{gid}:tmp:{uid}:first"))
        atype = "zanjir" if code == "zj" else "sehrgar"
        if first:
            await ActionService.save_action(gid, ph, uid, int(first), atype)
        await ActionService.save_action(gid, ph, uid, int(target), atype)
        n1 = await _player_name(int(first)) if first else "?"
        n2 = await _player_name(int(target))
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, f"{n1}, {n2}", lang=chat_lang, gid=gid)
        await _mark_action_completed(gid, ph, uid)
        return

    # Jin: o'yinchi (nishon) tanlanganda, Jin o'sha o'yinchi huzuriga boradi va o'yinchiga tilak menyusi yuboriladi
    if code == "ji" and kind == "t" and int(target) != 0:
        jin_uid = uid
        target_uid = int(target)
        target_player = await player_repo.load_player(gid, target_uid)
        if not target_player or not target_player.is_alive:
            await call.answer("Bu o'yinchi allaqachon o'yindan chiqqan!", show_alert=True)
            return
        target_name = await _player_name(target_uid)
        await _announce_night_action(call, gid, ph, jin_uid, role)
        await _confirm_choice(call, role, f"🧞 <b>{target_name}</b> huzuriga bordingiz.\nU o'z tilagini tanlamoqda...", lang=chat_lang, gid=gid)
        await _set_last_visited(gid, jin_uid, target_uid)
        await _mark_action_completed(gid, ph, jin_uid)

        # Tanlangan o'yinchiga (target_uid) 3 ta tilak menyusi yuboriladi
        from utils.i18n import get_chat_lang
        t_lang = await get_chat_lang(target_uid)
        wish_prompts = {
            "uz": "🧞 <b>Huzuringizga Jin keldi!</b>\n\nU sizning bitta tilagingizni bajo keltiradi.\nQuyidagi 3 ta tilakdan birini tanlang:",
            "ru": "🧞 <b>К вам явился Джинн!</b>\n\nОн исполнит одно ваше желание.\nВыберите одно из 3 желаний:",
            "en": "🧞 <b>A Genie has appeared before you!</b>\n\nHe will grant one of your wishes.\nChoose one of the 3 wishes:",
            "tr": "🧞 <b>Huzurunuza Cin geldi!</b>\n\nBir dileğinizi yerine getirecek.\nAşağıdaki 3 dilekten birini seçin:",
            "kk": "🧞 <b>Сізге Жын келді!</b>\n\nОл сіздің бір тілегіңізді орындайды.\n3 тілектің бірін таңдаңыз:"
        }
        life_btns = {"uz": "✨ Hayot (himoya)", "ru": "✨ Жизнь (защита)", "en": "✨ Life (protection)", "tr": "✨ Yaşam (koruma)", "kk": "✨ Өмір (қорғаныс)"}
        money_btns = {"uz": "💰 Boylik (pul)", "ru": "💰 Богатство (деньги)", "en": "💰 Wealth (money)", "tr": "💰 Zenginlik (para)", "kk": "💰 Байлық (ақша)"}
        kill_btns = {"uz": "💀 Qotillik", "ru": "💀 Убийство", "en": "💀 Murder", "tr": "💀 Cinayet", "kk": "💀 Өлтіру"}

        kb = InlineKeyboardBuilder()
        kb.button(text=life_btns.get(t_lang, life_btns["uz"]), callback_data=f"jw|{gid}|{ph}|life|{jin_uid}|{target_uid}")
        kb.button(text=money_btns.get(t_lang, money_btns["uz"]), callback_data=f"jw|{gid}|{ph}|money|{jin_uid}|{target_uid}")
        kb.button(text=kill_btns.get(t_lang, kill_btns["uz"]), callback_data=f"jw|{gid}|{ph}|kill|{jin_uid}|{target_uid}")
        kb.adjust(1)

        from utils.redis_game.night_engine import _send_private
        await _send_private(call.bot, target_uid, wish_prompts.get(t_lang, wish_prompts["uz"]), kb.as_markup())
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

        if role in (RoleNames.DON, RoleNames.MAFIA):
            await _notify_mafia_team_vote(call.bot, gid, uid, int(target))

        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, choice, lang=chat_lang, gid=gid)
        await _mark_action_completed(gid, ph, uid)
        return

    await call.answer()


_DAY_VOTE_BUFFERS: dict[int, list[str]] = {}
_DAY_VOTE_TASKS: dict[int, asyncio.Task] = {}
_DAY_VOTE_LOCK = asyncio.Lock()


async def flush_day_votes(gid: int, bot=None) -> None:
    """Bufferda yig'ilgan ovozlarni guruhlab yuborish (True Mafia uslubida)."""
    async with _DAY_VOTE_LOCK:
        items = _DAY_VOTE_BUFFERS.pop(gid, [])
        curr_task = asyncio.current_task()
        task = _DAY_VOTE_TASKS.pop(gid, None)
        if task and task is not curr_task and not task.done():
            task.cancel()

    if not items:
        return

    try:
        game_state = await game_repo.load_game(gid)
        if not game_state or not game_state.chat_id:
            return
        combined_text = "\n".join(items)
        if bot:
            await bot.send_message(
                game_state.chat_id,
                combined_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
    except Exception as e:
        print(f"Error flushing day votes for game {gid}: {e}")


async def _announce_day_vote(call: CallbackQuery, gid: int, uid: int, target_uid=None, *, skipped: bool = False, day: Optional[int] = None) -> None:
    """Kunduzgi ovoz e'loni — ovozlar umumlashtirilib (True Mafia kabi debounced batch) guruhga e'lon qilinadi."""
    try:
        game_state = await game_repo.load_game(gid)
        if not game_state or not game_state.chat_id:
            return

        if day is None:
            day_raw = await r.get(f"game:{gid}:day_num")
            day = int(day_raw) if day_raw is not None else 0

        dup_key = f"game:{gid}:day:{day}:vote_announced:{uid}"
        try:
            first_time = await r.set(dup_key, "1", nx=True, ex=7200)
            if not first_time:
                return
        except Exception:
            pass

        player = await player_repo.load_player(gid, uid)
        is_janob = player and player.role == RoleNames.JANOB
        voter = RoleNames.JANOB if is_janob else await _player_mention(uid)
        if skipped:
            text = f"🚷 {voter} hech kimni tanlamaslikka qaror qildi!"
        else:
            target = await _player_mention(int(target_uid))
            text = f"{voter} - {target}ga ovoz berdi"

        should_flush = False
        async with _DAY_VOTE_LOCK:
            if gid not in _DAY_VOTE_BUFFERS:
                _DAY_VOTE_BUFFERS[gid] = []
            _DAY_VOTE_BUFFERS[gid].append(text)

            # Agar 6 ta ovoz yig'ilsa, zudlik bilan guruhlab yuborish
            if len(_DAY_VOTE_BUFFERS[gid]) >= 6:
                should_flush = True
            elif gid not in _DAY_VOTE_TASKS or _DAY_VOTE_TASKS[gid].done():
                # Debounced grouping: 2 soniya ichidagi ovozlarni birlashtirib yuborish
                async def _delayed_flush(target_gid=gid, target_bot=call.bot):
                    try:
                        await asyncio.sleep(2.0)
                        await flush_day_votes(target_gid, target_bot)
                    except asyncio.CancelledError:
                        pass

                _DAY_VOTE_TASKS[gid] = asyncio.create_task(_delayed_flush())

        if should_flush:
            await flush_day_votes(gid, call.bot)
            return

    except Exception as e:
        print(f"Error in _announce_day_vote: {e}")


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
    existing_vote = await VoteService.get_vote(gid, day, uid)
    if existing_vote is not None:
        await call.answer("⚠️ Siz allaqachon ovoz bergansiz!", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    if target == "s":
        await VoteService.save_vote(gid, day, uid, 0)
        await _announce_day_vote(call, gid, uid, skipped=True, day=day)
        await call.answer("Hech kimni tanlamaslikka qaror qildingiz!")
        group_markup = await _get_go_group_markup(call.bot, gid)
        try:
            await call.message.edit_text("Hech kimni tanlamaslikka qaror qildingiz!", reply_markup=group_markup)
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
    await _announce_day_vote(call, gid, uid, target_id, day=day)
    await call.answer(f"Siz {name}ga ovoz berdingiz!")
    text = f"Siz {name}ga ovoz berdingiz!"
    group_markup = await _get_go_group_markup(call.bot, gid)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=group_markup)
    except Exception:
        try:
            await call.message.edit_text(text, reply_markup=group_markup)
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
    if uid == tid:
        await call.answer()
        return

    player = await player_repo.load_player(gid, uid)
    if not player or not player.is_alive:
        await call.answer()
        return

    if player.role == RoleNames.JANOB:
        votes = await VoteService.get_all_votes(gid, day)
        if votes.get(uid) == tid:
            await call.answer("🎖 Siz Janobsiz! Sizning 5 ta ovozingiz avtomatik qo'shilgan.", show_alert=True)
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


@router.callback_query(F.data.startswith("jw|"))
async def jin_wish_choice_cb(call: CallbackQuery, bot=None):
    """Jin kelgan o'yinchi 3 ta tilakdan birini tanlaydi (Hayot / Boylik / Qotillik)."""
    try:
        _, gid, ph, wish, jin_uid, wisher_uid = call.data.split("|")
        gid, ph, jin_uid, wisher_uid = int(gid), int(ph), int(jin_uid), int(wisher_uid)
    except Exception:
        await call.answer()
        return

    if call.from_user.id != wisher_uid:
        await call.answer("Bu tilak siz uchun emas!", show_alert=True)
        return

    if not await _ensure_night_phase(call, gid, ph):
        return

    from utils.i18n import get_chat_lang
    t_lang = await get_chat_lang(wisher_uid)
    wisher_name = await _player_name(wisher_uid)
    from utils.redis_game.night_engine import _send_private

    if wish == "life":
        await ActionService.clear_player_actions(gid, ph, jin_uid)
        await ActionService.save_action(gid, ph, jin_uid, wisher_uid, "jin_hayot")
        res_text = {
            "uz": "✨ <b>Hayot tilagi tanlandi!</b>\nJin bu tun sizni o'limdan himoya qiladi.",
            "ru": "✨ <b>Выбрано желание Жизни!</b>\nДжинн защитит вас от смерти этой ночью.",
            "en": "✨ <b>Life wish chosen!</b>\nThe Genie will protect you from death tonight.",
            "tr": "✨ <b>Yaşam dileği seçildi!</b>\nCin bu gece sizi ölümden koruyacak.",
            "kk": "✨ <b>Өмір тілегі таңдалды!</b>\nЖын бұл түнде сізді өлімнен қорғайды."
        }.get(t_lang, "✨ <b>Hayot tilagi tanlandi!</b>")
        try:
            await call.message.edit_text(res_text, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        await _send_private(call.bot, jin_uid, f"🧞 <b>{wisher_name}</b> Hayot tilagini tanladi. Bu tun u sizning himoyangizda!")
        
        # Guruhga tilak e'loni
        game_state = await game_repo.load_game(gid)
        if game_state and game_state.chat_id:
            c_lang = await get_chat_lang(game_state.chat_id)
            c_msg = {
                "uz": "✨ <b>Tilak bajarildi - Kimdir bugun o'lmaydi!</b>",
                "ru": "✨ <b>Желание исполнено - Кто-то сегодня не умрёт!</b>",
                "en": "✨ <b>Wish granted - Someone will not die tonight!</b>",
                "tr": "✨ <b>Dilek gerçekleşti - Biri bu gece ölmeyecek!</b>",
                "kk": "✨ <b>Тілек орындалды - Бүгін біреу өлмейді!</b>"
            }.get(c_lang, "✨ <b>Tilak bajarildi - Kimdir bugun o'lmaydi!</b>")
            try:
                await call.bot.send_message(game_state.chat_id, c_msg, parse_mode="HTML")
            except Exception:
                pass

        await call.answer("✨ Hayot tilagi qabul qilindi!")
        return

    elif wish == "money":
        await ActionService.clear_player_actions(gid, ph, jin_uid)
        await ActionService.save_action(gid, ph, jin_uid, wisher_uid, "jin_pul")
        res_text = {
            "uz": "💰 <b>Boylik tilagi tanlandi!</b>\nJin ertalab sizga boylik (pul/olmos) in'om etadi.",
            "ru": "💰 <b>Выбрано желание Богатства!</b>\nУтром Джинн одарит вас деньгами/алмазами.",
            "en": "💰 <b>Wealth wish chosen!</b>\nThe Genie will grant you riches in the morning.",
            "tr": "💰 <b>Zenginlik dileği seçildi!</b>\nCin sabah size para/elmas verecek.",
            "kk": "💰 <b>Байлық тілегі таңдалды!</b>\nЖын таңертең сізге байлық береді."
        }.get(t_lang, "💰 <b>Boylik tilagi tanlandi!</b>")
        try:
            await call.message.edit_text(res_text, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        await _send_private(call.bot, jin_uid, f"🧞 <b>{wisher_name}</b> Boylik tilagini tanladi. Ertalab unga boylik beriladi!")
        
        # Guruhga tilak e'loni
        game_state = await game_repo.load_game(gid)
        if game_state and game_state.chat_id:
            c_lang = await get_chat_lang(game_state.chat_id)
            c_msg = {
                "uz": "✨ <b>Tilak bajarildi - Kimdir boyib ketdi!</b>",
                "ru": "✨ <b>Желание исполнено - Кто-то разбогател!</b>",
                "en": "✨ <b>Wish granted - Someone got rich!</b>",
                "tr": "✨ <b>Dilek gerçekleşti - Biri zengin oldu!</b>",
                "kk": "✨ <b>Тілек орындалды - Біреу байып кетті!</b>"
            }.get(c_lang, "✨ <b>Tilak bajarildi - Kimdir boyib ketdi!</b>")
            try:
                await call.bot.send_message(game_state.chat_id, c_msg, parse_mode="HTML")
            except Exception:
                pass

        await call.answer("💰 Boylik tilagi qabul qilindi!")
        return

    elif wish == "kill":
        players = await player_repo.get_alive_players(gid)
        candidates = [p for p in players if p.user_id not in (wisher_uid, jin_uid)]
        names = await _name_map([p.user_id for p in candidates])
        kb = InlineKeyboardBuilder()
        for c in candidates:
            c_name = names.get(c.user_id) or str(c.user_id)
            kb.button(text=c_name, callback_data=f"jk|{gid}|{ph}|{c.user_id}|{jin_uid}|{wisher_uid}")
        kb.adjust(2)
        prompt = {
            "uz": "💀 <b>Qotillik tilagi:</b>\nKimni o'ldirishni tilaysiz? Nishonni tanlang:",
            "ru": "💀 <b>Желание Убийства:</b>\nКого приказать убить? Выберите цель:",
            "en": "💀 <b>Murder wish:</b>\nWho do you wish to eliminate? Choose a target:",
            "tr": "💀 <b>Cinayet dileği:</b>\nKimi öldürtmek istersiniz? Hedefi seçin:",
            "kk": "💀 <b>Өлтіру тілегі:</b>\nКімді өлтіруді бұйырасыз? Нысананы таңдаңыз:"
        }.get(t_lang, "💀 Kimni o'ldirishni tilaysiz?")
        try:
            await call.message.edit_text(prompt, parse_mode="HTML", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return


@router.callback_query(F.data.startswith("jk|"))
async def jin_kill_target_cb(call: CallbackQuery, bot=None):
    """Jin qotillik tilagi uchun o'yinchi nishon tanlaganda."""
    try:
        _, gid, ph, victim_uid, jin_uid, wisher_uid = call.data.split("|")
        gid, ph, victim_uid, jin_uid, wisher_uid = int(gid), int(ph), int(victim_uid), int(jin_uid), int(wisher_uid)
    except Exception:
        await call.answer()
        return

    if call.from_user.id != wisher_uid:
        await call.answer("Bu sizning tanlovingiz emas!", show_alert=True)
        return

    if not await _ensure_night_phase(call, gid, ph):
        return

    victim_player = await player_repo.load_player(gid, victim_uid)
    if not victim_player or not victim_player.is_alive:
        await call.answer("Bu o'yinchi allaqachon o'yindan chiqqan!", show_alert=True)
        return

    from utils.i18n import get_chat_lang
    t_lang = await get_chat_lang(wisher_uid)
    victim_name = await _player_name(victim_uid)
    wisher_name = await _player_name(wisher_uid)
    from utils.redis_game.night_engine import _send_private

    await ActionService.clear_player_actions(gid, ph, jin_uid)
    await ActionService.save_action(gid, ph, jin_uid, victim_uid, "jin_qotil")

    res_text = {
        "uz": f"💀 Siz <b>{victim_name}</b>ni o'ldirishni tiladingiz!\nJin bu tilakni bajo keltiradi.",
        "ru": f"💀 Вы пожелали убить <b>{victim_name}</b>!\nДжинн исполнит это желание.",
        "en": f"💀 You wished to eliminate <b>{victim_name}</b>!\nThe Genie will grant this wish.",
        "tr": f"💀 <b>{victim_name}</b> kişisinin öldürülmesini dilediniz!\nCin bu dileği yerine getirecek.",
        "kk": f"💀 Сіз <b>{victim_name}</b> өлтіруді бұйырдыңыз!\nЖын бұл тілекті орындайды."
    }.get(t_lang, f"💀 Siz <b>{victim_name}</b>ni o'ldirishni tiladingiz!")

    try:
        await call.message.edit_text(res_text, parse_mode="HTML", reply_markup=None)
    except Exception:
        pass

    await _send_private(call.bot, jin_uid, f"🧞 <b>{wisher_name}</b> sizdan <b>{victim_name}</b>ni o'ldirishni tiladi! Bu tun uni yo'q qilasiz.")

    # Guruhga tilak e'loni
    game_state = await game_repo.load_game(gid)
    if game_state and game_state.chat_id:
        c_lang = await get_chat_lang(game_state.chat_id)
        c_msg = {
            "uz": "✨ <b>Tilak bajarildi - Bu tun kimdir o'ladi!</b>",
            "ru": "✨ <b>Желание исполнено - Эту ночь кто-то умрёт!</b>",
            "en": "✨ <b>Wish granted - Someone will die tonight!</b>",
            "tr": "✨ <b>Dilek gerçekleşti - Bu gece biri ölecek!</b>",
            "kk": "✨ <b>Тілек орындалды - Бұл түнде біреу өледі!</b>"
        }.get(c_lang, "✨ <b>Tilak bajarildi - Bu tun kimdir o'ladi!</b>")
        try:
            await call.bot.send_message(game_state.chat_id, c_msg, parse_mode="HTML")
        except Exception:
            pass

    await call.answer("💀 Qotillik tilagi qabul qilindi!")
