class RoleNames:
    DON = "🤵🏻 Don"
    MAFIA = "🤵🏼 Mafia"
    KOMISSAR = "🕵🏼 Komissar katani"
    DOKTOR = "👨🏼‍⚕️ Doktor"
    SERJANT = "👮🏼 Serjant"
    FUQARO = "👨🏼 Tinch axoli"
    DAYDI = "🧙‍♂️ Daydi"
    KEZUVCHI = "💃 Kezuvchi"
    ADVOKAT = "👨🏼‍💼 Advokat"
    SUIDSID = "🤦🏼 Suidsid"
    OMADLI = "🤞🏼 Omadli"
    JANOB = "🎖 Janob"
    BORI = "🐺 Bo'ri"
    QOTIL = "🔪 Qotil"
    OVCHI = "🥷 Yollanma qotil"
    QASOSKOR = "🧨 Qasoskor"
    AFERIST = "🤹🏻 Aferist"
    GAZABDOR = "🧌 G'azabkor"
    SEHRGAR = "🧙‍ Sehrgar"
    KONCHI = "👷🏻‍♂️ Konchi"
    QAROQCHI = "⚔️ Qaroqchi"
    QORIQCHI = "🛡 Qo'riqchi"
    ZANJIR = "⛓ Zanjir"
    
    AKTYOR = "🎭 Aktyor"
    JIN = "🧞 Jin"
    TAQLIDCHI = "🎭 Taqlidchi"

    @classmethod
    def all(cls):
        return [
            # Tinchlar (9)
            cls.KOMISSAR, cls.SERJANT, cls.FUQARO, cls.DOKTOR,
            cls.DAYDI, cls.KEZUVCHI, cls.OMADLI, cls.JANOB,
            cls.QORIQCHI, cls.ZANJIR,
            # Mafia (4)
            cls.DON, cls.MAFIA, cls.ADVOKAT, cls.OVCHI,
            # Yakkalar (12)
            cls.QOTIL, cls.BORI, cls.AFERIST, cls.GAZABDOR, cls.SEHRGAR,
            cls.SUIDSID, cls.QASOSKOR, cls.QAROQCHI, cls.AKTYOR, cls.JIN, cls.KONCHI,
            cls.TAQLIDCHI
        ]

    @classmethod
    def get_by_role(cls, clean_name: str) -> str:
        mapping = {
            "Don": cls.DON,
            "Mafia": cls.MAFIA,
            "Komissar": cls.KOMISSAR,
            "Doktor": cls.DOKTOR,
            "Serjant": cls.SERJANT,
            "Fuqaro": cls.FUQARO,
            "Komissar katani": cls.KOMISSAR,
            "Tinch axoli": cls.FUQARO,
            "Daydi": cls.DAYDI,
            "Kezuvchi": cls.KEZUVCHI,
            "Advokat": cls.ADVOKAT,
            "Suidisid": cls.SUIDSID,
            "Omadli": cls.OMADLI,
            "Janob": cls.JANOB,
            "Bori": cls.BORI,
            "Qotil": cls.QOTIL,
            "Ovchi": cls.OVCHI,
            "qasoskor": cls.QASOSKOR,
            "aferist": cls.AFERIST,
            "G'azabkor": cls.GAZABDOR,
            "Sehrgar": cls.SEHRGAR,
            "Konchi": cls.KONCHI,
            "Qaroqchi": cls.QAROQCHI,
            "Qo'riqchi": cls.QORIQCHI,
            "Zanjir": cls.ZANJIR,
            "aktyor": cls.AKTYOR,
            "jin": cls.JIN,
            "taqlidchi": cls.TAQLIDCHI,
            "mimic": cls.TAQLIDCHI,
        }
        return mapping.get(clean_name, clean_name)