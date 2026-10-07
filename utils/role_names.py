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
    JURNALIST = "👩🏼‍💻 Jurnalist"
    SOTQIN = "🤓 Sotqin"
    JOKER = "🤡 Joker"
    ADMIRAL = "🧑🏻‍✈️ Admiral"
    KIMYOGAR = "👨‍🔬 Kimyogar"
    BOYOTA = "💰 Rais"
    MINIOR = "☠️  Minior"
    ROBIN_GUD = "🏹 Robin Gud"
    AYGOQCHI = "🦇 Ayg'oqchi"
    KONCHI = "👷🏻‍♂️ Konchi"
    FOTOPARATCHI = "📸 Fotoparatchi"
    QAROQCHI = "⚔️ Qaroqchi"
    ZOMBI = "🧟 Zombi"
    LABARANT = "👩‍⚕️ Labarant"
    HAMSHIRA = "👩🏻‍⚕️ Hamshira"
    KOLDUN = "⚡️ Koldun"
    QORBOBO = "🎅🏻 Qorbobo"
    TULKI = "🦊 Tulki"
    QORIQCHI = "🛡 Qo'riqchi"
    XOYIN = "👺 Xoyin"
    ZANJIR = "⛓ Zanjir"
    
    AKTYOR = "🎭 Aktyor"
    JIN = "🧞 Jin"
    SAVDOGAR = "🏪 Savdogar"
    TAQLIDCHI = "🎭 Taqlidchi"
    REVERSER = "🔄 Reverser"

    @classmethod
    def all(cls):
        return [
            # Tinchlar (13)
            cls.KOMISSAR, cls.SERJANT, cls.FUQARO, cls.DOKTOR, cls.HAMSHIRA,
            cls.DAYDI, cls.KEZUVCHI, cls.OMADLI, cls.JANOB, cls.SOTQIN,
            cls.XOYIN, cls.QORIQCHI, cls.ZANJIR,
            # Mafia (6)
            cls.DON, cls.MAFIA, cls.ADVOKAT, cls.OVCHI, cls.JURNALIST, cls.AYGOQCHI,
            # Yakkalar (13)
            cls.QOTIL, cls.BORI, cls.AFERIST, cls.GAZABDOR, cls.SEHRGAR,
            cls.SUIDSID, cls.QASOSKOR, cls.QAROQCHI, cls.AKTYOR, cls.JIN, cls.KONCHI,
            cls.TAQLIDCHI, cls.REVERSER
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
            "Jurnalist": cls.JURNALIST,
            "Sotqin": cls.SOTQIN,
            "Joker": cls.JOKER,
            "Admiral": cls.ADMIRAL,
            "kimyogar": cls.KIMYOGAR,
            "boy ota": cls.BOYOTA,
            "minior": cls.MINIOR,
            "Robin Gud": cls.ROBIN_GUD,
            "Ayg'oqchi": cls.AYGOQCHI,
            "Konchi": cls.KONCHI,
            "Fotoparatchi": cls.FOTOPARATCHI,
            "Qaroqchi": cls.QAROQCHI,
            "Zombie 1": cls.ZOMBI,
            "Labarant": cls.LABARANT,
            "Hamshira": cls.HAMSHIRA,
            "Koldun": cls.KOLDUN,
            "Qorbobo": cls.QORBOBO,
            "Tulki": cls.TULKI,
            "Qo'riqchi": cls.QORIQCHI,
            "Xoyin": cls.XOYIN,
            "Zanjir": cls.ZANJIR,
            "aktyor": cls.AKTYOR,
            "jin": cls.JIN,
            "Savdogar": cls.SAVDOGAR,
            "taqlidchi": cls.TAQLIDCHI,
            "mimic": cls.TAQLIDCHI,
            "reverser": cls.REVERSER
        }
        return mapping.get(clean_name, clean_name)