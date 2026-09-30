import asyncio
from tortoise import Tortoise
from models.user import User, Profile
import os
from dotenv import load_dotenv

load_dotenv()

# Olmoslar ro'yxati (100 ta): (user_id, diamond, is_vip)
diamond_data = [
    (19, 1304, True), (432, 75, False), (55, 72, False), (8, 69, True),
    (108, 66, False), (173, 60, False), (280, 58, False), (1960, 55, False),
    (326, 53, False), (2390, 52, False), (160, 50, False), (482, 49, False),
    (1, 49, False), (594, 48, False), (1041, 48, False), (180, 46, False),
    (21, 39, False), (1039, 39, False), (38, 36, False), (70, 35, False),
    (27, 33, False), (7, 32, False), (154, 31, False), (852, 31, False),
    (385, 29, False), (256, 29, False), (26, 28, False), (694, 28, False),
    (132, 26, False), (145, 25, False), (906, 24, False), (120, 24, False),
    (4, 24, False), (46, 23, False), (598, 21, False), (149, 20, False),
    (452, 19, False), (444, 18, False), (755, 18, False), (294, 18, False),
    (576, 18, False), (74, 17, False), (244, 17, False), (2377, 16, False),
    (1562, 16, False), (1700, 16, False), (1943, 16, False), (4938, 16, False),
    (95, 15, False), (178, 15, False), (1186, 15, False), (188, 15, False),
    (2019, 15, False), (4360, 15, False), (207, 14, False), (433, 14, False),
    (728, 14, False), (53, 14, False), (350, 13, False), (542, 13, False),
    (319, 13, False), (64, 13, False), (361, 13, False), (5331, 12, False),
    (1911, 12, False), (388, 12, False), (2013, 11, False), (6, 11, False),
    (2376, 10, False), (40, 10, False), (1071, 10, False), (232, 10, False),
    (2094, 10, False), (77, 10, False), (1892, 10, False), (5, 10, False),
    (10, 9, False), (687, 9, False), (1324, 9, False), (57, 9, False),
    (309, 9, False), (764, 9, False), (2492, 9, False), (3567, 9, False),
    (526, 9, False), (2381, 8, False), (85, 8, False), (42, 8, False),
    (2762, 8, False), (441, 8, False), (2890, 8, False), (174, 8, False),
    (2229, 8, False), (179, 8, False), (211, 8, False), (158, 8, False),
    (936, 7, False), (982, 7, False), (720, 7, False), (998, 7, False)
]

async def restore_diamonds():
    print("⏳ Bazaga ulanish...")
    await Tortoise.init(
        db_url=os.getenv("DATABASE_URL"),
        modules={"models": ["models.user", "models.game_data", "models.game_set"]}
    )
    
    count = 0
    for user_id, diamond, is_vip in diamond_data:
        # User yaratish yoki olish
        user, _ = await User.get_or_create(
            user_id=user_id, 
            defaults={"full_name": "Tiklangan", "mention": f"ID:{user_id}"}
        )
        
        # Profil yaratish yoki olish
        profile, _ = await Profile.get_or_create(user=user)
        profile.diamond = diamond
        if is_vip:
            profile.vip = True
        
        await profile.save()
        count += 1
        if count % 10 == 0:
            print(f"✅ {count} ta foydalanuvchi olmoslari tiklandi...")

    print(f"\n🎉 JAMI {count} TA FOYDALANUVCHI OLMOSLARI MUVAFFAQIYATLI TIKLANDI!")
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(restore_diamonds())

