import asyncio
import json
import os
import subprocess
from tortoise import Tortoise
from config import DATABASE_URL
from models.user import User, Profile
from models.game_data import GamePlayer, Action

async def deep_investigate():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    conn = Tortoise.get_connection("default")
    
    target_user_id = 8379517793
    user = await User.get_or_none(user_id=target_user_id)
    profile = await Profile.get_or_none(user=user)
    
    print(f"USER: ID={user.id}, tg_id={user.user_id}, name={user.full_name}")
    print(f"PROFILE: diamonds={profile.diamond}, dollars={profile.dollar}")
    
    # 1. Check all games played
    games_played = await conn.execute_query_dict(
        "SELECT gp.id, gp.role, gp.win, gp.is_really_winner, g.id as game_id, g.mode, g.created_at "
        "FROM gameplayer gp JOIN game g ON gp.game_id = g.id WHERE gp.user_id = $1 ORDER BY gp.id DESC LIMIT 50;",
        [user.id]
    )
    print(f"\n[GAMES PLAYED: {len(games_played)}]")
    for g in games_played:
        print(f"  Game #{g['game_id']} | Role: {g['role']} | Win: {g['win']} | RealWinner: {g['is_really_winner']} | Date: {g['created_at']}")
        
    # 2. Check all actions by this user
    all_acts = await conn.execute_query_dict(
        "SELECT a.id, a.action_type, a.result, a.phase_id FROM action a "
        "JOIN gameplayer gp ON a.actor_id = gp.id WHERE gp.user_id = $1 ORDER BY a.id DESC LIMIT 100;",
        [user.id]
    )
    print(f"\n[ACTIONS: {len(all_acts)}]")
    for a in all_acts:
        print(f"  Action #{a['id']} | Type: {a['action_type']} | Result: {a['result']}")

    # 3. Check all actions where this user was target
    targ_acts = await conn.execute_query_dict(
        'SELECT a.id, a.action_type, a.result, gp.role as actor_role, u.user_id as actor_tg_id FROM action a '
        'JOIN gameplayer gp ON a.actor_id = gp.id JOIN "user" u ON gp.user_id = u.id '
        'WHERE a.target_id IN (SELECT id FROM gameplayer WHERE user_id = $1) ORDER BY a.id DESC LIMIT 50;',
        [user.id]
    )
    print(f"\n[TARGET IN ACTIONS: {len(targ_acts)}]")
    for a in targ_acts:
        print(f"  Action #{a['id']} | Type: {a['action_type']} | Result: {a['result']} | From actor role: {a['actor_role']} (tg: {a['actor_tg_id']})")
        
    # 4. Check all other tables
    tables = [
        'promocode', 'promo_activation', 'promocode_usage', 'sandiq', 'user_sandiq',
        'transfers', 'transactions', 'referral', 'paralar', 'para', 'marriages',
        'missions', 'user_missions', 'achievements', 'user_achievements',
        'active_roles', 'active_role', 'gift', 'gifts', 'daily_bonus'
    ]
    for t in tables:
        try:
            r = await conn.execute_query_dict(f"SELECT * FROM {t} WHERE user_id = {user.id} OR user_id = {target_user_id} LIMIT 10;")
            if r:
                print(f"\n[TABLE {t}]: {r}")
        except Exception:
            pass
            
    await Tortoise.close_connections()

asyncio.run(deep_investigate())
