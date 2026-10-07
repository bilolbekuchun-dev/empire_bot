from aiogram.types import CallbackQuery, Message
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from models.game_data import Game, GamePlayer, GamePhase, Action
from utils.role_names import RoleNames
from utils.premium_emojis import role_display

NIGHT_ACTION_ANNOUNCEMENTS = {
    RoleNames.DON: "🤵🏻 Don navbatdagi o'ljasini tanladi...",
    RoleNames.MAFIA: "🤵🏼 Mafia navbatdagi o'ljasini tanladi...",
    RoleNames.DOKTOR: "👨🏼‍⚕️ Doktor tungi navbatchilikka ketdi...",
    RoleNames.KOMISSAR: "🕵🏼 Komissar shubhali shaxsni tekshirdi...",
    RoleNames.QOTIL: "🔪 Qotil tungi o'ljasini tanladi...",
    RoleNames.DAYDI: "🧙‍♂️ Daydi tungi sayrga chiqdi...",
    RoleNames.KEZUVCHI: "💃 Kezuvchi tungi sayrga chiqdi...",
    RoleNames.ADVOKAT: "👨🏼‍💼 Advokat mijozini himoyaga oldi...",
    RoleNames.QORIQCHI: "🛡 Qo'riqchi qo'riqlash nishonini tanladi...",
    RoleNames.QAROQCHI: "⚔️ Qaroqchi harakat qildi...",
    RoleNames.SEHRGAR: "🧙‍♂️ Sehrgar sehru-joduni qo'lladi...",
    RoleNames.AFERIST: "🤹🏻 Aferist rejasini amalga oshirdi...",
    RoleNames.ZANJIR: "⛓ Zanjir zanjirlash nishonini tanladi...",
    RoleNames.REVERSER: "🔄 Reverser harakatni yo'naltirdi...",
    RoleNames.SOTQIN: "🤓 Sotqin hisob-kitob qildi...",
    RoleNames.AYGOQCHI: "🦇 Ayg'oqchi kuzatish o'tkazdi...",
    RoleNames.KONCHI: "👷🏻‍♂️ Konchi kon qazishni boshladi...",
    RoleNames.OVCHI: "🥷 Yollanma qotil nishonni belgiladi...",
    RoleNames.GAZABDOR: "🧌 G'azabkor g'azabini chiqardi...",
}

