import os
import json
import logging
from datetime import datetime, date, timedelta, timezone
from urllib.parse import parse_qs, unquote
from aiohttp import web

from tortoise.expressions import Q
from tortoise.functions import Sum, Count

from config import ADMINS
from models.user import (
    User, Profile, ActiveRole, VipUser, Paralar, Transfers,
    SupportMessage, SupportConversationState, Blocked_user,
    NftGiftCatalog, NftPurchaseLog, NftResaleListing, NftResalePurchaseLog,
    PremiumGiftOption, PremiumPurchaseLog
)
from models.game_data import Chat, Game, GamePlayer, Geroys
from models.user import GeroyMarket
from utils.paralar import _has_active_para
from utils.webapp_i18n import get_ui_strings

logger = logging.getLogger(__name__)

@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex
        except Exception as e:
            logger.exception(f"Unhandled API Exception: {e}")
            response = web.json_response({"ok": False, "error": str(e)}, status=500)
    
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    return response


def extract_user_id_from_payload(payload: dict) -> int | None:
    """Payload dan user_id ni aniqlash"""
    if not isinstance(payload, dict):
        return None
    
    # Direct user_id
    uid = payload.get("user_id") or payload.get("telegram_id") or payload.get("tg_id")
    if uid:
        try:
            return int(uid)
        except (ValueError, TypeError):
            pass

    # initData parse
    init_data = payload.get("initData")
    if init_data and isinstance(init_data, str):
        try:
            parsed = parse_qs(init_data)
            if "user" in parsed:
                u_data = json.loads(parsed["user"][0])
                if "id" in u_data:
                    return int(u_data["id"])
        except Exception:
            pass

    return None


async def get_db_user_and_profile(user_id: int):
    """Foydalanuvchi va profilini olish yoki yaratish"""
    user = await User.get_or_none(user_id=user_id)
    if not user:
        return None, None
    profile, _ = await Profile.get_or_create(user=user, defaults={"dollar": 0, "diamond": 0})
    return user, profile


ITEM_PRICES = {
    "himoya": {"currency": "dollar", "price": 100},
    "hujjat": {"currency": "dollar", "price": 100},
    "osishdan_himoya": {"currency": "diamond", "price": 5},
    "miltiq": {"currency": "diamond", "price": 5},
    "doridan_himoya": {"currency": "dollar", "price": 100},
    "maska": {"currency": "dollar", "price": 100},
    "qotildan_himoya": {"currency": "diamond", "price": 5},
    "slip_himoya": {"currency": "diamond", "price": 5},
    "geroy_himoya": {"currency": "diamond", "price": 5},
}


# ── Telegram Stars narxlari (webapp frontend bilan bir xil bo'lishi SHART) ──
DIAMOND_STAR_PACKS = {10: 70, 30: 200, 70: 450, 250: 1300}
DOLLAR_STAR_PACKS = {1000: 7, 10000: 70, 30000: 200}
DIAMOND_STAR_RATE = 7        # custom: 1 💎 = 7 ⭐
DOLLAR_STAR_PER = 1000       # custom: 1000 💵 = 7 ⭐
DOLLAR_STAR_RATE = 7
MIN_CUSTOM_DIAMOND = 1
MIN_CUSTOM_DOLLAR = 100

VIP_DIAMOND_PRICES = {7: 8, 14: 15, 30: 30}
VIP_STAR_PRICES = {7: 50, 14: 100, 30: 200}


def profile_payload(profile) -> dict:
    """Frontend kutadigan 'profile' obyekti (profile_handler bilan bir xil shakl)."""
    return {
        "dollar": profile.dollar,
        "diamond": profile.diamond,
        "wins": profile.wins,
        "games_count": profile.games_count,
        "himoya": profile.himoya,
        "hujjat": profile.hujjat,
        "qotildan_himoya": profile.qotildan_himoya,
        "osishdan_himoya": profile.osishdan_himoya,
        "miltiq": profile.miltiq,
        "doridan_himoya": profile.doridan_himoya,
        "maska": profile.maska,
        "slip_himoya": profile.slip_himoya,
        "geroy_himoya": profile.geroy_himoya,
    }


def _clean_role_key(role: str) -> str:
    """"🕵🏼 Komissar katani" -> "Komissar katani" (emoji ni olib tashlash)"""
    if " " in role:
        return role.split(" ", 1)[1].strip()
    return role


