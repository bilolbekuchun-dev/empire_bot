import asyncio
import sys
from tortoise import Tortoise
from models.user import User, Profile, Transfers, DiamondBuyStars, AdminGiveLog

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    from utils.database import init
    await init()
    
    target_id = 8115343477
    user = await User.get_or_none(user_id=target_id)
    print(f"=== USER DATA: {target_id} ===")
    if not user:
        print("User NOT found in database!")
        await Tortoise.close_connections()
        return

    print(f"ID: {user.id}, User ID: {user.user_id}, Name: {user.full_name}, Created at: {user.created_at}")
    
    profile = await Profile.get_or_none(user=user)
    if profile:
        print(f"Profile: ID={profile.id}, Diamond={profile.diamond}, Dollar={profile.dollar}, Wins={profile.wins}, Games={profile.games_count}")
    else:
        print("Profile: NONE")

    # Transfers from this user
    from_transfers = await Transfers.filter(from_user=user).prefetch_related("to_user").order_by("-id").all()
    print(f"\n--- Transfers Sent (count={len(from_transfers)}) ---")
    for t in from_transfers:
        to_name = t.to_user.full_name if t.to_user else str(t.to_user_id)
        to_uid = getattr(t.to_user, 'user_id', '?') if t.to_user else '?'
        print(f"[{t.created_at}] Sent {t.amount} {t.type} to {to_name} (TG: {to_uid}) | Caption: {t.caption}")

    # Transfers to this user
    to_transfers = await Transfers.filter(to_user=user).prefetch_related("from_user").order_by("-id").all()
    print(f"\n--- Transfers Received (count={len(to_transfers)}) ---")
    for t in to_transfers:
        from_name = t.from_user.full_name if t.from_user else str(t.from_user_id)
        from_uid = getattr(t.from_user, 'user_id', '?') if t.from_user else '?'
        print(f"[{t.created_at}] Received {t.amount} {t.type} from {from_name} (TG: {from_uid}) | Caption: {t.caption}")

    # Admin gives
    admin_gives = await AdminGiveLog.filter(target_user_id=target_id).order_by("-id").all()
    print(f"\n--- Admin Gives to User (count={len(admin_gives)}) ---")
    for ag in admin_gives:
        print(f"[{ag.created_at}] Admin {ag.admin_user_id} gave {ag.amount} {ag.field} ({ag.extra}) via {ag.source}")

    # DiamondBuyStars
    stars_buys = await DiamondBuyStars.filter(user_id=target_id).order_by("-id").all()
    print(f"\n--- Stars Purchases (count={len(stars_buys)}) ---")
    for sb in stars_buys:
        print(f"[{sb.created_at}] Bought {sb.amount} {sb.kind} for {sb.stars} stars via {sb.source} | charge_id={sb.charge_id}")

    # Raw SQL checks across other tables
    conn = Tortoise.get_connection("default")
    
    # Check Giveaways
    try:
        gw = await conn.execute_query_dict(f"SELECT * FROM giveaway WHERE winner_id = {user.id} OR winner_id = {target_id} ORDER BY id DESC LIMIT 20;")
        print(f"\n--- Giveaways won (count={len(gw)}) ---")
        for r in gw:
            print(r)
    except Exception as e:
        print(f"Giveaway check error: {e}")

    # Check GeroyMarket
    try:
        gm = await conn.execute_query_dict(f"SELECT * FROM geroy_market WHERE user_id = {user.id} OR user_id = {target_id} ORDER BY id DESC LIMIT 20;")
        print(f"\n--- GeroyMarket (count={len(gm)}) ---")
        for r in gm:
            print(r)
    except Exception as e:
        print(f"GeroyMarket check error: {e}")

    # Check OpenSandiqs
    try:
        os_rows = await conn.execute_query_dict(f"SELECT * FROM open_sandiqs WHERE user_id = {user.id} ORDER BY id DESC LIMIT 20;")
        print(f"\n--- OpenSandiqs (count={len(os_rows)}) ---")
        for r in os_rows:
            print(r)
    except Exception as e:
        print(f"OpenSandiqs check error: {e}")

    # Check All transfers in the system where 8115343477 was involved (by user_id or id)
    try:
        all_tr = await conn.execute_query_dict(f"SELECT * FROM transfers WHERE from_user_id = {user.id} OR to_user_id = {user.id} ORDER BY id DESC LIMIT 30;")
        print(f"\n--- Raw transfers rows (count={len(all_tr)}) ---")
        for r in all_tr:
            print(r)
    except Exception as e:
        print(f"Raw transfers error: {e}")

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
