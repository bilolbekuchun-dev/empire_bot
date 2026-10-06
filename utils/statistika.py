from tortoise.expressions import Q
from datetime import datetime, timedelta
from models.game_set import GroupBalance, CommandPermissionsChat
from models.game_data import Game, GamePlayer, Chat, GiveTopChat, PlayersGameBall
from models.user import Profile, VipUser, User
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus
from aiogram import Bot
from config import ADMINS
from tortoise.functions import Count, Sum
from tortoise.transactions import in_transaction

async def bozor_statistikasi(message: Message):
    if message.from_user.id not in ADMINS:
        return

    total_dollars_sum = await Profile.annotate(total=Sum("dollar")).values_list("total", flat=True)
    total_diamonds_sum = await Profile.annotate(total=Sum("diamond")).values_list("total", flat=True)

    # annotate() qaytaradigan natija ham list bo‘ladi (odatda 1 ta element),
    # shuning uchun birinchi elementni olish kerak
    total_dollars_sum = total_dollars_sum[0] or 0
    total_diamonds_sum = total_diamonds_sum[0] or 0

    total_chats = await Chat.all().count()
    total_games_count = await Game.all().count()
    total_active_games_count = await Game.filter(is_active=True).count()
    total_users_count = await User.all().count()

    await message.answer(
        f"<b>Umumiy statistikalar:</b>\n\n"
        f"<b>💵 Jami dollar: {total_dollars_sum:,}$</b>\n"
        f"<b>💎 Jami olmos: {total_diamonds_sum:,} ta</b>\n"
        f"<b>🎮 Jami o'yinlar: {total_games_count:,} ta</b>\n"
        f"<b>🎮 Faol o'yinlar: {total_active_games_count:,} ta</b>\n"
        f"<b>👤 Jami foydalanuvchilar: {total_users_count:,} ta</b>\n"
        f"<b>💬 Jami guruhlar: {total_chats:,} ta</b>",
        parse_mode="HTML"
    )

BATCH_SIZE_GAMES = 500

def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def _render_bar(p: float, width: int = 20) -> str:
    fill = int(p * width)
    return "█" * fill + "░" * (width - fill)

def _award_for_rank(rank: int) -> int:
    if rank == 1:
        return 7
    elif 2 <= rank <= 5:
        return 5
    else:
        return 1

