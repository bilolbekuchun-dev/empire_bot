import asyncio
from tortoise import Tortoise
from models.user import User, Profile
import os
from dotenv import load_dotenv

load_dotenv()

# Rasmdagi 100 ta foydalanuvchi ma'lumotlari: (user_id, dollar, is_vip)
data = [
    (19, 64291, True), (27, 30210, False), (1404, 22206, False), (8, 19140, True),
    (160, 12615, False), (107, 11507, False), (38, 11325, False), (35, 11159, False),
    (132, 7182, False), (595, 5840, False), (64, 5185, False), (164, 5066, False),
    (1, 5000, False), (441, 4838, False), (909, 4698, False), (244, 4062, False),
    (482, 4556, False), (111, 4355, False), (161, 4047, False), (664, 4024, False),
    (622, 3878, False), (440, 3532, False), (108, 3509, False), (370, 3205, False),
    (210, 3103, False), (85, 2926, False), (55, 2909, False), (77, 2765, False),
    (1211, 2631, False), (2074, 2515, False), (4, 2470, False), (389, 2456, False),
    (2040, 2368, False), (68, 2266, False), (208, 2152, False), (2422, 2070, False),
    (256, 2053, False), (294, 1998, False), (1041, 1910, False), (576, 1839, False),
    (694, 1827, False), (1846, 1820, False), (2019, 1654, False), (110, 1563, False),
    (46, 1528, False), (2390, 1497, False), (490, 1495, False), (326, 1494, False),
    (663, 1489, False), (319, 1486, False), (5, 1484, False), (2001, 1460, False),
    (1757, 1424, False), (2169, 1423, False), (587, 1399, False), (4360, 1390, False),
    (1475, 1380, False), (413, 1370, False), (42, 1370, False), (434, 1356, False),
    (10, 1323, False), (2397, 1303, False), (299, 1300, False), (57, 1299, False),
    (5331, 1255, False), (3255, 1223, False), (588, 1222, False), (309, 1212, False),
    (4913, 1199, False), (2352, 1180, False), (1087, 1169, False), (53, 1164, False),
    (385, 1139, False), (433, 1139, False), (456, 1127, False), (126, 1114, False),
    (658, 1090, False), (2360, 1090, False), (1045, 1085, False), (2494, 1040, False),
    (1141, 1035, False), (369, 1030, False), (358, 1025, False), (2380, 1020, False),
    (831, 1010, False), (1188, 1000, False), (289, 986, False), (134, 985, False),
    (37, 982, False), (123, 945, False), (5120, 920, False), (4608, 905, False),
    (998, 902, False), (444, 899, False), (1540, 895, False), (937, 892, False),
    (620, 879, False), (11, 856, False), (1241, 838, False), (2814, 835, False)
]

async def restore():
    print("⏳ Bazaga ulanish...")
    await Tortoise.init(
        db_url=os.getenv("DATABASE_URL"),
        modules={"models": ["models.user", "models.game_data", "models.game_set"]}
    )
    
    count = 0
    for user_id, dollar, is_vip in data:
        # User yaratish
        user, _ = await User.get_or_create(
            user_id=user_id, 
            defaults={"full_name": "Tiklangan", "mention": f"ID:{user_id}"}
        )
        
        # Profil yaratish va pulni o'rnatish
        profile, _ = await Profile.get_or_create(user=user)
        profile.dollar = dollar
        if is_vip:
            profile.vip = True
        
        await profile.save()
        count += 1
        if count % 10 == 0:
            print(f"✅ {count} ta foydalanuvchi tiklandi...")

    print(f"\n🎉 JAMI {count} TA FOYDALANUVCHI MUVAFFAQIYATLI TIKLANDI!")
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(restore())