async def _register_action(call: CallbackQuery, default_action_type: str, alert_text: str):
    """Tungi harakatni ro'yxatga olish va DB da Action yaratish"""
    # 1. Alert (dialog pop-up) ko'rsatmaslik — faqat kichik toast bildirishnoma
    await call.answer(alert_text, show_alert=False)
    
    parts = call.data.split("_")
    target_name = "O'tkazib yuborildi"
    
    if len(parts) >= 2:
        try:
            phase_id = int(parts[-1])
            phase = await GamePhase.get_or_none(id=phase_id).prefetch_related("game", "game__chat")
            if phase and not phase.is_end:
                game = phase.game
                actor = await GamePlayer.filter(game=game, user__user_id=call.from_user.id, is_alive=True).prefetch_related("user").first()
                if actor:
                    act_type = default_action_type
                    act_result = None

                    if actor.role == RoleNames.DON:
                        act_type = "otish"
                        act_result = "dondan ovoz"
                    elif actor.role == RoleNames.MAFIA:
                        act_type = "otish"
                        act_result = "mafdan ovoz"
                    elif actor.role == RoleNames.DOKTOR:
                        act_type = "davo"
                        act_result = "davo"
                    elif actor.role == RoleNames.KOMISSAR:
                        if "otish" in call.data:
                            act_type = "otish"
                            act_result = "o'ldi"
                        else:
                            act_type = "tek"
                            act_result = "tek"
                    elif actor.role == RoleNames.QOTIL or actor.role == RoleNames.OVCHI:
                        act_type = "otish"
                        act_result = "o'ldi"
                    elif actor.role == RoleNames.ZOMBI:
                        act_type = "otish"
                        act_result = "zombi"
                    elif actor.role == RoleNames.GAZABDOR:
                        act_type = "gazabdor"
                        act_result = "gazab"
                    elif "davo" in call.data:
                        act_type = "davo"
                        act_result = "davo"
                    elif "otish" in call.data:
                        act_type = "otish"
                        act_result = "o'ldi"
                    elif "tek" in call.data:
                        act_type = "tek"
                        act_result = "tek"
                    elif "daydi" in call.data or actor.role == RoleNames.DAYDI:
                        act_type = "daydi"
                        act_result = "daydi"
                    elif "kezuv" in call.data or actor.role == RoleNames.KEZUVCHI:
                        act_type = "kezuv"
                        act_result = "kezuv"
                    elif "adv" in call.data or actor.role == RoleNames.ADVOKAT:
                        act_type = "advokat"
                        act_result = "advokat"
                    elif "qoriqchi" in call.data or actor.role == RoleNames.QORIQCHI:
                        act_type = "qoriqchi"
                        act_result = "qoriqchi"
                    elif "sehr" in call.data or actor.role == RoleNames.SEHRGAR:
                        act_type = "sehr"
                        act_result = "sehr"
                    elif "aferist" in call.data or actor.role == RoleNames.AFERIST:
                        act_type = "aferist"
                        act_result = "aferist"
                    elif "zanjir" in call.data or actor.role == RoleNames.ZANJIR:
                        act_type = "zanjir"
                        act_result = "zanjir"
                    elif "reverser" in call.data or actor.role == RoleNames.REVERSER:
                        act_type = "reverser"
                        act_result = "reverser"
                    elif "jurnalist" in call.data or actor.role == RoleNames.JURNALIST:
                        act_type = "jurnalist"
                        act_result = "jurnalist"
                    elif "aygoqchi" in call.data or actor.role == RoleNames.AYGOQCHI:
                        act_type = "aygoqchi"
                        act_result = "aygoqchi"
                    elif "sotqin" in call.data or actor.role == RoleNames.SOTQIN:
                        act_type = "sotqin"
                        act_result = "sotqin"
                    elif "xoyin" in call.data or actor.role == RoleNames.XOYIN:
                        act_type = "xoyin"
                        act_result = "xoyin"

                    target_str = parts[-2]
                    target = None
                    if target_str.isdigit():
                        target_uid = int(target_str)
                        target = await GamePlayer.filter(game=game, user__user_id=target_uid, is_alive=True).prefetch_related("user").first()
                        if target and target.user:
                            target_name = target.user.full_name
                        else:
                            await call.answer("⚠️ Ushbu o'yinchi halok bo'lgan yoki topilmadi!", show_alert=True)
                            return

                    # Doktor o'zini davolaganda can_heal_self ni tekshirish va yangilash
                    if target and actor.role == RoleNames.DOKTOR and target.id == actor.id:
                        if not getattr(actor, "can_heal_self", True):
                            await call.answer("⚠️ Siz o'zingizni qayta davolay olmaysiz!", show_alert=True)
                            return
                        actor.can_heal_self = False
                        await actor.save()

                    # Avvalgi harakat bor-yo'qligini tekshirish va atomik yangilash (Race condition oldini olish)
                    existing_action = await Action.filter(phase=phase, actor=actor).first()
                    already_acted = existing_action is not None

                    if existing_action:
                        existing_action.target = target
                        existing_action.action_type = act_type
                        existing_action.result = act_result
                        await existing_action.save()
                    else:
                        await Action.create(
                            phase=phase,
                            actor=actor,
                            target=target,
                            action_type=act_type,
                            result=act_result
                        )

                    # Guruhga anonim harakat haqida bildirishnoma yuborish (birinchi martasida)
                    if not already_acted and game:
                        try:
                            send_announce = True
                            if actor.role == RoleNames.MAFIA:
                                don_alive = await GamePlayer.filter(game=game, role=RoleNames.DON, is_alive=True).exists()
                                if don_alive:
                                    send_announce = False

                            if send_announce:
                                await game.fetch_related("chat")
                                if game.chat and getattr(game.chat, "chat_id", None):
                                    if actor.role == RoleNames.KOMISSAR:
                                        if act_type == "otish":
                                            announce_msg = f"{role_display(actor.role)} pistoletini o'qladi..."
                                        else:
                                            announce_msg = f"{role_display(actor.role)} shubhali shaxsni tekshirdi..."
                                    else:
                                        announce_msg = NIGHT_ACTION_ANNOUNCEMENTS.get(
                                            actor.role,
                                            f"{role_display(actor.role)} tungi harakatini amalga oshirdi..."
                                        )
                                    from utils.game_logic import safe_send_message
                                    await safe_send_message(call.bot, game.chat.chat_id, announce_msg, parse_mode="HTML")
                        except Exception as ge:
                            print(f"Guruhga tungi e'lon yuborishda xato: {ge}")
        except Exception as e:
            print(f"_register_action xatosi: {e}")

    try:
        await call.message.edit_text(f"✅ Tanlov qabul qilindi: <b>{target_name}</b>", parse_mode="HTML")
    except Exception:
        pass

async def qaroqchi_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "qaroqchi", "⚔️ Qaroqchi: Tanlovingiz qabul qilindi!")

