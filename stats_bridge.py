"""
💱 stats_bridge.py — @empire_statsbot bilan pul almashuvi (aiogram 3.21 + Tortoise ORM 0.25)

Hamkor botga qo'shiladi. Ikki tomonlama:
  • Kiruvchi: stats bot sizning foydalanuvchiga $ qo'shadi  → POST /exchange/credit
  • Chiquvchi: profil → "💱 Stats puli" → 💵 dollar (1:1) yoki 💎 olmos (1 olmos = 1000$) yuboriladi

Railway Variables (hamkor bot):
  EXCHANGE_SECRET = <son_bot dagi EXCHANGE_SECRET bilan AYNAN bir xil>
  STATS_URL       = https://sonbot-production.up.railway.app
  PORT            = Railway o'zi beradi

Faqat ⚙️ belgili 3 joyni o'z modelingizga moslang (User modeli va dollar/olmos maydonlari).
"""
import os, json, time, hmac, hashlib, uuid, logging

import aiohttp
from aiohttp import web
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from tortoise import fields
from tortoise.models import Model
from tortoise.expressions import F as TF
from tortoise.transactions import in_transaction

log = logging.getLogger("stats_bridge")
SECRET = os.getenv("EXCHANGE_SECRET", "").encode()
STATS_URL = os.getenv("STATS_URL", "").rstrip("/")
TS_WINDOW = 300
DIAMOND_RATE = 1000          # 1 olmos = 1000 stats $
DOLLAR_AMOUNTS = [100, 500, 1000, 5000]
DIAMOND_AMOUNTS = [1, 3, 5, 10]

# ⚙️ 1) O'z User modelingizni import qiling va maydon nomlarini yozing
from models.user import User, Profile    # ← sizning modelingiz
USER_ID_FIELD = "user_id"                # Telegram ID saqlanadigan maydon (yoki "id")
DOLLAR_FIELD = "dollar"                  # ⚙️ 2) dollar maydoni (Profile modelida)
DIAMOND_FIELD = "diamond"                # ⚙️ 3) olmos maydoni (Profile modelida)


class ExchangeTxn(Model):
    """Idempotentlik: har txid bir marta. Tortoise generate_schemas() jadvalni o'zi yaratadi.
    Tortoise.init(modules={"models": ["models", "stats_bridge"]}) ga shu modulni qo'shing."""
    txid = fields.CharField(max_length=80, pk=True)
    direction = fields.CharField(max_length=3)     # "in" / "out"
    user_id = fields.BigIntField()
    amount = fields.BigIntField()                  # stats $ ekvivalenti
    status = fields.CharField(max_length=10, default="done")   # done / pending / refunded
    created_at = fields.IntField(default=lambda: int(time.time()))

    class Meta:
        table = "exchange_txns"


def sign(body: bytes) -> str:
    return hmac.new(SECRET, body, hashlib.sha256).hexdigest()


def _where(uid):
    return {USER_ID_FIELD: uid}


# ───────────────────────── Kiruvchi: POST /exchange/credit ─────────────────────────

async def _credit(request: web.Request):
    raw = await request.read()
    if not SECRET or not hmac.compare_digest(request.headers.get("X-Signature", ""), sign(raw)):
        return web.json_response({"ok": False, "error": "bad_signature"}, status=401)
    try:
        d = json.loads(raw)
        txid, uid, amount, ts = str(d["txid"])[:80], int(d["user_id"]), int(d["amount"]), int(d["ts"])
    except Exception:
        return web.json_response({"ok": False, "error": "bad_json"}, status=400)
    if abs(time.time() - ts) > TS_WINDOW:
        return web.json_response({"ok": False, "error": "stale"}, status=401)
    if amount <= 0:
        return web.json_response({"ok": False, "error": "bad_amount"}, status=400)
    async with in_transaction():
        if await ExchangeTxn.filter(txid=txid).exists():
            user = await User.get_or_none(**_where(uid))
            profile = await Profile.filter(user=user).first() if user else None
            return web.json_response({"ok": True, "duplicate": True,
                                      "balance": getattr(profile, DOLLAR_FIELD, 0) if profile else 0})
        user = await User.get_or_none(**_where(uid))
        if not user:
            return web.json_response({"ok": False, "error": "no_user"}, status=404)
        profile = await Profile.filter(user=user).first()
        if not profile:
            return web.json_response({"ok": False, "error": "no_profile"}, status=404)
        await Profile.filter(user=user).update(**{DOLLAR_FIELD: TF(DOLLAR_FIELD) + amount})
        await ExchangeTxn.create(txid=txid, direction="in", user_id=uid, amount=amount)
        profile = await Profile.filter(user=user).first()

    # Get user language for localized message
    lang = "uz"
    try:
        if user:
            from utils.i18n import clean_lang
            lang = clean_lang(user.lang)
    except Exception:
        pass

    from utils.i18n import clean_lang, STATS_LABELS
    l = clean_lang(lang)
    lbls = STATS_LABELS.get(l, STATS_LABELS["uz"])

    try:
        await request.app["bot"].send_message(uid, lbls["credit_received"].format(amount=amount), parse_mode="HTML")
    except Exception:
        pass
    return web.json_response({"ok": True, "balance": getattr(profile, DOLLAR_FIELD)})


