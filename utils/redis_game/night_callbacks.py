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


async def _confirm_choice(call: CallbackQuery, role: str, choice: str, lang: str = "uz") -> None:
    text = _choice_text(role, choice, lang=lang)
    await call.answer()
    try:
        await call.message.edit_text(text, parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(text)
        except Exception:
            pass


NIGHT_ACTION_ANNOUNCE = {
    "uz": {
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
    },
    "ru": {
        RoleNames.DOKTOR: "{role} отправился(лась) на ночное дежурство...",
        RoleNames.KOMISSAR: "{role} отправился(лась) на проверку...",
        RoleNames.DON: "{role} выбрал(а) жертву...",
        RoleNames.MAFIA: "{role} вышел(ла) на охоту...",
        RoleNames.AYGOQCHI: "{role} вышел(ла) на слежку...",
        RoleNames.QOTIL: "{role} ищет жертву...",
        RoleNames.OVCHI: "{role} взял(а) на прицел...",
        RoleNames.DAYDI: "{role} бродит по улицам...",
        RoleNames.KEZUVCHI: "{role} вышел(ла) на ночную прогулку...",
        RoleNames.ZANJIR: "{role} раскинул(а) цепи...",
        RoleNames.XOYIN: "{role} отправился(лась) на поиски...",
        RoleNames.QORIQCHI: "{role} встал(а) на пост...",
        RoleNames.ADVOKAT: "{role} открыл(а) материалы дела...",
        RoleNames.GAZABDOR: "{role} затаил(а) злобу...",
        RoleNames.AFERIST: "{role} строит ночные планы...",
        RoleNames.SEHRGAR: "{role} готовит заклинание...",
        RoleNames.JURNALIST: "{role} отправился(лась) собирать информацию...",
        RoleNames.SOTQIN: "{role} действует скрытно...",
        RoleNames.KONCHI: "{role} спустился(лась) в шахту...",
        RoleNames.QAROQCHI: "{role} отправился(лась) на поиски добычи...",
        RoleNames.JIN: "{role} появился(лась) из лампы...",
        RoleNames.REVERSER: "{role} видоизменяет судьбу...",
    },
    "en": {
        RoleNames.DOKTOR: "{role} went on night duty...",
        RoleNames.KOMISSAR: "{role} went to investigate...",
        RoleNames.DON: "{role} chose a target...",
        RoleNames.MAFIA: "{role} went hunting...",
        RoleNames.AYGOQCHI: "{role} went spying...",
        RoleNames.QOTIL: "{role} is looking for a victim...",
        RoleNames.OVCHI: "{role} locked target...",
        RoleNames.DAYDI: "{role} is roaming the streets...",
        RoleNames.KEZUVCHI: "{role} went for a night walk...",
        RoleNames.ZANJIR: "{role} cast the chains...",
        RoleNames.XOYIN: "{role} went searching...",
        RoleNames.QORIQCHI: "{role} stood guard...",
        RoleNames.ADVOKAT: "{role} opened the case files...",
        RoleNames.GAZABDOR: "{role} harbored anger...",
        RoleNames.AFERIST: "{role} is scheming...",
        RoleNames.SEHRGAR: "{role} is preparing a spell...",
        RoleNames.JURNALIST: "{role} went gathering news...",
        RoleNames.SOTQIN: "{role} moved silently...",
        RoleNames.KONCHI: "{role} went into the mine...",
        RoleNames.QAROQCHI: "{role} went searching for loot...",
        RoleNames.JIN: "{role} appeared from the lamp...",
        RoleNames.REVERSER: "{role} is altering fate...",
    },
    "tr": {
        RoleNames.DOKTOR: "{role} gece nöbetine çıktı...",
        RoleNames.KOMISSAR: "{role} birini kontrol etmeye gitti...",
        RoleNames.DON: "{role} kurbanını seçti...",
        RoleNames.MAFIA: "{role} ava çıktı...",
        RoleNames.AYGOQCHI: "{role} gözleme çıktı...",
        RoleNames.QOTIL: "{role} kurban arıyor...",
        RoleNames.OVCHI: "{role} hedef aldı...",
        RoleNames.DAYDI: "{role} sokaklarda geziyor...",
        RoleNames.KEZUVCHI: "{role} gece yürüyüşüne çıktı...",
        RoleNames.ZANJIR: "{role} zincirlerini attı...",
        RoleNames.XOYIN: "{role} aramaya çıktı...",
        RoleNames.QORIQCHI: "{role} nöbete durdu...",
        RoleNames.ADVOKAT: "{role} dava dosyasını açtı...",
        RoleNames.GAZABDOR: "{role} öfkesini gizledi...",
        RoleNames.AFERIST: "{role} gece planını yaptı...",
        RoleNames.SEHRGAR: "{role} büyü hazırlıyor...",
        RoleNames.JURNALIST: "{role} bilgi toplamaya çıktı...",
        RoleNames.SOTQIN: "{role} sessizce hareket etti...",
        RoleNames.KONCHI: "{role} madene indi...",
        RoleNames.QAROQCHI: "{role} ganimet aramaya gitti...",
        RoleNames.JIN: "{role} lambadan çıktı...",
        RoleNames.REVERSER: "{role} kaderi değiştirmeye çıktı...",
    },
    "kk": {
        RoleNames.DOKTOR: "{role} түнгі кезекшілікке кетті...",
        RoleNames.KOMISSAR: "{role} біреуді тексеруге кетті...",
        RoleNames.DON: "{role} олжасын таңдады...",
        RoleNames.MAFIA: "{role} аңшылыққа шықты...",
        RoleNames.AYGOQCHI: "{role} бақылауға шықты...",
        RoleNames.QOTIL: "{role} құрбан іздеп кетті...",
        RoleNames.OVCHI: "{role} нысанаға алды...",
        RoleNames.DAYDI: "{role} көше аралап жүр...",
        RoleNames.KEZUVCHI: "{role} түнгі серуенге шықты...",
        RoleNames.ZANJIR: "{role} шынжырларын тастады...",
        RoleNames.XOYIN: "{role} іздеуге шықты...",
        RoleNames.QORIQCHI: "{role} бекетке тұрды...",
        RoleNames.ADVOKAT: "{role} іс қағаздарын ашты...",
        RoleNames.GAZABDOR: "{role} ашуын жасырды...",
        RoleNames.AFERIST: "{role} түнгі жоспарын құрды...",
        RoleNames.SEHRGAR: "{role} сиқыр дайындауда...",
        RoleNames.JURNALIST: "{role} ақпарат жинауға шықты...",
        RoleNames.SOTQIN: "{role} дыбыссыз әрекет етті...",
        RoleNames.KONCHI: "{role} шахтаға түсті...",
        RoleNames.QAROQCHI: "{role} олжа іздеп кетті...",
        RoleNames.JIN: "{role} шамның жанында пайда болды...",
        RoleNames.REVERSER: "{role} тағдырды бұруға шықты...",
    }
}


async def _announce_night_action(call: CallbackQuery, gid: int, ph: int, uid: int, role: str, *, skipped: bool = False, kind: str = None) -> None:
    """Guruhga tungi harakat e'lonini bir marta yuborish (nishon ochilmaydi)."""
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
        await _confirm_choice(call, role, skip_text, lang=chat_lang)
        await _mark_action_completed(gid, ph, uid)
        return

    # Komissar: Ortga qaytish (rejim tanlash menyusi)
    if code == "ko" and kind == "b":
        check_btn = {"uz": "🔍 Tekshirish", "ru": "🔍 Проверить", "en": "🔍 Investigate", "tr": "🔍 Kontrol", "kk": "🔍 Тексеру"}.get(chat_lang, "🔍 Tekshirish")
        shoot_btn = {"uz": "🔫 O'ldirish", "ru": "🔫 Убить", "en": "🔫 Shoot", "tr": "🔫 Öldür", "kk": "🔫 Өлтіру"}.get(chat_lang, "🔫 O'ldirish")
        skip_btn = {"uz": "🚷 O'tkazib yuborish", "ru": "🚷 Пропустить", "en": "🚷 Skip", "tr": "🚷 Pas geç", "kk": "🚷 Өткізіп жіберу"}.get(chat_lang, "🚷 O'tkazib yuborish")
        kb = InlineKeyboardBuilder()
        kb.button(text=check_btn, callback_data=f"na|ko|{gid}|{ph}|c|0")
        kb.button(text=shoot_btn, callback_data=f"na|ko|{gid}|{ph}|k|0")
        kb.button(text=skip_btn, callback_data=f"na|ko|{gid}|{ph}|s|0")
        kb.adjust(2, 1)
        kom_head = {"uz": "🕵🏼 <b>Komissar</b>, nima qilasiz?", "ru": "🕵🏼 <b>Комиссар</b>, что делаем?", "en": "🕵🏼 <b>Detective</b>, what is your move?", "tr": "🕵🏼 <b>Komiser</b>, ne yapacaksınız?", "kk": "🕵🏼 <b>Комиссар</b>, не істейсіз?"}.get(chat_lang, "🕵🏼 <b>Komissar</b>, nima qilasiz?")
        try:
            await call.message.edit_text(kom_head, parse_mode="HTML", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return

    # Komissar: rejim tugmasi (target==0) -> nishon ro'yxati va "🔙 Ortga" tugmasi
    if code == "ko" and kind in ("c", "k") and int(target) == 0:
        _p, tg = await _alive_targets(gid, exclude_uid=uid)
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
        await _confirm_choice(call, role, f"{action_name} ➔ {target_name}", lang=chat_lang)
        await _mark_action_completed(gid, ph, uid)
        return

    # Zanjir / Sehrgar / Reverser: 1-nishon -> 2-nishon
    if code in ("zj", "se", "rv") and kind == "t":
        await ActionService.clear_player_actions(gid, ph, uid)
        await r.set(f"game:{gid}:tmp:{uid}:first", str(target), ex=3600)
        exclude = {uid, int(target)} if code == "rv" else None
        _p, tg = await _alive_targets(gid, exclude_uid=exclude)
        skip_btn = {"uz": "🚷 O'tkazib yuborish", "ru": "🚷 Пропустить", "en": "🚷 Skip", "tr": "🚷 Pas geç", "kk": "🚷 Өткізіп жіберу"}.get(chat_lang, "🚷 O'tkazib yuborish")
        kb = InlineKeyboardBuilder()
        for tuid, label in tg:
            kb.button(text=label, callback_data=f"na|{code}|{gid}|{ph}|2|{tuid}")
        kb.button(text=skip_btn, callback_data=f"na|{code}|{gid}|{ph}|s|0")
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
        await _confirm_choice(call, role, f"{n1}, {n2}", lang=chat_lang)
        await _mark_action_completed(gid, ph, uid)
        return

    # Jin: Ortga qaytish / Asosiy menyu
    if code == "ji" and kind == "b":
        kb = InlineKeyboardBuilder()
        kb.button(text="✨ Hayot", callback_data=f"na|ji|{gid}|{ph}|jh_menu|0")
        kb.button(text="💰 Pul", callback_data=f"na|ji|{gid}|{ph}|jp_menu|0")
        kb.button(text="💀 Qotillik", callback_data=f"na|ji|{gid}|{ph}|jq_menu|0")
        kb.button(text="🚷 O'tkazib yuborish", callback_data=f"na|ji|{gid}|{ph}|s|0")
        kb.adjust(1)
        try:
            await call.message.edit_text("🧞 <b>Jin</b>, tilagingizni tanlang:", parse_mode="HTML", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return

    # Jin: ✨ Hayot menyusi (O'zimga / Boshqaga)
    if code == "ji" and kind == "jh_menu":
        kb = InlineKeyboardBuilder()
        kb.button(text="👤 O'zimga", callback_data=f"na|ji|{gid}|{ph}|jh_self|0")
        kb.button(text="👥 Boshqaga", callback_data=f"na|ji|{gid}|{ph}|jh_other|0")
        kb.button(text="🔙 Ortga", callback_data=f"na|ji|{gid}|{ph}|b|0")
        kb.adjust(2, 1)
        try:
            await call.message.edit_text("Kimga hayot tilamoqchisiz?", parse_mode="HTML", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return

    # Jin: ✨ Hayot ➔ O'zimga
    if code == "ji" and kind == "jh_self":
        await ActionService.clear_player_actions(gid, ph, uid)
        await ActionService.save_action(gid, ph, uid, uid, "jin_hayot")
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, "✨ Hayot ➔ O'zimga", lang=chat_lang)
        await _mark_action_completed(gid, ph, uid)
        return

    # Jin: ✨ Hayot ➔ Boshqaga (o'yinchilar ro'yxati)
    if code == "ji" and kind == "jh_other":
        _p, tg = await _alive_targets(gid, exclude_uid=uid)
        kb = InlineKeyboardBuilder()
        for tuid, label in tg:
            kb.button(text=label, callback_data=f"na|ji|{gid}|{ph}|jh_target|{tuid}")
        kb.button(text="🔙 Ortga", callback_data=f"na|ji|{gid}|{ph}|jh_menu|0")
        kb.adjust(1)
        try:
            await call.message.edit_text("✨ Kimga hayot tilamoqchisiz?", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return

    # Jin: ✨ Hayot ➔ NISHON tanlandi
    if code == "ji" and kind == "jh_target" and int(target) != 0:
        await ActionService.clear_player_actions(gid, ph, uid)
        await ActionService.save_action(gid, ph, uid, int(target), "jin_hayot")
        target_name = await _player_name(int(target))
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, f"✨ Hayot ➔ {target_name}", lang=chat_lang)
        await _mark_action_completed(gid, ph, uid)
        return

    # Jin: 💰 Pul menyusi (o'yinchilar ro'yxati)
    if code == "ji" and kind == "jp_menu":
        players = await player_repo.get_alive_players(gid)
        names = await _name_map([p.user_id for p in players])
        kb = InlineKeyboardBuilder()
        for p in players:
            label = html.escape(names.get(p.user_id) or str(p.user_id))
            kb.button(text=label, callback_data=f"na|ji|{gid}|{ph}|jp_target|{p.user_id}")
        kb.button(text="🔙 Ortga", callback_data=f"na|ji|{gid}|{ph}|b|0")
        kb.adjust(1)
        try:
            await call.message.edit_text("💰 Kimga pul (va olmos) in'om etmoqchisiz?", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return

    # Jin: 💰 Pul ➔ NISHON tanlandi
    if code == "ji" and kind == "jp_target" and int(target) != 0:
        await ActionService.clear_player_actions(gid, ph, uid)
        await ActionService.save_action(gid, ph, uid, int(target), "jin_pul")
        target_name = await _player_name(int(target))
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, f"💰 Pul ➔ {target_name}", lang=chat_lang)
        await _mark_action_completed(gid, ph, uid)
        return

    # Jin: 💀 Qotillik menyusi (o'yinchilar ro'yxati)
    if code == "ji" and kind == "jq_menu":
        _p, tg = await _alive_targets(gid, exclude_uid=uid)
        kb = InlineKeyboardBuilder()
        for tuid, label in tg:
            kb.button(text=label, callback_data=f"na|ji|{gid}|{ph}|jq_target|{tuid}")
        kb.button(text="🔙 Ortga", callback_data=f"na|ji|{gid}|{ph}|b|0")
        kb.adjust(1)
        try:
            await call.message.edit_text("💀 Kimni o'ldirmoqchisiz?", reply_markup=kb.as_markup())
        except Exception:
            pass
        await call.answer()
        return

    # Jin: 💀 Qotillik ➔ NISHON tanlandi
    if code == "ji" and kind == "jq_target" and int(target) != 0:
        await ActionService.clear_player_actions(gid, ph, uid)
        await ActionService.save_action(gid, ph, uid, int(target), "jin_qotil")
        target_name = await _player_name(int(target))
        await _announce_night_action(call, gid, ph, uid, role)
        await _confirm_choice(call, role, f"💀 Qotillik ➔ {target_name}", lang=chat_lang)
        await _mark_action_completed(gid, ph, uid)
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
        await _confirm_choice(call, role, choice, lang=chat_lang)
        await _mark_action_completed(gid, ph, uid)
        return

    await call.answer()


async def _announce_day_vote(call: CallbackQuery, gid: int, uid: int, target_uid=None, *, skipped: bool = False) -> None:
    """Kunduzgi ovoz e'loni — har bir ovoz harakati (yangi ovoz yoki o'zgargan ovoz) guruhga e'lon qilinadi."""
    try:
        game_state = await game_repo.load_game(gid)
        if not game_state:
            return
        day_raw = await r.get(f"game:{gid}:day_num")
        day_num = int(day_raw) if day_raw is not None else 0

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
            target = await _player_mention(int(target_uid))
            text = f"{voter} - {target}ga ovoz berdi"

        await call.bot.send_message(
            game_state.chat_id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
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
        await _announce_day_vote(call, gid, uid, skipped=True)
        await call.answer("Hech kimni tanlamaslikka qaror qildingiz!")
        try:
            await call.message.edit_text("Hech kimni tanlamaslikka qaror qildingiz!", reply_markup=None)
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
    await call.answer(f"Siz {name}ga ovoz berdingiz!")
    text = f"Siz {name}ga ovoz berdingiz!"
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=None)
    except Exception:
        try:
            await call.message.edit_text(text, reply_markup=None)
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

