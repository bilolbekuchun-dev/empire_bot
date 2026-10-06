"""NFT (sovg'a) market — admin shaxsiy Telegram hisobiga ulangan userbot (Telethon)
orqali Telegram sovg'alar katalogidan xarid qilib, xaridorga yuboradi.

Muhim cheklov: userbot faqat @username orqali odamni topa oladi (bare user_id bilan
ishlamaydi, chunki userbot hisobi o'sha odam bilan hech qachon aloqada bo'lmagan).
Shuning uchun xaridorda Telegram username bo'lishi shart."""

import asyncio
try:
    import fcntl
except ImportError:
    fcntl = None
import gzip
import json
import logging
import os

from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError
from telethon.tl.functions.payments import (
    GetStarGiftsRequest,
    GetResaleStarGiftsRequest,
    GetPremiumGiftCodeOptionsRequest,
    GetPaymentFormRequest,
    SendStarsFormRequest,
    GetStarsStatusRequest,
)
from telethon.tl.types import (
    InputInvoiceStarGift, InputInvoiceStarGiftResale, InputInvoicePremiumGiftStars, InputPeerSelf,
    DocumentAttributeFilename, TextWithEntities,
    StarGiftAttributeModel, StarsAmount,
)

from config import TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH, TELEGRAM_USERBOT_SESSION
from models.user import (
    NftGiftCatalog, NftPurchaseLog, NftMarketSettings, NftResaleListing, NftResalePurchaseLog,
    PremiumGiftOption, PremiumPurchaseLog,
)

STICKER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "nft_stickers")
RESALE_STICKER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "nft_resale_stickers")

_client: TelegramClient | None = None
_client_lock = asyncio.Lock()

# Sherif2 va Empire bitta haqiqiy Telegram hisobini (ikkita alohida sessiya orqali)
# ishlatadi. Telegram cheklovlari (FloodWait) hisob darajasida qo'llanadi, shuning
# uchun ikkala BOT PROCESSI bir vaqtda xarid qilib yubormasligi uchun umumiy,
# jarayonlararo fayl-qulf ishlatiladi — navbat bilan, bittadan xarid.
_GLOBAL_PURCHASE_LOCKFILE = "/root/.nft_userbot_purchase.lock"


async def _acquire_global_purchase_lock():
    if fcntl is None:
        return None
    loop = asyncio.get_event_loop()
    try:
        f = open(_GLOBAL_PURCHASE_LOCKFILE, "a")
        await loop.run_in_executor(None, fcntl.flock, f, fcntl.LOCK_EX)
        return f
    except Exception:
        return None


def _release_global_purchase_lock(f):
    if f is None or fcntl is None:
        return
    try:
        fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass
    finally:
        try:
            f.close()
        except Exception:
            pass


async def get_client() -> TelegramClient:
    """Ulangan Telethon klientini qaytaradi (birinchi chaqiruvda ulanadi, keyin qayta ishlatiladi)."""
    global _client
    async with _client_lock:
        if _client is None:
            _client = TelegramClient(TELEGRAM_USERBOT_SESSION, TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH)
        if not _client.is_connected():
            await _client.connect()
    return _client


async def get_stars_balance() -> int:
    """Userbot hisobidagi qolgan Telegram Stars miqdorini qaytaradi (haqiqiy, umumiy hisob balansi)."""
    client = await get_client()
    result = await client(GetStarsStatusRequest(peer=InputPeerSelf()))
    return result.balance.amount


