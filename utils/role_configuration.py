from utils.role_names import RoleNames
from utils.telegram_utils import split_long_message
from typing import Dict, List, Tuple

class RoleConfiguration:
    """
    Role tartiblarini saqlash va boshqarish classi.
    Faqat Super mode'lar saqlanib qolgan.
    """
    
    # Super Mode Base Configuration (Rollarni erta chiqarish tartibi)
    SUPER_BASE: List[Tuple[int, str]] = [
        # 4 kishi
        (4, RoleNames.DON), (4, RoleNames.KOMISSAR), (4, RoleNames.DOKTOR), (4, RoleNames.FUQARO),
        # 5 kishi
        (5, RoleNames.DAYDI),
        # 6 kishi
        (6, RoleNames.KEZUVCHI),
        # 7 kishi
        (7, RoleNames.MAFIA),
        # 8 kishi (Jin erta chiqadi)
        (8, RoleNames.JIN),
        # 9 kishi
        (9, RoleNames.QASOSKOR),
        # 10 kishi (Qotil erta chiqadi)
        (10, RoleNames.QOTIL),
        # 11 kishi (Zanjir)
        (11, RoleNames.ZANJIR),
        # 12 kishi
        (12, RoleNames.MAFIA),
        # 13 kishi (Konchi erta chiqadi)
        (13, RoleNames.KONCHI),
        # 14 kishi (Aktyor erta chiqadi)
        (14, RoleNames.AKTYOR),
        # 15 kishi
        (15, RoleNames.ADVOKAT),
        # 16 kishi (Qaroqchi erta chiqadi)
        (16, RoleNames.QAROQCHI),
        # 17 kishi (Serjant)
        (17, RoleNames.SERJANT),
        # 18 kishi (Ovchi / Yollanma qotil erta chiqadi)
        (18, RoleNames.OVCHI),
        # 19 kishi
        (19, RoleNames.OMADLI),
        # 20 kishi (Sehrgar erta chiqadi)
        (20, RoleNames.SEHRGAR),
        # 21 kishi (Bo'ri erta chiqadi)
        (21, RoleNames.BORI),
        # 22 kishi
        (22, RoleNames.JANOB),
        # 23 kishi (G'azabkor erta chiqadi)
        (23, RoleNames.GAZABDOR),
        # 24 kishi (Aferist erta chiqadi)
        (24, RoleNames.AFERIST),
        # 25 kishi (Qo'riqchi)
        (25, RoleNames.QORIQCHI),
        # 26 kishi
        (26, RoleNames.MAFIA),
        # 27 kishi
        (27, RoleNames.SUIDSID),
        # 28 kishi
        (28, RoleNames.MAFIA),
        # 29 kishi
        (29, RoleNames.QASOSKOR),
        # 35 kishi
        (35, RoleNames.BORI),
        # 36 kishi
        (36, RoleNames.MAFIA),
        # 37 kishi
        (37, RoleNames.SERJANT),
        # 38 kishi
        (38, RoleNames.FUQARO),
        # 39 kishi
        (39, RoleNames.FUQARO),
        # 40 kishi
        (40, RoleNames.MAFIA),
        # 41 kishi
        (41, RoleNames.FUQARO),
        # 42 kishi
        (42, RoleNames.BORI),
        # 43 kishi
        (43, RoleNames.MAFIA),
        # 44 kishi
        (44, RoleNames.FUQARO),
        # 45 kishi
        (45, RoleNames.MAFIA),
    ]

    SUPER = SUPER_BASE
    SUPER_VS = SUPER_BASE
    PARA_SUPER = SUPER_BASE

    MODE_MAP: Dict[str, List[Tuple[int, str]]] = {
        "super": SUPER,
        "super:vs": SUPER_VS,
        "para x super": PARA_SUPER,
    }

    @classmethod
    def get_roles_for_mode(cls, mode: str, player_count: int) -> List[str]:
        role_config = None
        for mode_key, config in cls.MODE_MAP.items():
            if mode.startswith(mode_key):
                role_config = config
                break
        
        if not role_config:
            role_config = cls.SUPER
        
        roles = []
        for min_players, role in role_config:
            if player_count >= min_players:
                roles.append(role)
        
        return roles

    @classmethod
    def get_formatted_config(cls, mode: str) -> List[str]:
        role_config = cls.MODE_MAP.get(mode)
        if not role_config:
            return [f"❌ '{mode}' mode topilmadi!"]
        
        text = f"<b>🎭 {mode.upper()} MODE - ROL TARTIBI</b>\n\n"
        current_player = 4
        for min_players, role in role_config:
            if min_players != current_player:
                text += f"\n<b>{min_players} kishi:</b>\n   • {role}\n"
                current_player = min_players
            else:
                text += f"   • {role}\n"
        
        return split_long_message(text)

    @classmethod
    def get_all_modes(cls) -> List[str]:
        return list(cls.MODE_MAP.keys())

    @classmethod
    def validate_mode(cls, mode: str) -> bool:
        return any(mode.startswith(key) for key in cls.MODE_MAP.keys())