async def gtop_global(message, bot):
    """
    Kanalga umumiy (barcha guruhlar) statistika va diamond taqsimlash.
    /top1, /top7, /top30, /top
    """
    cmd = (message.text or "").strip().lower()
    days, title = None, None
    if cmd == "/gtop1":
        days, title = 1,  "🕐 Bugungi eng yaxshi o‘yinchilar"
    elif cmd == "/gtop7":
        days, title = 7,  "📅 Haftalik eng yaxshi o‘yinchilar"
    elif cmd == "/gtop30":
        days, title = 30, "📆 30 kunlik eng yaxshi o‘yinchilar"
    elif cmd == "/gtop":
        days, title = None, "🏆 Eng yaxshi o‘yinchilar"
    else:
        return

    time_filter = datetime.now() - timedelta(days=days) if days else None

    games_q = Game.all().only("id")
    if time_filter:
        games_q = games_q.filter(created_at__gte=time_filter)
    games = await games_q
    if not games:
        await message.answer("🎮 Bu davrda o‘yin topilmadi.")
        return

    game_ids_all = [g.id for g in games]
    total_games = len(game_ids_all)

    # progress xabari
    progress_msg = await message.answer("⏳ Statistika yig‘ilmoqda...\n" + "[░" * 10 + "] 0%")
    last_pct_shown = -1

    def maybe_update_progress(done_games):
        nonlocal last_pct_shown
        p = done_games / max(total_games, 1)
        pct = int(p * 100)
        if pct - last_pct_shown >= 3 or pct == 100:
            last_pct_shown = pct
            bar = _render_bar(p, 20)
            return bar, pct
        return None, None

    # uid -> {name, score, played}
    agg_stat = {}
    processed_games = 0

    for batch_game_ids in _chunks(game_ids_all, BATCH_SIZE_GAMES):
        totals = await (
            GamePlayer
            .filter(game_id__in=batch_game_ids)
            .group_by("game_id")
            .annotate(total=Count("id"))
            .values("game_id", "total")
        )
        total_map = {r["game_id"]: r["total"] for r in totals}

        winners = await (
            GamePlayer
            .filter(game_id__in=batch_game_ids, win=True)
            .group_by("game_id")
            .annotate(winners=Count("id"))
            .values("game_id", "winners")
        )
        winners_map = {r["game_id"]: r["winners"] for r in winners}

        players = await (
            GamePlayer
            .filter(game_id__in=batch_game_ids)
            .prefetch_related("user")
            .only("id", "game_id", "win", "user_id")
            .all()
        )

        for p in players:
            if not p.user_id or not p.user:
                continue

            total = total_map.get(p.game_id, 0)
            win_cnt = winners_map.get(p.game_id, 0)
            delta = (2 * total - win_cnt) if p.win else (-win_cnt)

            entry = agg_stat.get(p.user_id)
            if not entry:
                entry = {
                    "name": p.user.full_name,
                    "score": 0,
                    "played": 0,
                }
                agg_stat[p.user_id] = entry
            entry["played"] += 1
            entry["score"] += delta

        processed_games += len(batch_game_ids)
        bar, pct = maybe_update_progress(processed_games)
        if bar is not None:
            try:
                await progress_msg.edit_text(
                    f"⏳ Statistika yig‘ilmoqda...\n[{bar}] {pct}%"
                )
            except Exception:
                pass

    user_ids = list(agg_stat.keys())

    vip_ids = set()
    if user_ids:
        vip_ids = set(await VipUser.filter(user_id__in=user_ids).values_list("user_id", flat=True))

    profiles_map = {}
    if user_ids:
        profile_rows = await Profile.filter(user_id__in=user_ids).all()
        profiles_map = {pr.user_id: pr for pr in profile_rows}

    final_list = [dict(uid=uid, **data) for uid, data in agg_stat.items() if data["played"] >= 1]
    if not final_list:
        await progress_msg.edit_text("❗ Kamida 1 ta o‘yinda qatnashganlar kerak.")
        return

    final_list.sort(key=lambda x: x["score"], reverse=True)

    shown = final_list[:30]  # TOP 30 ko‘rsatiladi
    updated_profiles = []

    async with in_transaction():
        for idx, item in enumerate(shown, start=1):
            award = _award_for_rank(idx)
            uid = item["uid"]

            pr = profiles_map.get(uid)
            if pr is None:
                pr, _ = await Profile.get_or_create(user_id=uid, defaults={"diamond": 0})
                profiles_map[uid] = pr

            current = getattr(pr, "diamond", 0) or 0
            setattr(pr, "diamond", current + award)
            updated_profiles.append(pr)

        if updated_profiles:
            await Profile.bulk_update(updated_profiles, fields=["diamond"])

    # YAKUNIY MATN
    lines = [f"<b>{title}</b>\n"]
    for idx, item in enumerate(shown, start=1):
        is_vip = (item["uid"] in vip_ids)
        prefix = f"⭐ {idx}." if is_vip else f"{idx}."
        award = _award_for_rank(idx)
        name_safe = (item["name"] or "").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"{prefix} {name_safe} – {item['score']} ball • 💎 +{award}")

    try:
        await progress_msg.edit_text("\n".join(lines), parse_mode="HTML")
    except Exception:
        await message.answer("\n".join(lines), parse_mode="HTML")


# _chunks and _render_bar already defined above