async def _ping(_):
    return web.json_response({"ok": True})


async def start_bridge(bot, port: int | None = None):
    """Bot ishga tushganda (masalan dp.startup da) bir marta chaqiring."""
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/exchange/credit", _credit)
    app.router.add_get("/exchange/ping", _ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port or int(os.getenv("PORT", "8080"))).start()
    log.info("Stats bridge ishga tushdi")


# ───────────────────────── Chiquvchi: stats botga yuborish ─────────────────────────

async def _post_stats(txid, uid, stats_dollars):
    """Qaytaradi: "ok" | "rejected" | "unknown"."""
    body = json.dumps({"txid": txid, "user_id": uid, "amount": stats_dollars, "ts": int(time.time())}).encode()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.post(STATS_URL + "/exchange/credit", data=body,
                              headers={"Content-Type": "application/json", "X-Signature": sign(body)}) as r:
                data = await r.json(content_type=None)
                if r.status == 200 and data.get("ok"):
                    return "ok"
                return "rejected" if 400 <= r.status < 500 else "unknown"
    except Exception as e:
        log.warning("stats bridge: %s", e)
        return "unknown"


async def send_to_stats(uid: int, kind: str, qty: int) -> str:
    """kind: "usd" yoki "dia". Pulni atomik yechib yuboradi; rad etilsa qaytaradi."""
    field = DOLLAR_FIELD if kind == "usd" else DIAMOND_FIELD
    stats_dollars = qty if kind == "usd" else qty * DIAMOND_RATE
    txid = f"vento-{uuid.uuid4().hex}"
    async with in_transaction():
        user = await User.get_or_none(**_where(uid))
        if not user:
            return "funds"
        profile = await Profile.filter(user=user).first()
        if not profile:
            return "funds"
        n = await Profile.filter(user=user, **{f"{field}__gte": qty}).update(**{field: TF(field) - qty})
        if not n:
            return "funds"
        await ExchangeTxn.create(txid=txid, direction="out", user_id=uid, amount=stats_dollars, status="pending")
    res = await _post_stats(txid, uid, stats_dollars)
    if res == "unknown":                      # bir marta o'sha txid bilan qayta urinamiz (stats idempotent)
        res = await _post_stats(txid, uid, stats_dollars)
    if res == "ok":
        await ExchangeTxn.filter(txid=txid).update(status="done")
    elif res == "rejected":
        async with in_transaction():
            user = await User.get_or_none(**_where(uid))
            if user:
                await Profile.filter(user=user).update(**{field: TF(field) + qty})
            await ExchangeTxn.filter(txid=txid).update(status="refunded")
    return res          # "unknown" — pending qoladi; retry_pending() keyin hal qiladi


async def retry_pending():
    """Ixtiyoriy: har bir necha daqiqada chaqiring — noaniq o'tkazmalarni qayta yuboradi."""
    for t in await ExchangeTxn.filter(direction="out", status="pending"):
        if await _post_stats(t.txid, t.user_id, t.amount) == "ok":
            await ExchangeTxn.filter(txid=t.txid).update(status="done")


# ───────────────────────── "💱 Stats puli" tugmasi (aiogram Router) ─────────────────────────

router = Router()


def stats_button(lang: str = "uz"):
    """Profil klaviaturangizga qo'shing: [stats_button(lang)]"""
    from utils.i18n import clean_lang, STATS_LABELS
    l = clean_lang(lang)
    lbls = STATS_LABELS.get(l, STATS_LABELS["uz"])
    return InlineKeyboardButton(text=lbls["btn_stats"], callback_data="sx:menu")


@router.callback_query(F.data == "sx:menu")
async def sx_menu(q: CallbackQuery):
    from utils.i18n import clean_lang, STATS_LABELS
    lang = "uz"
    try:
        from models.user import User
        user = await User.get_or_none(user_id=q.from_user.id)
        if user:
            lang = clean_lang(user.lang)
    except Exception:
        pass

    l = clean_lang(lang)
    lbls = STATS_LABELS.get(l, STATS_LABELS["uz"])

    kb = [[InlineKeyboardButton(text=f"💵 {a}$", callback_data=f"sx:usd:{a}") for a in DOLLAR_AMOUNTS],
          [InlineKeyboardButton(text=f"💎 {a}", callback_data=f"sx:dia:{a}") for a in DIAMOND_AMOUNTS]]
    await q.message.answer(
        lbls["menu_title"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    await q.answer()


@router.callback_query(F.data.startswith("sx:"))
async def sx_send(q: CallbackQuery):
    from utils.i18n import clean_lang, STATS_LABELS
    lang = "uz"
    try:
        from models.user import User
        user = await User.get_or_none(user_id=q.from_user.id)
        if user:
            lang = clean_lang(user.lang)
    except Exception:
        pass

    l = clean_lang(lang)
    lbls = STATS_LABELS.get(l, STATS_LABELS["uz"])

    _, kind, qty = q.data.split(":")
    res = await send_to_stats(q.from_user.id, kind, int(qty))
    text = {"ok": lbls["sent_ok"],
            "funds": lbls["sent_funds"],
            "rejected": lbls["sent_rejected"],
            "unknown": lbls["sent_unknown"]}[res]
    await q.answer(text, show_alert=True)
