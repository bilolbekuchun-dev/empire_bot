import os
import json
import shutil
import zipfile
import asyncio
from datetime import datetime
from pathlib import Path
from tortoise import Tortoise
from utils.database import redis_client
from config import DATABASE_URL

EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)


async def export_all_data() -> str:
    """
    Barcha ma'lumotlarni eksport qiladi va ZIP faylga yig'di.
    Returns: ZIP faylning yo'li
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"empire_bot_backup_{timestamp}.zip"
    zip_path = EXPORT_DIR / zip_filename
    
    # Vaqtinchalik katalog yaratish
    temp_dir = EXPORT_DIR / f"temp_{timestamp}"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # 1. PostgreSQL database dump
        await export_postgres_dump(temp_dir)
        
        # 2. Redis data export
        await export_redis_data(temp_dir)
        
        # 3. JSON config files
        export_config_files(temp_dir)
        
        # 4. Metadata
        create_metadata(temp_dir)
        
        # ZIP yaratish
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(temp_dir)
                    zipf.write(file_path, arcname)
        
        # Vaqtinchalik katalogni o'chirish
        shutil.rmtree(temp_dir)
        
        return str(zip_path)
    
    except Exception as e:
        # Xatolik bo'lsa, temp dirni tozalash
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise e


async def export_postgres_dump(temp_dir: Path):
    """PostgreSQL databaseni SQL dump sifatida eksport qiladi"""
    try:
        from tortoise import connections
        
        conn = connections.get("default")
        
        # Barcha jadvallarni olish
        tables = [
            "user", "profile", "activerole", "vipuser", "paralar", 
            "transfers", "blocked_user", "admin_give_log",
            "chat", "game", "gameplayer", "gamephase", "action", 
            "vote", "votelike", "gazabdorpick", "geroys",
            "groupbalance", "blockgrousp", "game_sets_time",
            "commandpermissionschat", "command_permissions_chat",
            "customemojiconfig", "geroymarket", "tournament",
            "nftgiftcatalog", "nftpurchaselog", "nftresalelisting",
            "nftresalepurchaselog", "premiumgiftoption", "premiumpurchaselog",
            "diamondbuystars", "supportmessage", "supportconversationstate",
            "stats_bridge"
        ]
        
        dump_file = temp_dir / "database_dump.json"
        dump_data = {}
        
        for table in tables:
            try:
                # Har bir jadval ma'lumotlarini olish
                query = f"SELECT * FROM {table}"
                result = await conn.execute_query_dict(query)
                dump_data[table] = result
            except Exception as e:
                print(f"⚠️ Jadval {table} eksport qilinmadi: {e}")
                dump_data[table] = []
        
        with open(dump_file, 'w', encoding='utf-8') as f:
            json.dump(dump_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ Database dump saqlandi: {dump_file}")
        
    except Exception as e:
        print(f"❌ Database export xatolik: {e}")
        raise


async def export_redis_data(temp_dir: Path):
    """Redis ma'lumotlarini eksport qiladi"""
    try:
        redis_file = temp_dir / "redis_data.json"
        redis_data = {}
        
        # Barcha kalitlarni olish
        keys = []
        try:
            cursor = 0
            while True:
                cursor, batch = await redis_client.scan(cursor, match="*", count=1000)
                keys.extend(batch)
                if cursor == 0:
                    break
        except Exception as e:
            print(f"⚠️ Redis keys scan xatolik: {e}")
        
        # Har bir kalitning ma'lumotini olish
        for key in keys:
            try:
                key_type = await redis_client.type(key)
                if key_type == 'string':
                    value = await redis_client.get(key)
                    redis_data[key] = {"type": "string", "value": value}
                elif key_type == 'hash':
                    value = await redis_client.hgetall(key)
                    redis_data[key] = {"type": "hash", "value": value}
                elif key_type == 'list':
                    value = await redis_client.lrange(key, 0, -1)
                    redis_data[key] = {"type": "list", "value": value}
                elif key_type == 'set':
                    value = await redis_client.smembers(key)
                    redis_data[key] = {"type": "set", "value": list(value)}
                elif key_type == 'zset':
                    value = await redis_client.zrange(key, 0, -1, withscores=True)
                    redis_data[key] = {"type": "zset", "value": value}
            except Exception as e:
                print(f"⚠️ Redis key {key} o'qib bo'lmadi: {e}")
        
        with open(redis_file, 'w', encoding='utf-8') as f:
            json.dump(redis_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ Redis data saqlandi: {redis_file}")
        
    except Exception as e:
        print(f"❌ Redis export xatolik: {e}")
        raise


def export_config_files(temp_dir: Path):
    """Konfiguratsiya fayllarini eksport qiladi"""
    config_files = [
        ".env",
        "custom_emojis.json",
        "config.py",
    ]
    
    config_dir = temp_dir / "configs"
    config_dir.mkdir(exist_ok=True)
    
    for file_name in config_files:
        src_path = Path(file_name)
        if src_path.exists():
            dest_path = config_dir / file_name
            shutil.copy2(src_path, dest_path)
            print(f"✅ Config file nusxalandi: {file_name}")


def create_metadata(temp_dir: Path):
    """Eksport metadata faylini yaratadi"""
    metadata = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
        "description": "Empire Mafia Bot full backup"
    }
    
    metadata_file = temp_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


