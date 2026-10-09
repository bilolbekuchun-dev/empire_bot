import random
from typing import Tuple
from models.user import User, Profile, ActiveRole
from models.airdrop import RoleSpinLog
from utils.role_names import RoleNames

# Rollar va ularning nodirlik (weighted chance) og'irliklari
# Og'irlik qancha kichik bo'lsa, tushish ehtimoli shuncha kam bo'ladi.
ROLE_WEIGHTS = {
    # Afsonaviy / Qimmat rollar (past ehtimollik)
    "Don": 2,
    "Komissar": 2,
    "Advokat": 3,
    "Qotil": 3,
    "Joker": 3,
    "Sehrgar": 3,
    "Robin Gud": 3,
    "Aferist": 4,

    # O'rtacha rollar
    "Doktor": 6,
    "Ovchi": 6,
    "Bori": 6,
    "Aygoqchi": 6,
    "Qasoskor": 6,
    "G'azabkor": 6,
    "Aktyor": 7,
    "Jin": 7,
    "Daydi": 8,
    "Kezuvchi": 8,
    "Janob": 8,

    # Oddiy rollar (yuqori ehtimollik)
    "Serjant": 12,
    "Sotqin": 12,
    "Hamshira": 12,
    "Konchi": 12,
    "Omadli": 12,
    "Fuqaro": 15
}

def spin_role() -> str:
    """Weighted random selection orqali rol tanlaydi (faqat faol rollar)"""
    from config import is_role_enabled
    valid_items = [(r, w) for r, w in ROLE_WEIGHTS.items() if is_role_enabled(r)]
    if not valid_items:
        valid_items = [("Fuqaro", 15)]
    roles = [item[0] for item in valid_items]
    weights = [item[1] for item in valid_items]
    selected_role = random.choices(roles, weights=weights, k=1)[0]
    return selected_role

async def process_role_spin(user_id: int) -> Tuple[bool, str]:
    """
    Foydalanuvchi balansasidan 2 almaz yechib, rol spinini amalga oshiradi.
    Returns: (success: bool, message: str)
    """
    user = await User.get_or_none(user_id=user_id)
    if not user:
        return False, "Foydalanuvchi topilmadi."

    profile = await Profile.get_or_none(user=user)
    if not profile or profile.diamond < 2:
        return False, "❌ Spiningiz uchun kamida <b>2 almaz</b> kerak!"

    # 2 almaz yechiladi
    profile.diamond -= 2
    await profile.save()

    # Rol spin qilinadi
    won_role_name = spin_role()
    formatted_role_title = RoleNames.get_by_role(won_role_name)

    # ActiveRole bazasiga qo'shiladi
    await ActiveRole.create(profile=profile, role=won_role_name, is_active=True)
    await RoleSpinLog.create(user=user, won_role=won_role_name, cost_diamonds=2)

    return True, f"🎰 <b>TABRIKLAYMIZ!</b>\n\nSiz <b>{formatted_role_title}</b> faol rolini yutib oldingiz! 🎉\nRol profilingizga saqlandi va keyingi o'yiningizda faollashadi."
