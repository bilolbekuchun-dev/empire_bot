"""
50,000 olmos — oxirgi 90 kun o'yinlariga proporsional, max 50 ta.

Ishga tushirish:
  python tmp/diamond_gift.py          -- preview + statistika
  python tmp/diamond_gift.py --apply  -- haqiqatan yangilaydi
"""
import asyncio
import asyncpg
import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_URL = os.getenv("DATABASE_URL")
APPLY = "--apply" in sys.argv
BUDGET = 50_000
MAX_DIAMOND = 50
DAYS = 90


async def run():
    conn = await asyncpg.connect(DB_URL)
    cutoff = datetime.now() - timedelta(days=DAYS)

    # Har bir user uchun oxirgi 90 kundagi o'yin soni
    # gameplayer.deaded_at >= cutoff bo'lgan yozuvlarni sanaymiz
    total_90day_games = await conn.fetchval("""
        SELECT COUNT(*)
        FROM gameplayer
        WHERE deaded_at >= $1
    """, cutoff)

    participants = await conn.fetchval("""
        SELECT COUNT(DISTINCT u.id)
        FROM "user" u
        JOIN gameplayer gp ON gp.user_id = u.id
        WHERE gp.deaded_at >= $1
    """, cutoff)

    print("=" * 60)
    print("STATISTIKA")
    print("=" * 60)
    print(f"  90 kundagi jami gameplayer yozuvlar : {total_90day_games:>10,}")
    print(f"  Qatnashgan userlar                  : {participants:>10,}")
    print(f"  Byudjet                             : {BUDGET:>10,} olmos")
    print(f"  Maksimal (1 kishi)                  : {MAX_DIAMOND:>10} olmos")
    print()

    # Proporsional formula: user_games / total_games * BUDGET, max=MAX_DIAMOND
    # Coefficient = BUDGET / total_90day_games, lekin max chegarasi bilan
    # Eng aktiv userning 90 kundagi o'yin soni
    max_user_games = await conn.fetchval("""
        SELECT MAX(cnt) FROM (
            SELECT COUNT(*) AS cnt
            FROM "user" u
            JOIN gameplayer gp ON gp.user_id = u.id
            WHERE gp.deaded_at >= $1
            GROUP BY u.id
        ) sub
    """, cutoff)

    print(f"  Eng aktiv user (90 kun)             : {max_user_games:>10,} o'yin")
    print()

    # Formula: ROUND(user_games / total_games * BUDGET), max=50, min=0
    # Jami = BUDGET dan oshib ketmaydi (top userlardagi kesim uni kamaytiradi)
    dist = await conn.fetch("""
        SELECT
            LEAST($2, ROUND(cnt::float / $3 * $4))::int AS diamond,
            COUNT(*) AS users
        FROM (
            SELECT u.id, COUNT(*) AS cnt
            FROM "user" u
            JOIN gameplayer gp ON gp.user_id = u.id
            WHERE gp.deaded_at >= $1
            GROUP BY u.id
        ) sub
        WHERE ROUND(cnt::float / $3 * $4) >= 1
        GROUP BY LEAST($2, ROUND(cnt::float / $3 * $4))
        ORDER BY diamond
    """, cutoff, MAX_DIAMOND, total_90day_games, BUDGET)

    actual_total = sum(int(r['diamond']) * int(r['users']) for r in dist)
    max_receivers = sum(int(r['users']) for r in dist if int(r['diamond']) == MAX_DIAMOND)

    print("=" * 60)
    print("TAQSIMOT (butun sonlar)")
    print("=" * 60)
    print(f"  {'Olmos':>6}  {'Userlar':>9}")
    print("-" * 22)
    for r in dist:
        print(f"  {int(r['diamond']):>6}  {int(r['users']):>9,}")

    print()
    print("=" * 60)
    print("XULOSA")
    print("=" * 60)
    min_d = min(int(r['diamond']) for r in dist)
    max_d = max(int(r['diamond']) for r in dist)
    print(f"  Eng kam olmos       : {min_d}")
    print(f"  Eng ko'p olmos      : {max_d} (max {MAX_DIAMOND} ga yetganlar: {max_receivers:,} user)")
    print(f"  Jami beriladigan    : {actual_total:,}  (farq byudjetdan: {actual_total - BUDGET:+,})")
    print(f"  Oluvchilar soni     : {participants:,}")

    print()
    print("=" * 60)
    print("KANAL E'LONI (namuna)")
    print("=" * 60)
    print(f"""
🎉 Hayit Muborak! 🎉

Aziz o'yinchilar, Hayit munosabati bilan barcha faol o'yinchilarga
olmos sovg'a qilamiz!

💎 Jami {actual_total:,} ta olmos taqsimlandi
👥 {participants:,} nafar o'yinchi sovg'a oldi
📅 Oxirgi 90 kundagi faollik asosida
🏆 Eng ko'p: {max_d} olmos | Eng kam: {min_d} olmos

Qancha ko'p o'ynagan bo'lsangiz — shuncha ko'p oldingiz!

Hayitingiz muborak bo'lsin! 🌙
""")

    if not APPLY:
        print("[PREVIEW MODE] Hech narsa o'zgartirilmadi.")
        print("Yangilash uchun: python tmp/diamond_gift.py --apply")
        await conn.close()
        return

    print("Yangilanmoqda...")
    r1 = await conn.execute("""
        UPDATE profile p
        SET diamond = t.amount
        FROM (
            SELECT
                u.id AS uid,
                GREATEST(1, ROUND(COUNT(*)::float / $2 * $3))::bigint AS amount
            FROM "user" u
            JOIN gameplayer gp ON gp.user_id = u.id
            WHERE gp.deaded_at >= $1
            GROUP BY u.id
        ) t
        JOIN "user" u2 ON u2.id = t.uid
        WHERE p.user_id = u2.id
    """, cutoff, max_user_games, MAX_DIAMOND)
    print(f"  Yangilandi: {r1.split()[-1]} ta profil")
    print("Tugadi!")
    await conn.close()


asyncio.run(run())