def build_roles_catalog() -> list:
    """WebApp "O'yin rollari" bo'limi uchun katalog (tinch/mafia/yakka)."""
    from config import tinch_rollar, mafia_rollar, yakka_rollar
    from utils.roles_text import Roles as RolesText

    def entry(role, team):
        return {
            "name": role,
            "team": team,
            "role_key": _clean_role_key(role),
            "elite": False,
            "description": RolesText.get_description(role),
        }

    return (
        [entry(r, "tinch") for r in tinch_rollar]
        + [entry(r, "mafia") for r in mafia_rollar]
        + [entry(r, "yakka") for r in yakka_rollar]
    )


def build_shop_items() -> list:
    """Build item shop list (himoya, hujjat, qotildan_himoya, osishdan_himoya, miltiq, doridan_himoya, maska, slip_himoya, geroy_himoya)"""
    return [
        {"key": "himoya", "label": "🛡 Tinch axoli himoyasi", "price": 100, "currency": "dollar", "elite": False},
        {"key": "hujjat", "label": "📜 Hujjat", "price": 100, "currency": "dollar", "elite": False},
        {"key": "qotildan_himoya", "label": "🔪 Qotildan himoya", "price": 5, "currency": "diamond", "elite": True},
        {"key": "osishdan_himoya", "label": "🔒 Osishdan himoya", "price": 5, "currency": "diamond", "elite": True},
        {"key": "miltiq", "label": "🔫 Miltiq", "price": 5, "currency": "diamond", "elite": False},
        {"key": "doridan_himoya", "label": "💊 Doridan himoya", "price": 100, "currency": "dollar", "elite": False},
        {"key": "maska", "label": "🎭 Niqob (Maska)", "price": 100, "currency": "dollar", "elite": False},
        {"key": "slip_himoya", "label": "📜 Sirpanishdan himoya", "price": 5, "currency": "diamond", "elite": False},
        {"key": "geroy_himoya", "label": "📦 Geroydan himoya", "price": 5, "currency": "diamond", "elite": False},
    ]


def build_active_role_shop() -> list:
    """Build active role shop list for active enabled roles"""
    import re
    from utils.premium_emojis import get_all_active_roles, role_display
    active_roles = get_all_active_roles()
    role_items = []
    for r in active_roles:
        disp = role_display(r)
        disp_clean = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', str(disp))
        role_items.append({
            "role": r,
            "label": f"🎭 Faol rol: {disp_clean}",
            "price": 10,
            "currency": "diamond",
            "elite": True
        })
    return role_items



