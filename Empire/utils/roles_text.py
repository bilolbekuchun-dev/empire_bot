from utils.role_names import RoleNames
from utils.premium_emojis import role_display

class Roles:
    _DESCRIPTIONS = {
        RoleNames.KOMISSAR: "Shaharning asosiy himoyachisisiz. Tunda bir o'yinchining rolini tekshirishingiz yoki uni otib o'ldirishingiz mumkin.",
        RoleNames.FUQARO: "Sizning vazifangiz mafiani topish va ovoz berish jarayonida ularni osish.",
        RoleNames.SERJANT: "Komissar yordamchisiz.",
        RoleNames.DOKTOR: "Shahar tabibisiz. Har tun bir o'yinchini davolaysiz.",
        RoleNames.HAMSHIRA: "Doktor sizga masterklass o'tib berib turadi. Agar u halok bo'lsa, o'rniga siz doktor bo'lasiz.",
        RoleNames.DAYDI: "Tunda kimnidir kuzatib, qotillik guvohi bo'lib qolishingiz mumkin.",
        RoleNames.KEZUVCHI: "Tunda kimnidir tanlab, unga uyqu dorisi berasiz va u bir kun uxlaydi.",
        RoleNames.OMADLI: "Tinch axolisiz. O'limdan omon qolish ehtimolingiz yuqori.",
        RoleNames.JANOB: "Tinch axolisiz, ammo ovozingiz og'irroq.",
        RoleNames.SOTQIN: "Tinchlarsiz. Ammo mafiya sizni o'z safida ko'radi.",
        RoleNames.XOYIN: "Tinchlarsiz. Tunda mafiyani topishga urinasiz. Topsangiz mafiyaga aylanasiz, 3 marta topolmasangiz o'lasiz.",
        RoleNames.QORIQCHI: "Tinchlarsiz. Har tun bir kishini himoya qilasiz.",
        RoleNames.ZANJIR: "Tinchlarsiz. Har tun ikki kishini bog'lab qo'yasiz. Biri o'lsa, ikkinchisi ham o'ladi!",
        RoleNames.DON: "Mafialar sardorisiz. Tunda buyruq berasiz.",
        RoleNames.MAFIA: "Don buyrug'ini bajarasiz va tunda birga ovga chiqasiz.",
        RoleNames.ADVOKAT: "Mafia tarafdasiz. Sudda mafiyani himoya qilasiz.",
        RoleNames.OVCHI: "Har tun bir kishini o'ldirishingiz mumkin. Maqsadingiz - tinchlar va mafiyani yo'q qilish!",
        RoleNames.JURNALIST: "Mafialar agentisiz.",
        RoleNames.AYGOQCHI: "Mafia tarafdasiz. Tunda bir o'yinchining rolini bilib, mafiyaga aytishingiz mumkin.",
        RoleNames.QOTIL: "Shaxardagi xamma o'lishi kerak, sizdan tashqari albatta :)",
        RoleNames.BORI: "Kimning qo'lidan o'lishingizga qarab tarafingiz o'zgaradi.",
        RoleNames.AFERIST: "Erkin rol. Maqsadingiz - omon qolish!",
        RoleNames.GAZABDOR: "Maqsadingiz - omon qolish va jazolash!",
        RoleNames.SEHRGAR: "Tunda ikki kishining rolini o'zaro almashtirishingiz mumkin.",
        RoleNames.SUIDSID: "Seni osib o'ldirishsa sen yutasan! :)",
        RoleNames.QASOSKOR: "Maqsadingiz - tinchlarga yordam berish.",
        RoleNames.QAROQCHI: "Tunda kimgadir borib pul yoki olmosini olasiz, topolmasangiz do'pposlab qaytasiz.",
        RoleNames.AKTYOR: "Har tun bot tomonidan sizga yangi rol beriladi va o'sha rolda o'ynaysiz.",
        RoleNames.JIN: "Tunda 1 kishiga tanlov berasiz:\n1. Hayot - u omon qoladi.\n2. Pul - unga pul yoki olmos.\n3. Qotillik - u so'ragan ishtirokchini o'ldirib berasiz.",
        RoleNames.KONCHI: "Tunda maxfiy shaxtalardan boylik (dollar va olmos) qazib olasiz, ammo ehtiyot bo'ling — ba'zi konlarda o'lim tuzog'i bor!",
        RoleNames.TAQLIDCHI: "O'yin boshida maxsus rolingiz yo'q. Birinchi o'lik o'yinchining rolini egallaysiz va keyinchalik o'sha rolda o'ynaysiz.",
        RoleNames.REVERSER: "Neytral rol. Har tun bir o'yinchining (1-nishon) tungi harakatini boshqa bir o'yinchiga (2-nishon) yo'naltiradi (Reverse)!"
    }

    @classmethod
    def get_description(cls, role_with_emoji: str, lang: str = "uz") -> str:
        return cls._DESCRIPTIONS.get(role_with_emoji, "Vazifasi kiritilmagan.")

    @classmethod
    def get_by_role(cls, role_with_emoji: str, lang: str = "uz") -> str:
        """Rol xabari: premium emoji bilan (admin sozlagan bo'lsa) va o'zbekcha nom."""
        disp = role_display(role_with_emoji)
        desc = cls.get_description(role_with_emoji)
        return f"Siz - <b>{disp}</b>!\n{desc}"
