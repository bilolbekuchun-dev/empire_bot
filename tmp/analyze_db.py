"""
Database tahlil skripti — faqat SELECT, hech narsa o'zgarmaydi.
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
if not DB_URL:
    raise RuntimeError(".env da DATABASE_URL topilmadi!")


async def analyze():
    conn = await asyncpg.connect(DB_URL)

    print("\n" + "="*60)
    print("📊 JADVALLAR, YOZUVLAR SONI VA HAJMI")
    print("="*60)
    tables = await conn.fetch("""
        SELECT table_name,
               pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size,
               pg_total_relation_size(quote_ident(table_name)) AS size_bytes
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY size_bytes DESC;
    """)
    for t in tables:
        count = await conn.fetchval(f'SELECT COUNT(*) FROM "{t["table_name"]}"')
        print(f"  {t['table_name']:<25} {count:>10} ta   [{t['size']}]")

    print("\n" + "="*60)
    print("👤 USER jadvali ustunlari")
    print("="*60)
    cols = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'user' AND table_schema = 'public'
        ORDER BY ordinal_position;
    """)
    for c in cols:
        print(f"  {c['column_name']:<25} {c['data_type']:<20} nullable={c['is_nullable']}")

    print("\n" + "="*60)
    print("🎮 GAMEPLAYER jadvali ustunlari")
    print("="*60)
    cols = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'gameplayer' AND table_schema = 'public'
        ORDER BY ordinal_position;
    """)
    for c in cols:
        print(f"  {c['column_name']:<25} {c['data_type']:<20} nullable={c['is_nullable']}")

    print("\n" + "="*60)
    print("👤 PROFILE jadvali ustunlari")
    print("="*60)
    cols = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'profile' AND table_schema = 'public'
        ORDER BY ordinal_position;
    """)
    for c in cols:
        print(f"  {c['column_name']:<25} {c['data_type']:<20} nullable={c['is_nullable']}")

    print("\n" + "="*60)
    print("📅 GAMEPLAYER — deaded_at & joined_at statistikasi")
    print("="*60)
    stats = await conn.fetchrow("""
        SELECT
            COUNT(*)                        AS total,
            COUNT(deaded_at)                AS with_deaded_at,
            COUNT(*) - COUNT(deaded_at)     AS null_deaded_at,
            MIN(deaded_at)                  AS oldest_deaded,
            MAX(deaded_at)                  AS newest_deaded,
            COUNT(joined_at)                AS with_joined_at,
            MIN(joined_at)                  AS oldest_joined,
            MAX(joined_at)                  AS newest_joined
        FROM gameplayer;
    """)
    print(f"  Jami yozuvlar             : {stats['total']}")
    print(f"  deaded_at bor             : {stats['with_deaded_at']}")
    print(f"  deaded_at NULL            : {stats['null_deaded_at']}")
    print(f"  deaded_at [min - max]     : {stats['oldest_deaded']}  ->  {stats['newest_deaded']}")
    print(f"  joined_at bor             : {stats['with_joined_at']}")
    print(f"  joined_at [min - max]     : {stats['oldest_joined']}  ->  {stats['newest_joined']}")

    print("\n" + "="*60)
    print("🔍 90 KUNLIK FAOLSIZLIK TAHLILI")
    print("="*60)
    cutoff = datetime.now() - timedelta(days=90)
    print(f"  Chegara sanasi (UTC)       : {cutoff.strftime('%Y-%m-%d %H:%M:%S')}")

    inactive_count = await conn.fetchval("""
        SELECT COUNT(*) FROM (
            SELECT u.id
            FROM "user" u
            LEFT JOIN gameplayer gp ON gp.user_id = u.id
            GROUP BY u.id
            HAVING MAX(gp.deaded_at) IS NULL OR MAX(gp.deaded_at) < $1
        ) sub
    """, cutoff)
    print(f"  90 kun faolsiz userlar    : {inactive_count}")

    active_count = await conn.fetchval("""
        SELECT COUNT(DISTINCT u.id)
        FROM "user" u
        JOIN gameplayer gp ON gp.user_id = u.id
        WHERE gp.deaded_at >= $1
    """, cutoff)
    print(f"  90 kun ichida aktiv       : {active_count}")

    total_users = await conn.fetchval('SELECT COUNT(*) FROM "user"')
    print(f"  Jami userlar              : {total_users}")

    print("\n" + "="*60)
    print("🔗 FOREIGN KEY bog'liqliklar (user jadvali uchun)")
    print("="*60)
    fks = await conn.fetch("""
        SELECT
            tc.table_name       AS child_table,
            kcu.column_name     AS child_column,
            ccu.column_name     AS parent_column,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.referential_constraints rc
            ON tc.constraint_name = rc.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON rc.unique_constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = 'user';
    """)
    if fks:
        for fk in fks:
            print(f"  {fk['child_table']}.{fk['child_column']} -> user.{fk['parent_column']}  [ON DELETE {fk['delete_rule']}]")
    else:
        print("  Hech qanday FK topilmadi")

    print("\n" + "="*60)
    print("✅ Tahlil tugadi")
    print("="*60 + "\n")

    await conn.close()


asyncio.run(analyze())