async def import_all_data(zip_path: str):
    """
    ZIP fayldan barcha ma'lumotlarni import qiladi.
    """
    temp_dir = EXPORT_DIR / f"temp_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # ZIPni ochish
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # 1. Database import
        await import_postgres_dump(temp_dir)
        
        # 2. Redis import
        await import_redis_data(temp_dir)
        
        # 3. Config files import (ixtiyoriy - foydalanuvchiga bog'liq)
        # import_config_files(temp_dir)  # Xavfsizlik uchun o'chirildi
        
        # Vaqtinchalik katalogni o'chirish
        shutil.rmtree(temp_dir)
        
        return True
    
    except Exception as e:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise e


async def import_postgres_dump(temp_dir: Path):
    """PostgreSQL database dumpni import qiladi (UPDATE/INSERT - ma'lumotlar o'chmaydi)"""
    try:
        dump_file = temp_dir / "database_dump.json"
        if not dump_file.exists():
            print("⚠️ Database dump fayli topilmadi")
            return
        
        with open(dump_file, 'r', encoding='utf-8') as f:
            dump_data = json.load(f)
        
        from tortoise import connections
        conn = connections.get("default")
        
        for table, rows in dump_data.items():
            if not rows:
                continue
            
            try:
                # Har bir qator uchun UPDATE yoki INSERT (UPSERT)
                imported_count = 0
                for row in rows:
                    columns = list(row.keys())
                    values = list(row.values())
                    
                    # Primary keyni aniqlash (odatda 'id' yoki 'user_id' yoki 'chat_id')
                    primary_key = None
                    for pk in ['id', 'user_id', 'chat_id']:
                        if pk in columns:
                            primary_key = pk
                            break
                    
                    if primary_key and row.get(primary_key):
                        # UPDATE - agar ma'lumot mavjud bo'lsa
                        pk_value = row[primary_key]
                        set_clause = ', '.join([f"{col} = ?" for col in columns if col != primary_key])
                        update_values = [row[col] for col in columns if col != primary_key]
                        
                        try:
                            result = await conn.execute_query(
                                f"UPDATE {table} SET {set_clause} WHERE {primary_key} = ?",
                                update_values + [pk_value]
                            )
                            if result and result[0] > 0:
                                imported_count += 1
                            else:
                                # UPDATE qilmadi bo'lsa, INSERT qilish
                                placeholders = ', '.join(['?' for _ in values])
                                columns_str = ', '.join(columns)
                                await conn.execute_query(
                                    f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                                    values
                                )
                                imported_count += 1
                        except Exception:
                            # UPDATE xatolik bo'lsa, INSERT qilish
                            placeholders = ', '.join(['?' for _ in values])
                            columns_str = ', '.join(columns)
                            await conn.execute_query(
                                f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                                values
                            )
                            imported_count += 1
                    else:
                        # Primary key yo'q bo'lsa, oddiy INSERT
                        placeholders = ', '.join(['?' for _ in values])
                        columns_str = ', '.join(columns)
                        await conn.execute_query(
                            f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                            values
                        )
                        imported_count += 1
                
                print(f"✅ {table}: {imported_count} ta qator import qilindi (UPDATE/INSERT)")
            
            except Exception as e:
                print(f"⚠️ {table} import xatolik: {e}")
        
        print("✅ Database import tugadi (ma'lumotlar o'chirilmadi)")
        
    except Exception as e:
        print(f"❌ Database import xatolik: {e}")
        raise


async def import_redis_data(temp_dir: Path):
    """Redis ma'lumotlarini import qiladi (ma'lumotlar o'chirilmaydi, UPDATE qilinadi)"""
    try:
        redis_file = temp_dir / "redis_data.json"
        if not redis_file.exists():
            print("⚠️ Redis data fayli topilmadi")
            return
        
        with open(redis_file, 'r', encoding='utf-8') as f:
            redis_data = json.load(f)
        
        # Eski ma'lumotlarni tozalash O'CHIRILDI - endi faqat UPDATE qilamiz
        
        # Yangi ma'lumotlarni qo'shish (UPDATE/INSERT)
        imported_count = 0
        for key, data in redis_data.items():
            try:
                if data["type"] == "string":
                    await redis_client.set(key, data["value"])
                    imported_count += 1
                elif data["type"] == "hash":
                    await redis_client.delete(key)
                    await redis_client.hset(key, mapping=data["value"])
                    imported_count += 1
                elif data["type"] == "list":
                    await redis_client.delete(key)
                    for item in reversed(data["value"]):
                        await redis_client.lpush(key, item)
                    imported_count += 1
                elif data["type"] == "set":
                    await redis_client.delete(key)
                    for item in data["value"]:
                        await redis_client.sadd(key, item)
                    imported_count += 1
                elif data["type"] == "zset":
                    await redis_client.delete(key)
                    for item in data["value"]:
                        if isinstance(item, list) and len(item) == 2:
                            await redis_client.zadd(key, {item[0]: item[1]})
                    imported_count += 1
            except Exception as e:
                print(f"⚠️ Redis key {key} import xatolik: {e}")
        
        print(f"✅ Redis import tugadi ({imported_count} ta key import qilindi)")
        
    except Exception as e:
        print(f"❌ Redis import xatolik: {e}")
        raise