async def get_budget_status() -> dict:
    """Shu botga ajratilgan Stars byudjeti holatini qaytaradi:
    real hisob balansi, byudjet (agar belgilangan bo'lsa), shu bot sarflagani va qolgani.
    Bir nechta bot bitta haqiqiy Telegram hisobini ishlatganda, har bir bot faqat
    o'ziga ajratilgan miqdordan foydalanishi uchun (haqiqiy hisobda ko'proq qolgan bo'lsa ham)."""
    real_balance = await get_stars_balance()
    settings = await NftMarketSettings.first()
    budget = settings.stars_budget if settings else None

    if budget is None:
        return {"real_balance": real_balance, "budget": None, "spent": 0, "remaining": real_balance, "effective": real_balance}

    sent_logs = await NftPurchaseLog.filter(status="sent")
    total_spent = sum(l.stars_price or 0 for l in sent_logs)
    baseline = settings.spent_baseline or 0
    spent_since_budget_set = max(0, total_spent - baseline)
    remaining_budget = max(0, budget - spent_since_budget_set)
    effective = min(real_balance, remaining_budget)
    return {"real_balance": real_balance, "budget": budget, "spent": spent_since_budget_set, "remaining": remaining_budget, "effective": effective}


async def get_effective_stars_balance() -> int:
    """Do'kon filtrlash va xarid tekshiruvi uchun ishlatiladigan balans —
    haqiqiy hisob balansi va shu botga ajratilgan byudjetdan kichigi."""
    status = await get_budget_status()
    return status["effective"]


async def sync_catalog() -> int:
    """Telegramning sovg'a katalogini olib, NftGiftCatalog jadvalini yangilaydi.
    Yangi sovg'alar uchun stikerini yuklab, JSON (Lottie) shaklida saqlaydi.
    Qaytaradi: jami qayta ishlangan sovg'alar soni."""
    os.makedirs(STICKER_DIR, exist_ok=True)
    client = await get_client()
    result = await client(GetStarGiftsRequest(hash=0))

    count = 0
    for g in result.gifts:
        title = None
        for attr in g.sticker.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                title = os.path.splitext(attr.file_name)[0].replace("_", " ").strip()
                break

        # Faqat haqiqatan sotuvda bor (tugamagan) sovg'alar do'konda ko'rinadi.
        is_sold_out = bool(getattr(g, "sold_out", False)) or (g.availability_remains == 0)

        existing = await NftGiftCatalog.get_or_none(gift_id=g.id)
        if existing is None:
            existing = await NftGiftCatalog.create(
                gift_id=g.id, stars_price=g.stars, title=title,
                availability_remains=g.availability_remains, availability_total=g.availability_total,
                is_active=not is_sold_out,
            )
        else:
            existing.stars_price = g.stars
            existing.availability_remains = g.availability_remains
            existing.availability_total = g.availability_total
            if title and not existing.title:
                existing.title = title
            existing.is_active = not is_sold_out
            await existing.save(update_fields=["stars_price", "title", "availability_remains", "availability_total", "is_active"])

        if not existing.sticker_path:
            # Avval statik rasm (thumbnail)ni sinab ko'ramiz — bu Lottie animatsiyadan
            # ANCHA yengil (webapp sekinlashmasligi uchun eng muhim narsa).
            jpg_file = os.path.join(STICKER_DIR, f"{g.id}.jpg")
            json_file = os.path.join(STICKER_DIR, f"{g.id}.json")
            saved_ext = None
            if not os.path.exists(jpg_file) and not os.path.exists(json_file):
                try:
                    thumb_bytes = await client.download_media(g.sticker, file=bytes, thumb=-1)
                    if thumb_bytes:
                        with open(jpg_file, "wb") as f:
                            f.write(thumb_bytes)
                        saved_ext = "jpg"
                except Exception as e:
                    logging.info(f"NFT statik rasm topilmadi (gift_id={g.id}): {e}")

                if not saved_ext:
                    try:
                        raw = await client.download_media(g.sticker, file=bytes)
                        lottie_json = gzip.decompress(raw)
                        with open(json_file, "wb") as f:
                            f.write(lottie_json)
                        saved_ext = "json"
                    except Exception as e:
                        logging.warning(f"NFT sticker download xato (gift_id={g.id}): {e}")
                        continue
            elif os.path.exists(jpg_file):
                saved_ext = "jpg"
            elif os.path.exists(json_file):
                saved_ext = "json"

            existing.sticker_path = f"/webapp/uploads/nft_stickers/{g.id}.{saved_ext}"
            await existing.save(update_fields=["sticker_path"])

        count += 1

    return count