async def komissar_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    data = call.data
    parts = data.split("_")

    if "tanla_tek" in data:
        try:
            phase_id = int(parts[-1])
            phase = await GamePhase.get_or_none(id=phase_id).prefetch_related("game")
            if phase and not phase.is_end:
                game = phase.game
                players = await GamePlayer.filter(game=game, is_alive=True).prefetch_related("user")
                from keyboards.game_keyboard import action_buttons
                kb = await action_buttons(
                    user_id=call.from_user.id,
                    role=RoleNames.KOMISSAR,
                    players=players,
                    phase_id=phase_id,
                    vsgame="vsgame" in game.mode,
                    tek=True,
                    nik=game.mode.split(">")[1] if len(game.mode.split(">")) > 1 else None
                )
                await call.message.edit_text("🕵🏼 <b>Komissar</b>: Kimni tekshirmoqchisiz?", reply_markup=kb, parse_mode="HTML")
                await call.answer()
                return
        except Exception:
            pass

    elif "tanla_otish" in data:
        try:
            phase_id = int(parts[-1])
            phase = await GamePhase.get_or_none(id=phase_id).prefetch_related("game")
            if phase and not phase.is_end:
                game = phase.game
                players = await GamePlayer.filter(game=game, is_alive=True).prefetch_related("user")
                from keyboards.game_keyboard import action_buttons
                kb = await action_buttons(
                    user_id=call.from_user.id,
                    role=RoleNames.KOMISSAR,
                    players=players,
                    phase_id=phase_id,
                    vsgame="vsgame" in game.mode,
                    otish=True,
                    nik=game.mode.split(">")[1] if len(game.mode.split(">")) > 1 else None
                )
                await call.message.edit_text("🕵🏼 <b>Komissar</b>: Kimni o'ldirmoqchisiz?", reply_markup=kb, parse_mode="HTML")
                await call.answer()
                return
        except Exception:
            pass

    elif "orqaga" in data:
        try:
            phase_id = int(parts[-1])
            phase = await GamePhase.get_or_none(id=phase_id).prefetch_related("game")
            if phase and not phase.is_end:
                game = phase.game
                players = await GamePlayer.filter(game=game, is_alive=True).prefetch_related("user")
                from keyboards.game_keyboard import action_buttons
                kb = await action_buttons(
                    user_id=call.from_user.id,
                    role=RoleNames.KOMISSAR,
                    players=players,
                    phase_id=phase_id,
                    vsgame="vsgame" in game.mode,
                    kom=True,
                    nik=game.mode.split(">")[1] if len(game.mode.split(">")) > 1 else None
                )
                await call.message.edit_text("🕵🏼 <b>Komissar</b>: Harakat turini tanlang:", reply_markup=kb, parse_mode="HTML")
                await call.answer()
                return
        except Exception:
            pass

    await _register_action(call, "komissar", "🕵🏼 Komissar: Tanlovingiz qabul qilindi!")

async def komissar_upgrade_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "komissar_upgrade", "🕵🏼 Komissar buyrug'i qabul qilindi!")

async def kom_learn_bosh_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "kom_learn", "🕵🏼 Komissar ma'lumoti qabul qilindi!")

async def dok_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "davo", "👨🏼‍⚕️ Doktor: Davolash nishoni qabul qilindi!")

async def zombi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "zombi", "🧟 Zombi harakati qabul qilindi!")

async def don_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "otish", "🤵🏻 Don: Natija va nishon tanlandi!")

async def maf_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "otish", "🤵🏼 Mafia: Otish nishoni qabul qilindi!")

async def qoriqchi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "qoriqchi", "🛡 Qo'riqchi: Qo'riqlash nishoni qabul qilindi!")

async def xoyin_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "xoyin", "👺 Xoyin: Tanlov qabul qilindi!")

async def zanjir_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "zanjir", "⛓ Zanjir harakati qabul qilindi!")

async def daydi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "daydi", "🧙‍♂️ Daydi: Kuzatish tanlovi qabul qilindi!")

async def kezuv_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "kezuv", "💃 Kezuvchi: Tanlov qabul qilindi!")

async def advokat_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "advokat", "👨🏼‍💼 Advokat: Himoya qabul qilindi!")

async def qotil_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "otish", "🔪 Qotil: Hujum nishoni qabul qilindi!")

async def night_sheriklar_msg(message: Message, bot: Bot, state: FSMContext):
    """Tunda sheriklar bir-biriga yozgan xabari"""
    pass

async def ovchi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "ovchi", "🥷 Yollanma qotil: Tanlov qabul qilindi!")

async def gazabdor_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "gazabdor", "🧌 G'azabkor: Niyat qabul qilindi!")

async def aferist_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "aferist", "🤹🏻 Aferist: Xiyola qabul qilindi!")

async def sehr_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "sehr", "🧙‍ Sehrgar amali qabul qilindi!")

async def sehrgar_night_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "sehr", "🧙‍ Sehrgar: Sehr qabul qilindi!")

async def jurnalist_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "jurnalist", "👩🏼‍💻 Jurnalist: Ma'lumot yig'ish qabul qilindi!")

async def sotqin_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "sotqin", "🤓 Sotqin: Tanlov qabul qilindi!")

async def aygoqchi_action_handler(call: CallbackQuery, state: FSMContext, bot: Bot = None):
    await _register_action(call, "aygoqchi", "🦇 Ayg'oqchi: Kuzatish qabul qilindi!")

async def konchi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "konchi", "👷🏻‍♂️ Konchi: Kon qazish qabul qilindi!")

async def reverser_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "reverser", "🔄 Reverser: Burish nishoni qabul qilindi!")

async def taqlidchi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "taqlidchi", "🎭 Taqlidchi: Tanlov qabul qilindi!")
