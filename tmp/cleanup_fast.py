"""
Tezkor tozalash — cascade ishlatmasdan, jadvallarni to'g'ridan tozalaydi.
Eng chuqur jadvaldan boshlab, oxirida user o'chiriladi.
"""
import asyncio
import asyncpg
import os
import sys
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_URL = os.getenv("DATABASE_URL")
DAYS = 90
BATCH = 5000


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


async def cleanup():
    conn = await asyncpg.connect(DB_URL)
    cutoff = datetime.now() - timedelta(days=DAYS)

    log(f"Chegara: {cutoff.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # --- 1. Faolsiz user ID larini temp jadvalga olamiz ---
    log("Faolsiz user ID lar temp jadvalga olinmoqda...")
    await conn.execute("DROP TABLE IF EXISTS _inactive_users")
    await conn.execute("""
        CREATE TEMP TABLE _inactive_users AS
        SELECT u.id AS uid
        FROM "user" u
        LEFT JOIN gameplayer gp ON gp.user_id = u.id
        GROUP BY u.id
        HAVING MAX(gp.deaded_at) IS NULL OR MAX(gp.deaded_at) < $1
    """, cutoff)
    await conn.execute("CREATE INDEX ON _inactive_users(uid)")

    total = await conn.fetchval("SELECT COUNT(*) FROM _inactive_users")
    log(f"Jami faolsiz user: {total} ta")

    if total == 0:
        log("O'chiriladigan narsa yo'q.")
        await conn.close()
        return

    # --- 2. Tegishli gameplayer ID larini temp jadvalga ---
    log("Gameplayer ID lar temp jadvalga olinmoqda...")
    await conn.execute("DROP TABLE IF EXISTS _inactive_gp")
    await conn.execute("""
        CREATE TEMP TABLE _inactive_gp AS
        SELECT gp.id AS gp_id
        FROM gameplayer gp
        JOIN _inactive_users iu ON iu.uid = gp.user_id
    """)
    await conn.execute("CREATE INDEX ON _inactive_gp(gp_id)")
    gp_total = await conn.fetchval("SELECT COUNT(*) FROM _inactive_gp")
    log(f"Jami gameplayer: {gp_total} ta")

    # --- 3. Chuqur jadvallarni o'chirish (gameplayer orqali) ---
    t = time.time()

    log("votelike o'chirilmoqda...")
    r = await conn.execute("""
        DELETE FROM votelike vl
        USING vote v
        JOIN _inactive_gp igp ON igp.gp_id = v.gameplayer_id
        WHERE vl.vote_id = v.id
    """)
    log(f"  votelike: {r.split()[-1]} ta ({time.time()-t:.1f}s)")

    t = time.time()
    log("vote o'chirilmoqda...")
    r = await conn.execute("""
        DELETE FROM vote v
        USING _inactive_gp igp
        WHERE v.gameplayer_id = igp.gp_id
    """)
    log(f"  vote: {r.split()[-1]} ta ({time.time()-t:.1f}s)")

    t = time.time()
    log("action o'chirilmoqda...")
    r = await conn.execute("""
        DELETE FROM action a
        USING _inactive_gp igp
        WHERE a.gameplayer_id = igp.gp_id
    """)
    log(f"  action: {r.split()[-1]} ta ({time.time()-t:.1f}s)")

    t = time.time()
    log("playersgameball o'chirilmoqda...")
    r = await conn.execute("""
        DELETE FROM playersgameball pgb
        USING _inactive_gp igp
        WHERE pgb.gameplayer_id = igp.gp_id
    """)
    log(f"  playersgameball: {r.split()[-1]} ta ({time.time()-t:.1f}s)")

    # gamephase game_id orqali bo'lishi mumkin — tekshirib o'chiramiz
    t = time.time()
    try:
        r = await conn.execute("""
            DELETE FROM gamephase gph
            USING _inactive_gp igp
            WHERE gph.gameplayer_id = igp.gp_id
        """)
        log(f"  gamephase: {r.split()[-1]} ta ({time.time()-t:.1f}s)")
    except Exception:
        pass

    # geroyaction
    try:
        r = await conn.execute("""
            DELETE FROM geroyaction ga
            USING _inactive_gp igp
            WHERE ga.gameplayer_id = igp.gp_id
        """)
        c = r.split()[-1]
        if int(c) > 0:
            log(f"  geroyaction: {c} ta")
    except Exception:
        pass

    # --- 4. gameplayer o'chirish ---
    t = time.time()
    log("gameplayer o'chirilmoqda...")
    r = await conn.execute("""
        DELETE FROM gameplayer gp
        USING _inactive_gp igp
        WHERE gp.id = igp.gp_id
    """)
    log(f"  gameplayer: {r.split()[-1]} ta ({time.time()-t:.1f}s)")

    # --- 5. profile o'chirish ---
    t = time.time()
    log("profile o'chirilmoqda...")
    r = await conn.execute("""
        DELETE FROM profile p
        USING _inactive_users iu
        WHERE p.user_id = iu.uid
    """)
    log(f"  profile: {r.split()[-1]} ta ({time.time()-t:.1f}s)")

    # --- 6. Kichik bog'liq jadvallar ---
    for table, col in [
        ("blocked_user", "user_id"),
        ("vipuser", "user_id"),
        ("geroys", "user_id"),
        ("geroymarket", "user_id"),
        ("opensandiqs", "user_id"),
        ("paralar", "user1_id"),
        ("paralar", "user2_id"),
    ]:
        try:
            r = await conn.execute(f"""
                DELETE FROM {table} t
                USING _inactive_users iu
                WHERE t.{col} = iu.uid
            """)
            c = int(r.split()[-1])
            if c > 0:
                log(f"  {table}.{col}: {c} ta")
        except Exception:
            pass

    # --- 7. User larni BATCH bilan o'chirish ---
    log(f"User lar o'chirilmoqda (batch={BATCH})...")
    deleted = 0
    batch_num = 0
    t_start = time.time()

    while True:
        batch_num += 1
        r = await conn.execute("""
            DELETE FROM "user"
            WHERE id IN (
                SELECT uid FROM _inactive_users
                LIMIT $1 OFFSET $2
            )
        """, BATCH, deleted)
        cnt = int(r.split()[-1])
        deleted += cnt
        elapsed = time.time() - t_start
        speed = deleted / elapsed if elapsed > 0 else 0
        eta = (total - deleted) / speed if speed > 0 else 0
        log(f"  Batch {batch_num}: {deleted}/{total} ({deleted*100//total}%) | {speed:.0f} ta/s | ETA: {eta:.0f}s")
        if cnt < BATCH:
            break

    log("=" * 50)
    log(f"TUGADI! O'chirildi: {deleted} ta user")
    await conn.close()


asyncio.run(cleanup())