async def get_stat_global(message: Message, bot: Bot):
    """
    Kanalga umumiy (barcha guruhlar) statistika.
    /top1, /top7, /top30, /top
    """

    cmd = (message.text or "").strip().lower()
    days, title = None, None
    if cmd == "/top1":
        days, title = 1,  "🕐 Bugungi eng yaxshi o‘yinchilar"
    elif cmd == "/top7":
        days, title = 7,  "📅 Haftalik eng yaxshi o‘yinchilar"
    elif cmd == "/top30":
        days, title = 30, "📆 30 kunlik eng yaxshi o‘yinchilar"
    elif cmd == "/top":
        days, title = None, "🏆 Eng yaxshi o‘yinchilar"
    else:
        return

    time_filter = datetime.now() - timedelta(days=days) if days else None

    # 1) Shu davrdagi barcha o‘yinlar
    games_q = Game.all().only("id")
    if time_filter:
        games_q = games_q.filter(created_at__gte=time_filter)
    games = await games_q
    if not games:
        await message.answer("🎮 Bu davrda o‘yin topilmadi.")
        return

    game_ids_all = [g.id for g in games]
    total_games = len(game_ids_all)

    progress_msg = await message.answer("⏳ Statistika yig‘ilmoqda...\n" + "[░" * 10 + "] 0%")
    last_pct_shown = -1

    def maybe_update_progress(done_games):
        nonlocal last_pct_shown
        p = done_games / max(total_games, 1)
        pct = int(p * 100)
        if pct - last_pct_shown >= 3 or pct == 100:
            last_pct_shown = pct
            bar = _render_bar(p, 20)
            return bar, pct
        return None, None

    agg_stat = {}
    processed_games = 0

    # 2) O‘yinlarni bo‘laklab qayta ishlash
    for batch_game_ids in _chunks(game_ids_all, BATCH_SIZE_GAMES):
        # a) total
        totals = await (
            GamePlayer
            .filter(game_id__in=batch_game_ids)
            .group_by("game_id")
            .annotate(total=Count("id"))
            .values("game_id", "total")
        )
        total_map = {r["game_id"]: r["total"] for r in totals}

        # b) winners
        winners = await (
            GamePlayer
            .filter(game_id__in=batch_game_ids, win=True)
            .group_by("game_id")
            .annotate(winners=Count("id"))
            .values("game_id", "winners")
        )
        winners_map = {r["game_id"]: r["winners"] for r in winners}

        # c) players
        players = await (
            GamePlayer
            .filter(game_id__in=batch_game_ids)
            .prefetch_related("user")
            .only("id", "game_id", "win", "user_id")
            .all()
        )

        # d) extra balls
        extra_balls = await PlayersGameBall.filter(game_id__in=batch_game_ids).values("game_id", "player_id", "ball")
        extra_map = {(row["game_id"], row["player_id"]): row["ball"] for row in extra_balls}

        # e) stat hisoblash
        for p in players:
            if not p.user_id or not p.user:
                continue

            total = total_map.get(p.game_id, 0)
            win_cnt = winners_map.get(p.game_id, 0)
            delta = (2 * total - win_cnt) if p.win else (-win_cnt)

            # qo‘shimcha ball qo‘shamiz
            delta += extra_map.get((p.game_id, p.id), 0)

            entry = agg_stat.get(p.user_id)
            if not entry:
                entry = {"name": p.user.full_name, "score": 0, "played": 0}
                agg_stat[p.user_id] = entry
            entry["played"] += 1
            entry["score"] += delta

        processed_games += len(batch_game_ids)
        bar, pct = maybe_update_progress(processed_games)
        if bar is not None:
            try:
                await progress_msg.edit_text(f"⏳ Statistika yig‘ilmoqda...\n[{bar}] {pct}%")
            except Exception:
                pass

    # 3) VIP va Profile
    user_ids = list(agg_stat.keys())
    vip_ids = set()
    if user_ids:
        vip_ids = set(await VipUser.filter(user_id__in=user_ids).values_list("user_id", flat=True))

    profiles_map = {}
    if user_ids:
        profile_rows = await Profile.filter(user_id__in=user_ids).all()
        profiles_map = {pr.user_id: pr for pr in profile_rows}

    # 4) Filtrlash va saralash
    final_list = [dict(uid=uid, **data) for uid, data in agg_stat.items() if data["played"] >= 1]
    if not final_list:
        await progress_msg.edit_text("❗ Kamida 1 ta o‘yinda qatnashganlar kerak.")
        return

    final_list.sort(key=lambda x: x["score"], reverse=True)

    # 5) Yakuniy chiqish (TOP 30)
    lines = [f"<b>{title}</b>\n"]
    for idx, item in enumerate(final_list[:30], start=1):
        is_vip = (item["uid"] in vip_ids)
        prefix = f"⭐ {idx}." if is_vip else f"{idx}."
        lines.append(f"{prefix} {item['name']} – {item['score']} ball")

    try:
        await progress_msg.edit_text("\n".join(lines), parse_mode="HTML")
    except Exception:
        await message.answer("\n".join(lines), parse_mode="HTML")