async def sync_resale_listings() -> int:
    """Telegramning "Collectibles" (noyob, boshqa foydalanuvchilar qayta sotuvga
    qo'ygan) sovg'alarini sinxronlaydi. Faqat Stars orqali sotib olinadigan
    (TON-only bo'lmagan) nusxalar olinadi (stars_only=True). Har bir limitli asosiy
    sovg'a turi (base gift) bo'yicha alohida so'rov yuboriladi.
    Qaytaradi: jami topilgan noyob nusxalar soni."""
    os.makedirs(RESALE_STICKER_DIR, exist_ok=True)
    client = await get_client()

    base_gift_ids = await NftGiftCatalog.filter(availability_total__not_isnull=True).values_list("gift_id", flat=True)

    count = 0
    for base_id in base_gift_ids:
        try:
            result = await client(GetResaleStarGiftsRequest(
                gift_id=base_id, offset="", limit=20, sort_by_price=True, stars_only=True,
            ))
        except Exception as e:
            logging.info(f"Resale ro'yxati olinmadi (base_gift_id={base_id}): {e}")
            continue

        for g in result.gifts:
            slug = getattr(g, "slug", None)
            unique_id = getattr(g, "id", None)
            if not slug or not unique_id:
                continue

            stars_price = None
            for amt in (getattr(g, "resell_amount", None) or []):
                if isinstance(amt, StarsAmount):
                    stars_price = amt.amount
                    break
            if stars_price is None:
                continue  # faqat TON evaziga sotilyapti — o'tkazib yuboramiz

            model_doc = None
            for attr in (getattr(g, "attributes", None) or []):
                if isinstance(attr, StarGiftAttributeModel):
                    model_doc = attr.document
                    break

            # Ba'zi noyob buyumlar bir nechta asosiy tur so'rovida qaytishi mumkin —
            # shuning uchun unique_id/slug bo'yicha xavfsiz upsert qilamiz.
            existing = await NftResaleListing.get_or_none(unique_id=unique_id)
            if existing is None:
                existing = await NftResaleListing.get_or_none(slug=slug)
            if existing is None:
                try:
                    existing = await NftResaleListing.create(
                        base_gift_id=base_id, unique_id=unique_id, slug=slug,
                        title=g.title, num=getattr(g, "num", None), stars_price=stars_price,
                    )
                except Exception:
                    existing = await NftResaleListing.get_or_none(unique_id=unique_id) or await NftResaleListing.get_or_none(slug=slug)
                    if existing is None:
                        continue
                    existing.stars_price = stars_price
                    existing.is_active = True
                    await existing.save(update_fields=["stars_price", "is_active"])
            else:
                existing.stars_price = stars_price
                existing.is_active = True
                await existing.save(update_fields=["stars_price", "is_active"])

            if not existing.sticker_path and model_doc is not None:
                jpg_file = os.path.join(RESALE_STICKER_DIR, f"{unique_id}.jpg")
                if not os.path.exists(jpg_file):
                    try:
                        thumb_bytes = await client.download_media(model_doc, file=bytes, thumb=-1)
                        if thumb_bytes:
                            with open(jpg_file, "wb") as f:
                                f.write(thumb_bytes)
                    except Exception as e:
                        logging.info(f"Resale rasm topilmadi (unique_id={unique_id}): {e}")
                if os.path.exists(jpg_file):
                    existing.sticker_path = f"/webapp/uploads/nft_resale_stickers/{unique_id}.jpg"
                    await existing.save(update_fields=["sticker_path"])

            count += 1

    return count


async def buy_resale_gift(username: str, slug: str) -> tuple[bool, str | None]:
    """Noyob (Collectible) sovg'ani slug orqali Stars evaziga sotib olib, @username'ga yuboradi."""
    lockfile = await _acquire_global_purchase_lock()
    try:
        client = await get_client()
        try:
            recipient = await client.get_entity(username)
        except UsernameNotOccupiedError:
            return False, "username_not_found"
        except ValueError as e:
            if "No user has" in str(e):
                return False, "username_not_found"
            return False, f"resolve_error: {e}"
        except Exception as e:
            return False, f"resolve_error: {e}"

        try:
            peer = await client.get_input_entity(recipient)
            invoice = InputInvoiceStarGiftResale(slug=slug, to_id=peer, ton=False)
            form = await client(GetPaymentFormRequest(invoice=invoice))
            await client(SendStarsFormRequest(form_id=form.form_id, invoice=invoice))
            return True, None
        except Exception as e:
            logging.warning(f"Resale gift yuborishda xato (slug={slug}, to={username}): {e}")
            return False, str(e)
    finally:
        _release_global_purchase_lock(lockfile)


