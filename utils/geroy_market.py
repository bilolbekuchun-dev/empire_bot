from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from models.user import Profile, User, GeroyMarket, ActiveRole, ChangeDiamondGiveAway, VipUser, Blocked_user
from models.game_data import Chat, Geroys
from config import INFO_GROUP, ADMINS, GEROY_MARKET_CHANNEL_ID, GEROY_MARKET_CHANNEL_URL, GEROY_SHOP_SYSTEM_USER_ID

class GeroyMarketPrice(StatesGroup):
    waiting_for_price = State()


def seller_label_for(user: User) -> str:
    if getattr(user, "username", None):
        return f"{user.full_name} (@{user.username})"
    return f"{user.full_name} (username yo'q)"


def _geroy_market_channel_text(seller_label: str, geroy: Geroys, price: int) -> str:
    min_dmg = 40 + (geroy.level - 1) * 7
    max_dmg = 40 + geroy.level * 7
    return (
        f"<b>🎉 Yangi geroy!\n\n</b>"
        f"<b>👤 Foydalanuvchi:</b> {seller_label}\n"
        f"<b>🛡 Geroy:</b> {geroy.name}\n"
        f"<b>👊 Kuch:</b> {min_dmg if min_dmg < 100 else 'maksimal uradi'}-{max_dmg if min_dmg < 100 else ''}\n"
        f"<b>♥️ Max himoya:</b> {int(10 * (geroy.level / 1.2))}\n"
        f"<b>☑️ Ball:</b> {geroy.ball}\n"
        f"<b>💰 Narxi:</b> {price} 💎\n\n"
        f"<b>Sotib olish uchun pastdagi tugmani bosing!</b>"
    )


async def create_market_listing(user: User, geroy: Geroys, price: int, bot: Bot, seller_label: str = None) -> GeroyMarket:
    """Bitta geroyni savdoga qo'yadi: GeroyMarket yozuvini yaratadi va kanalga e'lon joylaydi.
    Bot suhbatidan ham, webapp'dan ham chaqiriladi."""
    entry = await GeroyMarket.create(user=user, geroy=geroy, price=price, status="active")

    label = seller_label or seller_label_for(user)
    if GEROY_MARKET_CHANNEL_ID:
        try:
            sent = await bot.send_message(
                GEROY_MARKET_CHANNEL_ID,
                _geroy_market_channel_text(label, geroy, price),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Sotib olish", callback_data=f"market-geroy-buy_{geroy.id}_{price}")]
                ]),
                parse_mode="HTML"
            )
            entry.channel_message_id = sent.message_id
            await entry.save(update_fields=["channel_message_id"])
        except Exception:
            pass
    return entry


async def cancel_market_listing(entry: GeroyMarket, bot: Bot) -> None:
    """Faol e'lonni bekor qiladi. Kanaldagi xabarni iloji bo'lsa tahrirlaydi."""
    entry.status = "cancelled"
    await entry.save(update_fields=["status", "updated_at"])
    if entry.channel_message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=GEROY_MARKET_CHANNEL_ID,
                message_id=entry.channel_message_id,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Sotuvdan olindi", callback_data="market-geroy-gone")]]),
            )
        except Exception:
            pass


async def update_market_listing_price(entry: GeroyMarket, new_price: int, bot: Bot) -> None:
    """Faol e'lon narxini o'zgartiradi. Kanaldagi xabarni iloji bo'lsa yangi narx bilan tahrirlaydi."""
    entry.price = new_price
    await entry.save(update_fields=["price", "updated_at"])
    if entry.channel_message_id:
        try:
            geroy = await Geroys.get(id=entry.geroy_id)
            seller = await User.get(id=entry.user_id)
            label = seller_label_for(seller)
            await bot.edit_message_text(
                chat_id=GEROY_MARKET_CHANNEL_ID,
                message_id=entry.channel_message_id,
                text=_geroy_market_channel_text(label, geroy, new_price),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Sotib olish", callback_data=f"market-geroy-buy_{geroy.id}_{new_price}")]
                ]),
                parse_mode="HTML",
            )
        except Exception:
            pass


async def execute_purchase(entry: GeroyMarket, buyer_user: User, bot: Bot) -> dict:
    """GeroyMarket yozuvini sotib olish jarayonini bajaradi — bot callback'i va webapp
    endpoint'i uchun umumiy. Natija: {"ok": True, "geroy": ..., "price": ...} yoki
    {"ok": False, "error": "<code>"}."""
    await entry.fetch_related("user", "geroy")
    if entry.status != "active":
        return {"ok": False, "error": "sold_or_not_exist"}

    if buyer_user.id == entry.user.id:
        return {"ok": False, "error": "cannot_buy_own"}

    buyer_profile, _created = await Profile.get_or_create(user=buyer_user)
    if buyer_profile.diamond < entry.price:
        return {"ok": False, "error": "not_enough_diamond"}

    if await Geroys.filter(user=buyer_user).exists():
        return {"ok": False, "error": "already_have_one"}

    seller_user = entry.user
    seller_profile, _created = await Profile.get_or_create(user=seller_user)
    geroy = entry.geroy
    price = entry.price

    buyer_profile.diamond -= price
    seller_profile.diamond += price - 5

    await buyer_profile.save()
    await seller_profile.save()

    geroy.user = buyer_user
    await geroy.save()

    entry.status = "sold"
    entry.is_sold = True
    await entry.save(update_fields=["status", "is_sold", "updated_at"])

    bought_label = "✅ Sotib olindi"
    if entry.channel_message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=GEROY_MARKET_CHANNEL_ID,
                message_id=entry.channel_message_id,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=bought_label, callback_data="bought")]]),
            )
        except Exception:
            pass

    notify_target = seller_user.user_id if seller_user.user_id < GEROY_SHOP_SYSTEM_USER_ID else (ADMINS[0] if ADMINS else None)
    if notify_target:
        try:
            await bot.send_message(notify_target, f"Sizning geroyingiz {buyer_user.full_name} tomonidan {price} 💍 ga sotib olindi.")
        except Exception:
            pass

    return {"ok": True, "geroy": geroy, "price": price, "bought_label": bought_label, "buyer_profile": buyer_profile}