def setup_webapp_routes(app: web.Application, static_dir: str, bot=None):
    app.middlewares.append(cors_middleware)
    index_path = os.path.join(static_dir, "index.html")

    if os.path.exists(static_dir):
        app.router.add_static("/static/", path=static_dir, name="static")

    async def index_handler(request):
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
        if os.path.exists(index_path):
            return web.FileResponse(index_path, headers=headers)
        return web.Response(text="WebApp API Server Running", headers=headers)

    app.router.add_get("/", index_handler)
    app.router.add_get("/webapp", index_handler)
    app.router.add_get("/webapp/", index_handler)

    # ── AVATAR HANDLERS ──
    SVG_AVATAR_FALLBACK = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
        '<rect width="100%" height="100%" fill="#1e1e2d"/>'
        '<text x="50%" y="55%" font-size="42" fill="#f0c419" text-anchor="middle" dominant-baseline="middle">👤</text>'
        '</svg>'
    )

    async def avatar_handler(request):
        user_id_str = request.match_info.get("user_id")
        if bot and user_id_str:
            try:
                user_id = int(user_id_str)
                photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
                if photos and photos.total_count > 0 and photos.photos:
                    file_id = photos.photos[0][-1].file_id
                    tg_file = await bot.get_file(file_id)
                    file_url = f"https://api.telegram.org/file/bot{bot.token}/{tg_file.file_path}"
                    return web.HTTPFound(location=file_url)
            except Exception as e:
                logger.debug(f"Failed to fetch avatar for {user_id_str}: {e}")

        return web.Response(text=SVG_AVATAR_FALLBACK, content_type="image/svg+xml")

    async def avatar_chat_handler(request):
        chat_id_str = request.match_info.get("chat_id")
        if bot and chat_id_str:
            try:
                chat_id = int(chat_id_str)
                chat = await bot.get_chat(chat_id=chat_id)
                if chat and chat.photo:
                    tg_file = await bot.get_file(chat.photo.big_file_id)
                    file_url = f"https://api.telegram.org/file/bot{bot.token}/{tg_file.file_path}"
                    return web.HTTPFound(location=file_url)
            except Exception as e:
                logger.debug(f"Failed to fetch chat avatar for {chat_id_str}: {e}")

        return web.Response(text=SVG_AVATAR_FALLBACK, content_type="image/svg+xml")

    app.router.add_get("/webapp/avatar/{user_id}", avatar_handler)
    app.router.add_get("/webapp/avatar_chat/{chat_id}", avatar_chat_handler)

    # ── VERSION ──
    async def version_handler(request):
        return web.json_response({"ok": True, "version": "1.0.0"})
    app.router.add_get("/webapp/api/version", version_handler)
    app.router.add_post("/webapp/api/version", version_handler)

    # ── TOURNAMENT & HOLIDAY ──
    async def tournament_handler(request):
        return web.json_response({
            "ok": True,
            "info": {"title": "Empire Mafia", "active": False},
            "personal": None,
            "next_up": [],
            "history": []
        })
    app.router.add_get("/webapp/api/tournament", tournament_handler)
    app.router.add_post("/webapp/api/tournament", tournament_handler)

    async def holiday_handler(request):
        return web.json_response({
            "ok": True,
            "active": [],
            "upcoming": []
        })
    app.router.add_get("/webapp/api/holiday", holiday_handler)
    app.router.add_post("/webapp/api/holiday", holiday_handler)

    # ── PROFILE ──
    async def profile_handler(request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        
        user_id = extract_user_id_from_payload(payload)
        if not user_id:
            return web.json_response({"ok": False, "error": "user_id_required"}, status=400)

        user, profile = await get_db_user_and_profile(user_id)
        if not user:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        user_lang = getattr(user, "lang", "uz") or "uz"

        # VIP status
        vip = await VipUser.get_or_none(user=user)
        is_vip = bool(vip)

        # Active role
        active_role_obj = await ActiveRole.filter(profile=profile, is_active=True).first()
        active_role = active_role_obj.role if active_role_obj else None

        # Para info
        para_obj = await Paralar.filter(user1=user).prefetch_related("user2").first()
        if not para_obj:
            para_obj = await Paralar.filter(user2=user).prefetch_related("user1").first()

        para_info = None
        if para_obj:
            partner = para_obj.user2 if para_obj.user1_id == user.id else para_obj.user1
            para_info = {
                "partner_id": partner.user_id,
                "partner_name": partner.full_name,
                "partner_username": partner.username,
                "created_at": para_obj.created_at.isoformat() if para_obj.created_at else None
            }

        # Daily reward check
        today = date.today()
        claimed_today = (profile.last_claim_date == today)
        streak = profile.daily_streak or 0
        if streak < 1 or streak > 7:
            streak = 1
        
        DAILY_REWARD_TABLE = { 1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 400, 7: 500 }

        if claimed_today:
            next_streak = streak
            next_reward = DAILY_REWARD_TABLE.get(streak, 100)
        else:
            if profile.last_claim_date == today - timedelta(days=1):
                next_streak = 1 if streak >= 7 else streak + 1
            else:
                next_streak = 1
            next_reward = DAILY_REWARD_TABLE.get(next_streak, 100)

        daily_claim_data = {
            "claimed_today": claimed_today,
            "streak": streak,
            "next_streak": next_streak,
            "next_reward": next_reward,
            "can_claim": not claimed_today,
        }

        # Response payload
        data = {
            "ok": True,
            "user": {
                "id": user.user_id,
                "user_id": user.user_id,
                "full_name": user.full_name,
                "username": user.username,
                "gender": user.gender,
                "gender_changes": user.gender_changes,
                "is_admin": user.user_id in ADMINS,
            },
            "profile": {
                "dollar": profile.dollar,
                "diamond": profile.diamond,
                "wins": profile.wins,
                "games_count": profile.games_count,
                "himoya": profile.himoya,
                "hujjat": profile.hujjat,
                "qotildan_himoya": profile.qotildan_himoya,
                "osishdan_himoya": profile.osishdan_himoya,
                "miltiq": profile.miltiq,
                "doridan_himoya": profile.doridan_himoya,
                "maska": profile.maska,
                "slip_himoya": profile.slip_himoya,
                "geroy_himoya": profile.geroy_himoya,
            },
            "protections": {
                "on_himoya": profile.on_himoya,
                "on_hujjat": profile.on_hujjat,
                "on_qotildan_himoya": profile.on_qotildan_himoya,
                "on_osishdan_himoya": profile.on_osishdan_himoya,
                "on_miltiq": profile.on_miltiq,
                "on_doridan_himoya": profile.on_doridan_himoya,
                "on_maska": profile.on_maska,
                "on_slip_himoya": profile.on_slip_himoya,
                "on_geroy_himoya": profile.on_geroy_himoya,
            },
            "vip": {
                "is_vip": is_vip,
                "duration_days": vip.duration_days if vip else 0,
            },
            "active_role": active_role,
            "daily_claim": daily_claim_data,
            "daily": daily_claim_data,
            "para": para_info,
            "lang": user_lang,
            "ui": get_ui_strings(user_lang),
            "roles": build_roles_catalog(),
            "shop_items": build_shop_items(),
            "active_role_shop": build_active_role_shop(),
        }
        return web.json_response(data)

    app.router.add_post("/webapp/api/profile", profile_handler)

    # ── SET LANGUAGE ──
    async def set_lang_handler(request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        lang = str(payload.get("lang") or "uz")[:8].lower()
        if lang not in ["uz", "ru", "en", "tr"]:
            lang = "uz"
        user_id = extract_user_id_from_payload(payload)
        if user_id:
            await User.filter(user_id=user_id).update(lang=lang)
        return web.json_response({"ok": True, "lang": lang, "ui": get_ui_strings(lang)})

    app.router.add_post("/webapp/api/set_lang", set_lang_handler)

    # ── CLAIM DAILY REWARD ──
    async def claim_daily_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        user, profile = await get_db_user_and_profile(user_id)
        if not user:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        today = date.today()
        if profile.last_claim_date == today:
            return web.json_response({"ok": False, "error": "already_claimed_today"})

        if profile.last_claim_date == today - timedelta(days=1):
            profile.daily_streak = 1 if profile.daily_streak >= 7 else profile.daily_streak + 1
        else:
            profile.daily_streak = 1

        DAILY_REWARD_TABLE = { 1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 400, 7: 500 }
        reward = DAILY_REWARD_TABLE.get(profile.daily_streak, 100)
        profile.dollar += reward
        profile.last_claim_date = today
        await profile.save()

        return web.json_response({
            "ok": True,
            "reward": reward,
            "streak": profile.daily_streak,
            "dollar": profile.dollar,
            "claimed_today": True
        })

    app.router.add_post("/webapp/api/claim_daily", claim_daily_handler)

    # ── TOGGLE PROTECTION ──
    async def toggle_protection_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        item_key = payload.get("item")
        user, profile = await get_db_user_and_profile(user_id)
        if not user or not profile:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        field_name = f"on_{item_key}"
        if hasattr(profile, field_name):
            current_val = getattr(profile, field_name)
            setattr(profile, field_name, not current_val)
            await profile.save()
            return web.json_response({"ok": True, "item": item_key, "value": not current_val})
        
        return web.json_response({"ok": False, "error": "invalid_item"}, status=400)

    app.router.add_post("/webapp/api/toggle_protection", toggle_protection_handler)

    # ── BUY ITEM ──
    async def buy_item_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        item_key = payload.get("item") or payload.get("item_key")
        user, profile = await get_db_user_and_profile(user_id)
        if not user or not profile:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        if item_key not in ITEM_PRICES:
            return web.json_response({"ok": False, "error": "invalid_item"}, status=400)

        cfg = ITEM_PRICES[item_key]
        curr = cfg["currency"]
        price = cfg["price"]

        if curr == "dollar":
            if profile.dollar < price:
                return web.json_response({"ok": False, "error": "not_enough_balance"}, status=400)
            profile.dollar -= price
        else:
            if profile.diamond < price:
                return web.json_response({"ok": False, "error": "not_enough_balance"}, status=400)
            profile.diamond -= price

        current_cnt = getattr(profile, item_key, 0)
        setattr(profile, item_key, current_cnt + 1)
        await profile.save()

        return web.json_response({
            "ok": True,
            "profile": profile_payload(profile),
            "dollar": profile.dollar,
            "diamond": profile.diamond,
            "item": item_key,
            "count": current_cnt + 1
        })

    app.router.add_post("/webapp/api/buy", buy_item_handler)

    # ── BUY ACTIVE ROLE ──
    async def buy_active_role_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        role_name = payload.get("role")
        user, profile = await get_db_user_and_profile(user_id)
        if not user or not profile:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        if not role_name:
            return web.json_response({"ok": False, "error": "role_required"}, status=400)

        price_diamond = 10
        if profile.diamond < price_diamond:
            return web.json_response({"ok": False, "error": "not_enough_balance"}, status=400)

        profile.diamond -= price_diamond
        await profile.save()

        # O'chirish hammasini va yangisini qo'shish
        await ActiveRole.filter(profile=profile).delete()
        await ActiveRole.create(profile=profile, role=role_name, is_active=True)

        active_roles_list = await ActiveRole.filter(profile=profile, is_active=True).all()
        ar_objs = [{"id": ar.id, "role": ar.role, "is_active": ar.is_active} for ar in active_roles_list]

        return web.json_response({
            "ok": True,
            "profile": profile_payload(profile),
            "active_roles": ar_objs,
            "role": role_name,
            "diamond": profile.diamond
        })

    app.router.add_post("/webapp/api/buy_active_role", buy_active_role_handler)

    # ── CONVERT DOLLAR / DIAMOND ──
    async def buy_diamond_with_dollar_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        user, profile = await get_db_user_and_profile(user_id)
        if not user or not profile:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        amount = int(payload.get("amount", 1))
        cost = amount * 1000  # 1 diamond = 1000 dollar
        if profile.dollar < cost:
            return web.json_response({"ok": False, "error": "not_enough_dollar"})

        profile.dollar -= cost
        profile.diamond += amount
        await profile.save()

        return web.json_response({"ok": True, "dollar": profile.dollar, "diamond": profile.diamond})

    app.router.add_post("/webapp/api/buy_diamond_with_dollar", buy_diamond_with_dollar_handler)

    # ── BUY VIP ──
    async def buy_vip_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        user, profile = await get_db_user_and_profile(user_id)
        if not user or not profile:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        cost = 30  # 30 diamond = 30 kun VIP
        if profile.diamond < cost:
            return web.json_response({"ok": False, "error": "not_enough_diamond"})

        profile.diamond -= cost
        await profile.save()

        vip = await VipUser.get_or_none(user=user)
        if vip:
            vip.duration_days += 30
            await vip.save()
        else:
            vip = await VipUser.create(user=user, duration_days=30)

        return web.json_response({"ok": True, "diamond": profile.diamond, "duration_days": vip.duration_days})

    app.router.add_post("/webapp/api/buy_vip", buy_vip_handler)

    # ── LEADERBOARD ──
    async def leaderboard_handler(request):
        try: payload = await request.json()
        except: payload = {}

        lb_type = payload.get("type", "wins")  # wins, dollar, diamond, games
        order_field = f"-{lb_type}" if lb_type in ("wins", "dollar", "diamond", "games_count") else "-wins"

        tops = await Profile.all().prefetch_related("user").order_by(order_field).limit(30)
        
        result = []
        for idx, prof in enumerate(tops, start=1):
            if not prof.user:
                continue
            is_vip = await VipUser.filter(user=prof.user).exists()
            result.append({
                "rank": idx,
                "user_id": prof.user.user_id,
                "name": prof.user.full_name or f"User {prof.user.user_id}",
                "username": prof.user.username,
                "wins": prof.wins,
                "dollar": prof.dollar,
                "diamond": prof.diamond,
                "games_count": prof.games_count,
                "is_vip": is_vip,
            })

        return web.json_response({"ok": True, "leaderboard": result})

    app.router.add_post("/webapp/api/leaderboard", leaderboard_handler)

    # ── HISTORY / TRANSFERS ──
    async def history_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        user, _ = await get_db_user_and_profile(user_id)
        if not user:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        transfers = await Transfers.filter(Q(from_user=user) | Q(to_user=user)).prefetch_related("from_user", "to_user").order_by("-created_at").limit(30)

        items = []
        for t in transfers:
            is_sent = (t.from_user_id == user.id)
            other = t.to_user if is_sent else t.from_user
            items.append({
                "id": t.id,
                "is_sent": is_sent,
                "other_name": other.full_name if other else "Unknown",
                "amount": t.amount,
                "type": t.type,
                "caption": t.caption,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })

        return web.json_response({"ok": True, "history": items})

    app.router.add_post("/webapp/api/history", history_handler)

    # ── TRANSFER ──
    async def transfer_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        user, profile = await get_db_user_and_profile(user_id)
        if not user or not profile:
            return web.json_response({"ok": False, "error": "user_not_found"}, status=404)

        target = payload.get("target")
        amount = int(payload.get("amount", 0))
        t_type = payload.get("type", "dollar")  # dollar / diamond / item

        if amount <= 0:
            return web.json_response({"ok": False, "error": "invalid_amount"})

        targ_user = None
        if isinstance(target, int) or (isinstance(target, str) and target.isdigit()):
            targ_user = await User.get_or_none(user_id=int(target))
        elif isinstance(target, str):
            clean_name = target.lstrip("@").strip()
            targ_user = await User.get_or_none(username__iexact=clean_name)

        if not targ_user:
            return web.json_response({"ok": False, "error": "target_not_found"})

        if targ_user.id == user.id:
            return web.json_response({"ok": False, "error": "cannot_transfer_to_self"})

        targ_profile, _ = await Profile.get_or_create(user=targ_user, defaults={"dollar": 0, "diamond": 0})

        if t_type == "dollar":
            if profile.dollar < amount:
                return web.json_response({"ok": False, "error": "not_enough_dollar"})
            profile.dollar -= amount
            targ_profile.dollar += amount
        elif t_type == "diamond":
            if profile.diamond < amount:
                return web.json_response({"ok": False, "error": "not_enough_diamond"})
            profile.diamond -= amount
            targ_profile.diamond += amount
        else:
            return web.json_response({"ok": False, "error": "invalid_type"})

        await profile.save()
        await targ_profile.save()

        await Transfers.create(
            from_user=user,
            to_user=targ_user,
            amount=amount,
            type=t_type,
            caption="WebApp O'tkazmasi"
        )

        return web.json_response({
            "ok": True,
            "dollar": profile.dollar,
            "diamond": profile.diamond,
            "target_name": targ_user.full_name
        })

    app.router.add_post("/webapp/api/transfer", transfer_handler)

    # ── LOOKUP USER ──
    async def lookup_user_handler(request):
        try: payload = await request.json()
        except: payload = {}

        query = str(payload.get("query", "")).strip()
        targ_user = None
        if query.isdigit():
            targ_user = await User.get_or_none(user_id=int(query))
        elif query:
            clean_name = query.lstrip("@").strip()
            targ_user = await User.get_or_none(username__iexact=clean_name)

        if not targ_user:
            return web.json_response({"ok": False, "error": "user_not_found"})

        return web.json_response({
            "ok": True,
            "user": {
                "id": targ_user.user_id,
                "full_name": targ_user.full_name,
                "username": targ_user.username
            }
        })

    app.router.add_post("/webapp/api/lookup_user", lookup_user_handler)

    # ── MY GROUPS ──
    async def my_groups_handler(request):
        chats = await Chat.all().limit(20)
        items = [{
            "id": c.chat_id,
            "title": c.title,
            "invite_link": c.invite_link
        } for c in chats]
        return web.json_response({"ok": True, "groups": items})

    app.router.add_post("/webapp/api/my_groups", my_groups_handler)

    # ── SUPPORT CHAT ──
    async def support_history_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        if not user_id:
            return web.json_response({"ok": False, "error": "user_id_required"})

        msgs = await SupportMessage.filter(customer_user_id=user_id).order_by("created_at").limit(50)
        history = [{
            "id": m.id,
            "is_from_admin": m.is_from_admin,
            "text": m.customer_text or m.original_text,
            "image_url": m.image_url,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in msgs]

        return web.json_response({"ok": True, "history": history})

    app.router.add_post("/webapp/api/support_history", support_history_handler)

    async def support_send_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        text = payload.get("text", "").strip()
        image_url = payload.get("image_url")

        if not user_id or (not text and not image_url):
            return web.json_response({"ok": False, "error": "invalid_data"})

        msg = await SupportMessage.create(
            customer_user_id=user_id,
            is_from_admin=False,
            original_text=text,
            uz_text=text,
            customer_text=text,
            image_url=image_url
        )

        return web.json_response({
            "ok": True,
            "message": {
                "id": msg.id,
                "is_from_admin": False,
                "text": text,
                "image_url": image_url,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
        })

    app.router.add_post("/webapp/api/support_send", support_send_handler)

    async def support_unread_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        count = await SupportMessage.filter(customer_user_id=user_id, is_from_admin=True, is_read=False).count()
        return web.json_response({"ok": True, "unread": count})

    app.router.add_post("/webapp/api/support_unread", support_unread_handler)

    # ── ADMIN STATS & CONTROL ──
    async def admin_stats_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        if user_id not in ADMINS:
            return web.json_response({"ok": False, "error": "admin_only"}, status=403)

        total_users = await User.all().count()
        total_dollars = (await Profile.annotate(t=Sum("dollar")).values_list("t", flat=True))[0] or 0
        total_diamonds = (await Profile.annotate(t=Sum("diamond")).values_list("t", flat=True))[0] or 0
        total_games = await Game.all().count()
        active_games = await Game.filter(is_active=True).count()
        total_vips = await VipUser.all().count()

        return web.json_response({
            "ok": True,
            "stats": {
                "users": total_users,
                "dollars": total_dollars,
                "diamonds": total_diamonds,
                "total_games": total_games,
                "active_games": active_games,
                "vips": total_vips,
            }
        })

    app.router.add_post("/webapp/api/admin_stats", admin_stats_handler)

    async def admin_search_user_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        if user_id not in ADMINS:
            return web.json_response({"ok": False, "error": "admin_only"}, status=403)

        query = str(payload.get("query", "")).strip()
        targ = None
        if query.isdigit():
            targ = await User.get_or_none(user_id=int(query))
        elif query:
            clean = query.lstrip("@").strip()
            targ = await User.get_or_none(username__iexact=clean)

        if not targ:
            return web.json_response({"ok": False, "error": "user_not_found"})

        prof, _ = await Profile.get_or_create(user=targ, defaults={"dollar": 0, "diamond": 0})
        vip = await VipUser.get_or_none(user=targ)

        return web.json_response({
            "ok": True,
            "user": {
                "id": targ.user_id,
                "full_name": targ.full_name,
                "username": targ.username,
                "dollar": prof.dollar,
                "diamond": prof.diamond,
                "is_vip": bool(vip),
                "vip_days": vip.duration_days if vip else 0
            }
        })

    app.router.add_post("/webapp/api/admin_search_user", admin_search_user_handler)

    async def admin_adjust_balance_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        if user_id not in ADMINS:
            return web.json_response({"ok": False, "error": "admin_only"}, status=403)

        t_uid = int(payload.get("target_user_id", 0))
        dollar_delta = int(payload.get("dollar_delta", 0))
        diamond_delta = int(payload.get("diamond_delta", 0))

        targ = await User.get_or_none(user_id=t_uid)
        if not targ:
            return web.json_response({"ok": False, "error": "target_not_found"})

        prof, _ = await Profile.get_or_create(user=targ, defaults={"dollar": 0, "diamond": 0})
        prof.dollar = max(0, prof.dollar + dollar_delta)
        prof.diamond = max(0, prof.diamond + diamond_delta)
        await prof.save()

        return web.json_response({"ok": True, "dollar": prof.dollar, "diamond": prof.diamond})

    app.router.add_post("/webapp/api/admin_adjust_balance", admin_adjust_balance_handler)

    async def admin_grant_vip_handler(request):
        try: payload = await request.json()
        except: payload = {}

        user_id = extract_user_id_from_payload(payload)
        if user_id not in ADMINS:
            return web.json_response({"ok": False, "error": "admin_only"}, status=403)

        t_uid = int(payload.get("target_user_id", 0))
        days = int(payload.get("days", 30))

        targ = await User.get_or_none(user_id=t_uid)
        if not targ:
            return web.json_response({"ok": False, "error": "target_not_found"})

        vip = await VipUser.get_or_none(user=targ)
        if vip:
            vip.duration_days += days
            await vip.save()
        else:
            vip = await VipUser.create(user=targ, duration_days=days)

        return web.json_response({"ok": True, "duration_days": vip.duration_days})

    app.router.add_post("/webapp/api/admin_grant_vip", admin_grant_vip_handler)

    # ── NFT / MARKET PLACEHOLDERS ──
    async def nft_market_list_handler(request):
        items = await NftGiftCatalog.filter(is_active=True).all()
        result = [{
            "id": i.gift_id,
            "title": i.title,
            "stars_price": i.stars_price,
            "diamond_price": i.diamond_price,
            "sticker_path": i.sticker_path
        } for i in items]
        return web.json_response({"ok": True, "items": result})

    app.router.add_post("/webapp/api/nft_market_list", nft_market_list_handler)