async def sync_premium_options() -> int:
    """Telegram Premium'ni Stars evaziga sovg'a qilish variantlarini (masalan 3/6/12 oy)
    sinxronlaydi. Qaytaradi: topilgan variantlar soni."""
    client = await get_client()
    result = await client(GetPremiumGiftCodeOptionsRequest())

    count = 0
    for opt in result:
        if getattr(opt, "currency", None) != "XTR":
            continue  # faqat Stars (XTR) evaziga sotiladigan variantlar

        existing = await PremiumGiftOption.get_or_none(months=opt.months)
        if existing is None:
            await PremiumGiftOption.create(months=opt.months, stars_price=opt.amount)
        else:
            existing.stars_price = opt.amount
            await existing.save(update_fields=["stars_price"])
        count += 1

    return count


async def buy_premium_gift(username: str, months: int) -> tuple[bool, str | None]:
    """Telegram Premium obunasini (months oylik) Stars evaziga sotib olib, @username'ga sovg'a qiladi."""
    lockfile = await _acquire_global_purchase_lock()
    try:
        client = await get_client()
        try:
            recipient = await client.get_entity(username)
        except UsernameNotOccupiedError:
            return False, "username_not_found"
        except ValueError as e:
            if "No user has" in str(e):
                return False, "username_not_found"
            return False, f"resolve_error: {e}"
        except Exception as e:
            return False, f"resolve_error: {e}"

        try:
            user_input = await client.get_input_entity(recipient)
            invoice = InputInvoicePremiumGiftStars(
                user_id=user_input, months=months,
                message=TextWithEntities(text="EMPIRE MARKET", entities=[]),
            )
            form = await client(GetPaymentFormRequest(invoice=invoice))
            await client(SendStarsFormRequest(form_id=form.form_id, invoice=invoice))
            return True, None
        except Exception as e:
            logging.warning(f"Premium gift yuborishda xato (months={months}, to={username}): {e}")
            return False, str(e)
    finally:
        _release_global_purchase_lock(lockfile)


async def buy_and_send_gift(username: str, gift_id: int) -> tuple[bool, str | None]:
    """Berilgan sovg'ani (gift_id) Stars evaziga sotib olib, @username'ga yuboradi.
    Qaytaradi: (muvaffaqiyat, xato_matni_yoki_None).
    Sherif2 va Empire bitta hisobni ishlatgani uchun, xaridlar jarayonlararo
    qulf orqali navbat bilan (bir vaqtning o'zida bittadan) amalga oshiriladi."""
    lockfile = await _acquire_global_purchase_lock()
    try:
        client = await get_client()
        try:
            recipient = await client.get_entity(username)
        except UsernameNotOccupiedError:
            return False, "username_not_found"
        except ValueError as e:
            if "No user has" in str(e):
                return False, "username_not_found"
            return False, f"resolve_error: {e}"
        except Exception as e:
            return False, f"resolve_error: {e}"

        try:
            peer = await client.get_input_entity(recipient)
            invoice = InputInvoiceStarGift(
                peer=peer, gift_id=gift_id,
                message=TextWithEntities(text="EMPIRE MARKET", entities=[]),
            )
            form = await client(GetPaymentFormRequest(invoice=invoice))
            await client(SendStarsFormRequest(form_id=form.form_id, invoice=invoice))
            return True, None
        except Exception as e:
            logging.warning(f"NFT gift yuborishda xato (gift_id={gift_id}, to={username}): {e}")
            return False, str(e)
    finally:
        _release_global_purchase_lock(lockfile)
