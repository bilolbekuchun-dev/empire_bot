from aiogram.types import CallbackQuery, Message
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from models.game_data import Game, GamePlayer, GamePhase, Action
from utils.role_names import RoleNames

async def _register_action(call: CallbackQuery, action_type: str, alert_text: str):
    """Tungi harakatni ro'yxatga olish"""
    await call.answer(alert_text, show_alert=True)
    try:
        await call.message.edit_text(f"✅ Tanlov qabul qilindi: {call.data}")
    except Exception:
        pass

async def qaroqchi_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "qaroqchi", "⚔️ Qaroqchi: Tanlovingiz qabul qilindi!")

async def komissar_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "komissar", "🕵🏼 Komissar: Tanlovingiz qabul qilindi!")

async def komissar_upgrade_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "komissar_upgrade", "🕵🏼 Komissar buyrug'i qabul qilindi!")

async def kom_learn_bosh_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "kom_learn", "🕵🏼 Komissar ma'lumoti qabul qilindi!")

async def dok_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "doktor", "👨🏼‍⚕️ Doktor: Davolash nishoni qabul qilindi!")

async def zombi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "zombi", "🧟 Zombi harakati qabul qilindi!")

async def don_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "don", "🤵🏻 Don: Natija va nishon tanlandi!")

async def maf_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "mafia", "🤵🏼 Mafia: Otish nishoni qabul qilindi!")

async def qoriqchi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "qoriqchi", "🛡 Qo'riqchi: Qo'riqlash nishoni qabul qilindi!")

async def xoyin_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "xoyin", "👺 Xoyin: Tanlov qabul qilindi!")

async def zanjir_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "zanjir", "⛓ Zanjir harakati qabul qilindi!")

async def daydi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "daydi", "🧙‍♂️ Daydi: Kuzatish tanlovi qabul qilindi!")

async def kezuv_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "kezuvchi", "💃 Kezuvchi: Tanlov qabul qilindi!")

async def advokat_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "advokat", "👨🏼‍💼 Advokat: Himoya qabul qilindi!")

async def qotil_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "qotil", "🔪 Qotil: Hujum nishoni qabul qilindi!")

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
    await _register_action(call, "sehrgar", "🧙‍ Sehrgar: Sehr qabul qilindi!")

async def jurnalist_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "jurnalist", "👩🏼‍💻 Jurnalist: Ma'lumot yig'ish qabul qilindi!")

async def sotqin_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "sotqin", "🤓 Sotqin: Tanlov qabul qilindi!")

async def aygoqchi_action_handler(call: CallbackQuery, state: FSMContext, bot: Bot = None):
    await _register_action(call, "aygoqchi", "🦇 Ayg'oqchi: Kuzatish qabul qilindi!")

async def konchi_action_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    await _register_action(call, "konchi", "👷🏻‍♂️ Konchi: Kon qazish qabul qilindi!")
