import random
import json
from utils.database import redis_client as r

async def get_konchi_konlari(user_id: int, game_id: int):
    """
    Konchi uchun tanlash mumkin bo'lgan konlar ro'yxatini qaytaradi.
    Agar ro'yxat mavjud bo'lmasa, yangi tasodifiy ro'yxat yaratadi.
    
    Returns:
        list: Qolgan konlar ro'yxati. Har bir element dict: {"number": 1-10, "type": "dollar"|"olmos"|"o'lim"}
    """
    key = f"game:{game_id}:konchi:{user_id}:konlar"
    
    # Konlar ro'yxati mavjudligini tekshirish
    exists = await r.exists(key)
    
    if not exists:
        # Yangi konlar ro'yxatini yaratish: 3 ta dollarli, 1 ta olmosli, 6 ta o'lim (tuzoq)
        kon_types = ["dollar"] * 3 + ["olmos"] * 1 + ["o'lim"] * 6
        
        # Tasodifan joylashtiramiz
        random.shuffle(kon_types)
        
        # Raqamlar bilan birlashtiramiz (1-10)
        konlar = [{"number": i + 1, "type": kon_type} for i, kon_type in enumerate(kon_types)]
        
        # Redis'ga saqlaymiz
        await r.set(key, json.dumps(konlar))
    
    # Qolgan konlarni qaytaramiz
    konlar_json = await r.get(key)
    konlar = json.loads(konlar_json)
    
    return [kon["number"] for kon in konlar]

async def remove_kon(user_id: int, game_id: int, kon_number: int):
    """
    Berilgan raqamdagi konni topib, qiymatini qaytaradi va ro'yxatdan o'chiradi.
    
    Args:
        user_id: Konchi foydalanuvchi ID
        game_id: O'yin ID
        kon_number: Kon raqami (1-10)
    
    Returns:
        dict: Kon ma'lumoti {"number": ..., "type": ...} yoki None (agar kon topilmasa)
    """
    key = f"game:{game_id}:konchi:{user_id}:konlar"
    
    # Konlar ro'yxatini olamiz
    konlar_json = await r.get(key)
    if not konlar_json:
        return None
    
    konlar = json.loads(konlar_json)
    
    # Berilgan raqamdagi konni topamiz
    kon_found = None
    yangi_konlar = []
    
    for kon in konlar:
        if kon["number"] == kon_number:
            kon_found = kon
        else:
            yangi_konlar.append(kon)
    
    # Agar kon topilgan bo'lsa, yangilangan ro'yxatni saqlaymiz
    if kon_found:
        await r.set(key, json.dumps(yangi_konlar))
    
    return kon_found["type"]


async def clear_konchi_konlari(user_id: int, game_id: int):
    """
    Konchi uchun barcha kon ma'lumotlarini tozalaydi (Redis'dan o'chiradi).
    
    Args:
        user_id: Konchi foydalanuvchi ID
        game_id: O'yin ID
    
    Returns:
        bool: Muvaffaqiyatli o'chirilgan bo'lsa True
    """
    key = f"game:{game_id}:konchi:{user_id}:konlar"
    result = await r.delete(key)
    return result > 0
    