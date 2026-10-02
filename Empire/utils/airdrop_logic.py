import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
from models.user import User, Profile, VipUser
from models.airdrop import UserAirdrop

# Utilita nomlari va tavsiflari
UTILITIES = {
    "himoya": "🛡 Qalqon (Himoya)",
    "doridan_himoya": "💊 Doridan himoya",
    "slip_himoya": "🧊 Sirpanishdan himoya",
    "qotildan_himoya": "🗡 Qotildan himoya",
    "osishdan_himoya": "🪢 Osilishdan himoya",
    "miltiq": "🔫 Miltiq",
    "maska": "🎭 Maska",
    "hujjat": "📜 Soxta Hujjat",
    "geroy_himoya": "🦸‍♂️ Geroy Himoyasi"
}

def calculate_reward(airdrop_type: str) -> Tuple[str, Dict[str, Any]]:
    """
    Airdrop turiga qarab tasodifiy mukofotni hisoblaydi.
    Returns: (reward_description_string, reward_dict)
    """
    roll = random.random()  # 0.0 - 1.0

    if airdrop_type == "daily":
        # Kunlik drop: Bankrot (15%), Pul (50%), Utilitalar (35%)
        if roll < 0.15:
            return "💥 <b>Bankrot!</b> Afsuski bu safar hech narsa chiqmadi.", {"type": "bankrupt"}
        elif roll < 0.65:
            amount = random.randint(1, 1000)
            return f"💵 <b>${amount:,}</b> dollar pul tushdi!", {"type": "money", "amount": amount}
        else:
            util_key, util_name = random.choice(list(UTILITIES.items()))
            return f"🎁 <b>1 ta {util_name}</b> tushdi!", {"type": "utility", "item": util_key, "count": 1}

    elif airdrop_type == "weekly":
        # Haftalik drop: Bankrot (10%), Pul (55%), Utilita (35%)
        if roll < 0.10:
            return "💥 <b>Bankrot!</b> Afsuski bu safar omadingiz kelmadi.", {"type": "bankrupt"}
        elif roll < 0.65:
            # $1 - $7000, lekin >$1000 bo'lish ehtimoli past
            if random.random() < 0.75:
                amount = random.randint(1, 1000)
            else:
                amount = random.randint(1001, 7000)
            return f"💵 <b>${amount:,}</b> dollar pul tushdi!", {"type": "money", "amount": amount}
        else:
            util_key, util_name = random.choice(list(UTILITIES.items()))
            count = random.randint(1, 2)
            return f"🎁 <b>{count} ta {util_name}</b> tushdi!", {"type": "utility", "item": util_key, "count": count}

    elif airdrop_type == "monthly":
        # Oylik drop: Bankrot (5%), Pul (45%), Utilita (35%), VIP (15%)
        if roll < 0.05:
            return "💥 <b>Bankrot!</b> Oylik drop omadsiz chiqdi.", {"type": "bankrupt"}
        elif roll < 0.50:
            # $1000 - $30000, lekin >$7000 bo'lish ehtimoli past
            if random.random() < 0.80:
                amount = random.randint(1000, 7000)
            else:
                amount = random.randint(7001, 30000)
            return f"💵 <b>${amount:,}</b> dollar pul tushdi!", {"type": "money", "amount": amount}
        elif roll < 0.85:
            util_key, util_name = random.choice(list(UTILITIES.items()))
            count = random.randint(2, 5)
            return f"🎁 <b>{count} ta {util_name}</b> tushdi!", {"type": "utility", "item": util_key, "count": count}
        else:
            return "👑 <b>7 kunlik VIP Status</b> tushdi!", {"type": "vip", "days": 7}

    return "💥 Bankrot!", {"type": "bankrupt"}


async def apply_reward(user_id: int, reward_data: Dict[str, Any]):
    """Mukofotni foydalanuvchining profiliga qo'shadi"""
    user = await User.get_or_none(user_id=user_id)
    if not user:
        return

    profile, _ = await Profile.get_or_create(user=user)

    rew_type = reward_data.get("type")
    if rew_type == "money":
        profile.dollar += reward_data.get("amount", 0)
        await profile.save()
    elif rew_type == "utility":
        item_key = reward_data.get("item")
        count = reward_data.get("count", 1)
        if hasattr(profile, item_key):
            current_val = getattr(profile, item_key, 0)
            setattr(profile, item_key, current_val + count)
            await profile.save()
    elif rew_type == "vip":
        days = reward_data.get("days", 7)
        vip, created = await VipUser.get_or_create(user=user, defaults={"duration_days": days})
        if not created:
            vip.duration_days += days
            await vip.save()