async def back_to_the_begining(message: Message, bot: Bot):
    print("Funksiyaga kirildi")
    if message.chat.type != "private":
        return
    user = await User.get_or_none(id=message.from_user.id)
    if not user:
        return
    player_objs = await GamePlayer.filter(user=user)
    for player in player_objs:
        await player.delete()
    await message.answer("Sizning o'yinlardagi tarixingiz tozalandi!")


async def get_stat(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    try:
        tg_user = await bot.get_chat_member(message.chat.id, message.from_user.id)
    except Exception:
        await message.answer("Bot guruhda admin emas!")
        return

    command_perms, _ = await CommandPermissionsChat.get_or_create(
        chat_id=message.chat.id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin", 
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin"
        }
    )

    chat = await Chat.get_or_none(chat_id=message.chat.id)
    if not chat:
        return

    now = datetime.now()
    command = (message.text or "").strip().lower()
    # Joriy kun/hafta/oy bo'yicha filter
    time_filter = None
    if command == "/top1":
        perm = getattr(command_perms, "top1_cmd", "admin")
        if perm == "admin":
            if tg_user.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                if message.from_user.id not in ADMINS:
                    return
        elif perm == "ega":
            if tg_user.status != ChatMemberStatus.CREATOR:
                if message.from_user.id not in ADMINS:
                    return
        elif perm == "member":
            if tg_user.status not in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                if message.from_user.id not in ADMINS:
                    return

        time_filter = now.replace(hour=0, minute=0, second=0, microsecond=0)
        title = "🕐 Bugungi eng yaxshi o'yinchilar"
        msg = await message.answer("Statistika yig‘ilmoqda, iltimos kuting...")
    elif command == "/top7":
        
        perm = getattr(command_perms, "top7_cmd", "admin")
        if perm == "admin":
                if tg_user.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                    if message.from_user.id not in ADMINS:
                        return
        elif perm == "ega":
            if tg_user.status != ChatMemberStatus.CREATOR:
                if message.from_user.id not in ADMINS:
                    return
        elif perm == "member":
            if tg_user.status not in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                if message.from_user.id not in ADMINS:
                    return
        weekday = now.weekday()
        week_start = now - timedelta(days=weekday)
        time_filter = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        title = "📅 Haftalik eng yaxshi o‘yinchilar"
        msg = await message.answer("Statistika yig‘ilmoqda, iltimos kuting...")
    elif command == "/top30":
        perm = getattr(command_perms, "top30_cmd", "admin")
        if perm == "admin":
                if tg_user.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                    if message.from_user.id not in ADMINS:
                        return
        elif perm == "ega":
            if tg_user.status != ChatMemberStatus.CREATOR:
                if message.from_user.id not in ADMINS:
                    return
        elif perm == "member":
            if tg_user.status not in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                if message.from_user.id not in ADMINS:
                    return

        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        time_filter = month_start
        title = "📆 30 kunlik eng yaxshi o‘yinchilar"
        msg = await message.answer("Statistika yig‘ilmoqda, iltimos kuting...")

    elif command == "/top":
        if command_perms:
            # /top uchun default permission - admin bo'lsin
            perm = getattr(command_perms, "top_cmd", "admin")
            if perm == "admin":
                if tg_user.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                    if message.from_user.id not in ADMINS:
                        return
            elif perm == "ega":
                if tg_user.status != ChatMemberStatus.CREATOR:
                    if message.from_user.id not in ADMINS:
                        return
            elif perm == "member":
                if tg_user.status not in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                    if message.from_user.id not in ADMINS:
                        return
        else:
            # Agar command_perms yo'q bo'lsa, default admin permission
            if tg_user.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                if message.from_user.id not in ADMINS:
                    return
        title = "🏆 Umumiy eng yaxshi o'yinchilar"
        msg = await message.answer("Statistika yig'ilmoqda, iltimos kuting...")
    else:
        return

    if time_filter:
        games = await Game.filter(chat=chat, created_at__gte=time_filter).only("id").all()
    else:
        games = await Game.filter(chat=chat).only("id").all()

    game_ids = [g.id for g in games]
    if not game_ids:
        await msg.edit_text("Bu davrda o‘yinlar topilmadi.")
        return

    # Har bir o‘yinda ishtirokchilar soni
    totals = await (
        GamePlayer
        .filter(game_id__in=game_ids)
        .group_by("game_id")
        .annotate(total=Count("id"))
        .values("game_id", "total")
    )
    total_map = {row["game_id"]: row["total"] for row in totals}

    # Har bir o‘yinda g‘oliblar soni
    winners = await (
        GamePlayer
        .filter(game_id__in=game_ids, win=True)
        .group_by("game_id")
        .annotate(winners=Count("id"))
        .values("game_id", "winners")
    )
    winners_map = {row["game_id"]: row["winners"] for row in winners}

    # O‘yinchilarni olish
    players = await (
        GamePlayer
        .filter(game_id__in=game_ids)
        .prefetch_related("user")
        .only("id", "game_id", "win", "user_id")
        .all()
    )

    # VIP foydalanuvchilar
    user_ids = {p.user_id for p in players if p.user_id}
    vip_ids = set()
    if user_ids:
        vip_rows = await VipUser.filter(user_id__in=user_ids).values_list("user_id", flat=True)
        vip_ids = set(vip_rows)

    # Qo‘shimcha ballarni oldindan olish (bir martalik so‘rov)
    extra_balls = await PlayersGameBall.filter(game_id__in=game_ids).values("game_id", "player_id", "ball")
    extra_map = {(row["game_id"], row["player_id"]): row["ball"] for row in extra_balls}

    # Statistika yig‘ish
    stat = {}
    for p in players:
        if not p.user_id or not p.user:
            continue
        uid = p.user_id

        total = total_map.get(p.game_id, 0)
        win_cnt = winners_map.get(p.game_id, 0)

        # Asosiy ball formulasi
        score_delta = (2 * total - win_cnt) if p.win else (-win_cnt)

        # Qo‘shimcha ball qo‘shish
        score_delta += extra_map.get((p.game_id, p.id), 0)

        if uid not in stat:
            stat[uid] = {
                "name": p.user.full_name,
                "played": 0,
                "score": 0,
                "is_vip": uid in vip_ids,
            }

        stat[uid]["played"] += 1
        stat[uid]["score"] += score_delta

    filtered = [s for s in stat.values() if s["played"] >= 1]
    if not filtered:
        await msg.edit_text("Reytingga chiqish uchun kamida 1 ta o‘yinda qatnashgan bo‘lish kerak.")
        return

    sorted_stat = sorted(filtered, key=lambda x: x["score"], reverse=True)

    top_lines = [f"<b>{title}</b>\n"]
    for idx, item in enumerate(sorted_stat[:20], start=1):
        prefix = f"{idx}."
        if item["is_vip"]:
            prefix = f"⭐ {idx}."
        top_lines.append(f"{prefix} {item['name']} – {item['score']} ball")

    await msg.edit_text("\n".join(top_lines), parse_mode="HTML")