async def add_my_geroy_market(call: CallbackQuery, state: FSMContext):
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        return
    geroy = await Geroys.filter(user=user).first()

    if not geroy:
        await call.answer("Sizda Geroy mavjud emas!", show_alert=True)
        return

    geroy_market_entry = await GeroyMarket.get_or_none(geroy=geroy, status="active")
    if geroy_market_entry:
        await call.answer("Sizning geroyingiz allaqachon Geroy Marketda mavjud.", show_alert=True)
        return

    await state.set_state(GeroyMarketPrice.waiting_for_price)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await call.message.answer("Savdodan 5 💎 ushlab qolinadi shuni hisobga olib geroy narxini yuboring:\n\nMasalan: 90", reply_markup=keyboard)
    await call.answer()

async def process_geroy_market_price(message: Message, state: FSMContext):
    user = await User.get_or_none(user_id=message.from_user.id)
    if not user:
        return
    geroy = await Geroys.filter(user=user).first()

    if message.text.lower() == "bekor qilish":
        await message.answer("Geroy Marketga qo'shish bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos, to'g'ri narx kiriting (musbat butun son).")
        return

    if price < 20:
        await message.answer("Geroyingiz narxi kamida 20 💎 bo'lishi kerak.")
        return

    geroy_market_entry = await GeroyMarket.get_or_none(geroy=geroy, status="active")
    if geroy_market_entry:
        await message.answer("Sizning geroyingiz allaqachon Geroy Marketda mavjud.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    username_text = f"@{message.from_user.username}" if message.from_user.username else "username yo'q"
    seller_label = f"{message.from_user.full_name} ({username_text})"
    await create_market_listing(user, geroy, price, message.bot, seller_label=seller_label)

    await message.answer("Sizning geroyingiz Geroy Marketga muvaffaqiyatli qo'shildi!", reply_markup=ReplyKeyboardRemove())
    await message.answer("Bozorga o'tish uchun tugmani bosing:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Geroy Marketga o'tish", url=GEROY_MARKET_CHANNEL_URL)]
    ]))
    await state.clear()

async def buy_geroy_market(call: CallbackQuery, bot: Bot):
    parts = call.data.split("_")
    geroy_id = int(parts[1])

    buyer_user = await User.get_or_none(user_id=call.from_user.id)
    if not buyer_user:
        return

    entry = await GeroyMarket.get_or_none(geroy_id=geroy_id, status="active").prefetch_related("user", "geroy")
    if not entry:
        await call.answer("Bu geroy allaqachon sotilgan yoki mavjud emas.", show_alert=True)
        return

    if not entry.channel_message_id and call.message:
        entry.channel_message_id = call.message.message_id
        await entry.save(update_fields=["channel_message_id"])

    result = await execute_purchase(entry, buyer_user, bot)
    if not result["ok"]:
        error_msg = {
            "sold_or_not_exist": "Bu geroy allaqachon sotilgan yoki mavjud emas.",
            "cannot_buy_own": "Siz o'zingizning geroyingizni sotib ololmaysiz.",
            "not_enough_diamond": "Sizda yetarli miqdorda 💍 yo'q.",
            "already_have_one": "Sizda geroy mavjud. Sotib olish uchun avval o'zingiznikini boshqa kimgadir o'tkazib turishni maslahat beramiz!",
        }.get(result["error"], "Bu geroy allaqachon sotilgan yoki mavjud emas.")
        await call.answer(error_msg, show_alert=True)
        return

    await call.answer(result["bought_label"], show_alert=True)
    await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=result["bought_label"], callback_data="bought")]
    ]))

async def stats_geroy_market(message: Message):
    if message.from_user.id not in ADMINS:
        return
    total_listings = await GeroyMarket.all().count()
    sold_listings = await GeroyMarket.filter(status="sold").count()
    unsold_listings = await GeroyMarket.filter(status="active").count()

    await message.answer(
        f"Geroy Market Statistikasi:\n\n"
        f"📊 Jami e'lonlar: {total_listings} ta\n"
        f"✅ Sotilgan geroylar: {sold_listings} ta\n"
        f"⏳ Sotilayotgan geroylar: {unsold_listings} ta"
    )