BOT_ADMIN_IDS = ADMINS

async def give_stat(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    # Guruh balansini tekshirish
    group_balance = await GroupBalance.get_or_none(chat_id=message.chat.id)
    if group_balance and group_balance.balance < 7:
        await message.answer("🎮 Bu funksiya uchun guruh hisobida mablag' yetarli emas.")
        return

    # Kim chaqirganini tekshirish
    tg_user = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = tg_user.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    is_bot_admin = message.from_user.id in BOT_ADMIN_IDS
    if not is_bot_admin:
        return
    
    command = (message.text or "").strip().lower()
    give_type, days, title = None, None, None

    if command == "/gtop1":
        give_type, days, title = "1", 1, "🕐 Bugungi eng yaxshi o‘yinchi"
        if not is_admin: return
    elif command == "/gtop7":
        give_type, days, title = "7", 7, "📅 Haftalik eng yaxshi o‘yinchilar"
        if not is_admin: return
    elif command == "/gtop30":
        give_type, days, title = "30", 30, "📆 30 kunlik eng yaxshi o‘yinchilar"
        if not is_admin: return
    elif command == "/gtop":
        give_type, days, title = "all", None, "🏆 Eng yaxshi o‘yinchi"
        if not is_bot_admin: return
    else:
        return

    chat = await Chat.get_or_none(chat_id=message.chat.id)
    if not chat:
        return

    # Shu davrda mukofot berilgan-berilmaganini tekshirish
    if give_type != "all":
        existed = await GiveTopChat.filter(
            chat=chat,
            give_type=give_type,
            gived_at__gte=datetime.now() - timedelta(days=days)
        ).exists()
        if existed:
            await message.answer("⛔ Bu mukofot allaqachon berilgan.")
            return

    # Davr bo‘yicha o‘yinlar
    time_filter = datetime.now() - timedelta(days=days) if days else None
    games_q = Game.filter(chat=chat)
    if time_filter:
        games_q = games_q.filter(created_at__gte=time_filter)
    games = await games_q.only("id").all()
    if not games:
        await message.answer("🎮 Bu davrda o‘yin topilmadi.")
        return

    game_ids = [g.id for g in games]

    # 1) Har o‘yin uchun total ishtirokchi soni
    totals = await (
        GamePlayer
        .filter(game_id__in=game_ids)
        .group_by("game_id")
        .annotate(total=Count("id"))
        .values("game_id", "total")
    )
    total_map = {row["game_id"]: row["total"] for row in totals}

    # 2) Har o‘yin uchun g‘oliblar soni (win=True)
    winners = await (
        GamePlayer
        .filter(game_id__in=game_ids, win=True)
        .group_by("game_id")
        .annotate(winners=Count("id"))
        .values("game_id", "winners")
    )
    winners_map = {row["game_id"]: row["winners"] for row in winners}

    # 3) O‘yinchilarni olish (user bilan)
    players = await (
        GamePlayer
        .filter(game_id__in=game_ids)
        .prefetch_related("user")
        .only("id", "game_id", "win", "user_id")
        .all()
    )

    # Kerakli user id’lar
    user_ids = {p.user_id for p in players if p.user_id}

    # 4) VIP larni bitta IN bilan olish
    vip_ids = set()
    if user_ids:
        vip_ids = set(await VipUser.filter(user_id__in=user_ids).values_list("user_id", flat=True))

    # 5) Profil(lar)ni bitta IN bilan olish (mukofot berish uchun)
    profiles_map = {}
    if user_ids:
        profile_rows = await Profile.filter(user_id__in=user_ids).all()
        profiles_map = {pr.user_id: pr for pr in profile_rows}

    # 6) Statistika: yangi ball formulasi
    #    yutgan: 2*total - win_cnt
    #    yutqazgan: -win_cnt
    stat = {}  # uid -> dict
    for p in players:
        if not p.user:
            continue

        total = total_map.get(p.game_id, 0)
        win_cnt = winners_map.get(p.game_id, 0)
        delta = (2 * total - win_cnt) if p.win else (-win_cnt)

        uid = p.user_id
        if uid not in stat:
            stat[uid] = {
                "name": p.user.full_name,
                "score": 0,
                "played": 0,
                "profile": profiles_map.get(uid),  # bo‘lmasa None
                "is_vip": uid in vip_ids
            }
        stat[uid]["played"] += 1
        stat[uid]["score"] += delta

    # Kamida 1 ta o‘yinda qatnashganlar
    top_stat = [v for v in stat.values() if v["played"] >= 1]
    if not top_stat:
        await message.answer("❗ Kamida 1 ta o‘yinda qatnashganlar kerak.")
        return

    # Tartarib
    top_stat.sort(key=lambda x: x["score"], reverse=True)

    # ——— Mukofotlash va chiqish matni ———
    top_text = f"<b>{title}</b>\n\n"

    if give_type == "1":
        top = top_stat[0]
        if top["profile"]:
            top["profile"].dollar += 100
            await top["profile"].save()
        await GiveTopChat.create(chat=chat, give_type="1")
        top_text += f"🥇 {top['name']} – {top['score']} ball | 💵 100"

    elif give_type == "7":
        await GiveTopChat.create(chat=chat, give_type="7")
        for idx, user in enumerate(top_stat[:7], start=1):
            reward = max(0, 900 - idx * 100)  # (800,700,...,200,100) istasangiz qaytarib qo‘ying
            if user["profile"]:
                user["profile"].dollar += reward
                await user["profile"].save()
            prefix = f"⭐ {idx}." if user["is_vip"] else f"{idx}."
            top_text += f"{prefix} {user['name']} – {user['score']} ball | 💵 {reward}\n"

    elif give_type == "30":
        await GiveTopChat.create(chat=chat, give_type="30")
        for idx, user in enumerate(top_stat[:30], start=1):
            reward = max(0, 3200 - idx * 100)  # (3100,3000,...)
            if user["profile"]:
                user["profile"].dollar += reward
                await user["profile"].save()
            prefix = f"⭐ {idx}." if user["is_vip"] else f"{idx}."
            top_text += f"{prefix} {user['name']} – 💵 {reward}\n"

    elif give_type == "all":
        top = top_stat[0]
        if top["profile"]:
            top["profile"].dollar *= 2
            await top["profile"].save()
        top_text += f"🥇 {top['name']} – 💰 Hisobi 2 baravar bo‘ldi"

    await message.answer(top_text, parse_mode="HTML")

async def show_richest_users(message: Message):
    if message.from_user.id not in ADMINS:
        return

    dollar_tops = await Profile.all().prefetch_related("user").order_by("-dollar").limit(10)
    diamond_tops = await Profile.all().prefetch_related("user").order_by("-diamond").limit(10)

    # Batch VIP check instead of N+1 queries
    all_user_ids = {p.user_id for p in dollar_tops} | {p.user_id for p in diamond_tops}
    vip_ids = set(await VipUser.filter(user_id__in=all_user_ids).values_list("user_id", flat=True)) if all_user_ids else set()

    text = "<b>💵 Eng boylar (Dollar bo‘yicha)</b>\n"
    for idx, prof in enumerate(dollar_tops, 1):
        is_vip = prof.user_id in vip_ids
        text += f"{'⭐' if is_vip else idx}. {prof.user.full_name} — {prof.dollar}💵\n"

    text += "\n<b>💎 Eng boylar (Olmos bo‘yicha)</b>\n"
    for idx, prof in enumerate(diamond_tops, 1):
        is_vip = prof.user_id in vip_ids
        text += f"{'⭐' if is_vip else idx}. {prof.user.full_name} — {prof.diamond}💎\n"

    await message.answer(text, parse_mode="HTML")

async def show_richest_users_in_this_chat(message: Message):
    if message.from_user.id not in ADMINS:
        return

    chat = await Chat.get_or_none(chat_id=message.chat.id)
    if not chat:
        return

    # 1) Shu chatdagi noyob user_id larni oling (DISTINCT) — juda yengil va tez
    user_ids_in_chat = await (
        GamePlayer
        .filter(game__chat=chat)
        .distinct()
        .values_list("user_id", flat=True)
    )
    if not user_ids_in_chat:
        await message.answer("Bu chatda reyting uchun profil topilmadi.", parse_mode="HTML")
        return

    # 2) Profile larni shu userlar bo‘yicha, User bilan JOIN qilib oling
    base_q = (
        Profile
        .filter(user_id__in=user_ids_in_chat)
        .select_related("user")
        .only("user_id", "dollar", "diamond", "user__full_name")  # minimal ustunlar
    )

    dollar_tops  = await base_q.order_by("-dollar").limit(10)
    diamond_tops = await base_q.order_by("-diamond").limit(10)

    # 3) VIPlarni bitta IN so‘rovda olib, set qilamiz — N+1 yo‘q
    top_user_ids = {p.user_id for p in dollar_tops} | {p.user_id for p in diamond_tops}
    vip_ids = set(
        await VipUser
        .filter(user_id__in=top_user_ids)
        .values_list("user_id", flat=True)
    )

    def render(title, items, field, unit):
        lines = [f"<b>{title}</b>"]
        for idx, p in enumerate(items, 1):
            star = "⭐" if p.user_id in vip_ids else idx
            name = p.user.full_name or "Noma’lum"
            val = getattr(p, field)
            lines.append(f"{star}. {name} — {val}{unit}")
        return "\n".join(lines)

    text = "\n\n".join([
        render("💵 Shu chatdagi eng boylar (Dollar bo‘yicha)",  dollar_tops,  "dollar",  "💵"),
        render("💎 Shu chatdagi eng boylar (Olmos bo‘yicha)",   diamond_tops, "diamond", "💎"),
    ])

    await message.answer(text, parse_mode="HTML")


async def get_chat_stats(message: Message, bot: Bot):
    """
    Guruhlar bo'yicha statistika - o'yinlar soni bo'yicha top
    /tchat1, /tchat7, /tchat30, /tchat
    Faqat bot adminlari ishlata oladi
    """
    if message.from_user.id not in ADMINS:
        return

    command = (message.text or "").strip().lower()
    days, title = None, None
    
    if command == "/tchat1":
        days, title = 1, "🕐 Bugungi eng faol guruhlar"
    elif command == "/tchat7":
        days, title = 7, "📅 Haftalik eng faol guruhlar"
    elif command == "/tchat30":
        days, title = 30, "📆 30 kunlik eng faol guruhlar"
    elif command == "/tchat":
        days, title = None, "🏆 Eng faol guruhlar (barcha vaqt)"
    else:
        return

    # Vaqt filtri
    time_filter = datetime.now() - timedelta(days=days) if days else None
    
    # Progress xabari
    progress_msg = await message.answer("⏳ Guruhlar statistikasi yig'ilmoqda...")

    try:
        # O'yinlar so'rovi
        games_query = Game.select_related("chat")
        if time_filter:
            games_query = games_query.filter(created_at__gte=time_filter)
        
        # Guruh bo'yicha o'yinlar sonini hisoblash
        chat_stats = await (
            games_query
            .group_by("chat_id")
            .annotate(games_count=Count("id"))
            .values("chat_id", "games_count", "chat__title")
        )

        if not chat_stats:
            await progress_msg.edit_text("📊 Bu davrda o'yinlar topilmadi.")
            return

        # Statistikani saralash
        sorted_stats = sorted(chat_stats, key=lambda x: x["games_count"], reverse=True)

        # Natijalarni formatlash
        lines = [f"<b>{title}</b>\n"]
        
        for idx, stat in enumerate(sorted_stats[:20], start=1):  # TOP 20
            chat_title = stat["chat__title"] or "Noma'lum guruh"
            games_count = stat["games_count"]
            
            # Chat title'ni HTML uchun xavfsiz qilish
            safe_title = chat_title.replace("<", "&lt;").replace(">", "&gt;")
            
            lines.append(f"{idx}. {safe_title} — {games_count} o'yin")

        # Umumiy statistika
        total_chats = len(chat_stats)
        total_games = sum(stat["games_count"] for stat in chat_stats)
        
        lines.append(f"\n📊 <b>Jami:</b> {total_chats} ta guruh, {total_games} ta o'yin")

        result_text = "\n".join(lines)
        await progress_msg.edit_text(result_text, parse_mode="HTML")

    except Exception as e:
        await progress_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")


async def get_detailed_chat_stats(message: Message, bot: Bot):
    """
    Guruhlar bo'yicha batafsil statistika
    Faqat bot adminlari ishlata oladi
    """
    if message.from_user.id not in ADMINS:
        return

    # Progress xabari
    progress_msg = await message.answer("⏳ Batafsil statistika yig'ilmoqda...")

    try:
        # Barcha guruhlar va ularning o'yinlari
        chats_with_games = await (
            Chat
            .annotate(
                total_games=Count("games"),
                active_games=Count("games", _filter=Q(games__is_active=True))
            )
            .filter(total_games__gt=0)
            .order_by("-total_games")
            .values("chat_id", "title", "total_games", "active_games")
        )

        if not chats_with_games:
            await progress_msg.edit_text("📊 O'yin o'tkazgan guruhlar topilmadi.")
            return

        # Umumiy statistika
        total_chats = len(chats_with_games)
        total_games_all = sum(chat["total_games"] for chat in chats_with_games)
        total_active = sum(chat["active_games"] for chat in chats_with_games)

        # Top 15 guruh
        lines = ["<b>📊 Guruhlar bo'yicha batafsil statistika</b>\n"]
        
        for idx, chat in enumerate(chats_with_games[:15], start=1):
            title = chat["title"] or "Noma'lum guruh"
            safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
            
            total = chat["total_games"]
            active = chat["active_games"]
            
            status = f"({active} faol)" if active > 0 else ""
            lines.append(f"{idx}. {safe_title} — {total} o'yin {status}")

        # Umumiy ma'lumot
        lines.append(f"\n📈 <b>Umumiy:</b>")
        lines.append(f"• Jami guruhlar: {total_chats} ta")
        lines.append(f"• Jami o'yinlar: {total_games_all:,} ta")
        lines.append(f"• Faol o'yinlar: {total_active} ta")

        result_text = "\n".join(lines)
        await progress_msg.edit_text(result_text, parse_mode="HTML")

    except Exception as e:
        await progress_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")

async def calculate_and_cache_global_stats(period: str = "today"):
    pass

async def export_global_richest_to_excel(message, bot):
    pass

