from utils.role_names import RoleNames
from utils.premium_emojis import role_display

class Roles:
    _DESCRIPTIONS = {
        "uz": {
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
            RoleNames.TAQLIDCHI: "Siz taqlidchisiz. O'yin boshida rolingiz bo'lmaydi, birinchi halok bo'lgan o'yinchining rolini egallaysiz.",
            RoleNames.REVERSER: "Siz reversersiz. Har tun bir o'yinchining harakatini boshqa o'yinchiga yo'naltirib qo'yasiz."
        },
        "ru": {
            RoleNames.KOMISSAR: "Вы главный защитник города. Ночью вы можете проверить роль игрока или застрелить его.",
            RoleNames.FUQARO: "Ваша задача — найти мафию и выгнать на голосовании.",
            RoleNames.SERJANT: "Вы помощник комиссара.",
            RoleNames.DOKTOR: "Вы городской врач. Каждую ночь лечите одного игрока.",
            RoleNames.HAMSHIRA: "Вы медсестра. Если доктор погибнет, вы займете его место.",
            RoleNames.DAYDI: "Вы бродяга. Следя за кем-то ночью, вы можете стать свидетелем убийства.",
            RoleNames.KEZUVCHI: "Вы кутила. Усыпляете игрока ночью, и он пропускает ход.",
            RoleNames.OMADLI: "Вы везунчик. У вас высокий шанс выжить при нападении.",
            RoleNames.JANOB: "Вы дворянин. Ваш голос имеет больший вес на голосовании.",
            RoleNames.SOTQIN: "Вы предатель. Вы на стороне мирных, но мафия считает вас своим.",
            RoleNames.XOYIN: "Вы отступник. Ищете мафию; если найдете — примкнете, если ошибётесь 3 раза — умрете.",
            RoleNames.QORIQCHI: "Вы телохранитель. Защищаете одного игрока каждую ночь.",
            RoleNames.ZANJIR: "Вы связной. Связываете двух игроков; если умрет один, погибнет и второй!",
            RoleNames.DON: "Вы Дон мафии. Отдаете приказы ночью.",
            RoleNames.MAFIA: "Вы Мафия. Выполняете приказ Дона и выходите на охоту.",
            RoleNames.ADVOKAT: "Вы адвокат. Защищаете мафию на голосовании.",
            RoleNames.OVCHI: "Вы охотник. Можете убивать каждую ночь. Ваша цель — устранить всех!",
            RoleNames.JURNALIST: "Вы журналист. Агент мафии.",
            RoleNames.AYGOQCHI: "Вы шпион. Узнаете роли игроков для мафии.",
            RoleNames.QOTIL: "Вы маньяк. Все в городе должны умереть, кроме вас! :)",
            RoleNames.BORI: "Вы оборотень. Ваша сторона зависит от того, кто вас атакует.",
            RoleNames.AFERIST: "Вы аферист. Ваша цель — просто выжить!",
            RoleNames.GAZABDOR: "Вы каратель. Ваша цель — выжить и наказать виновных!",
            RoleNames.SEHRGAR: "Вы волшебник. Можете поменять роли двух игроков местами.",
            RoleNames.SUIDSID: "Вы самоубийца. Вы выиграете, если вас повесят! :)",
            RoleNames.QASOSKOR: "Вы мститель. Ваша цель — помочь мирным жителям.",
            RoleNames.QAROQCHI: "Вы грабитель. Забираете деньги у игроков ночью.",
            RoleNames.AKTYOR: "Вы актер. Каждую ночь получаете случайную роль и исполняете ее.",
            RoleNames.JIN: "Вы джинн. Даете игроку выбор: 1. Жизнь 2. Деньги 3. Убийство.",
            RoleNames.KONCHI: "Вы шахтер. Добываете богатства ночью, но берегитесь смертельных ловушек!",
            RoleNames.TAQLIDCHI: "Вы мимик. Принимаете роль первого погибшего игрока.",
            RoleNames.REVERSER: "Вы реверсер. Каждую ночь перенаправляете действие первого игрока на второго."
        },
        "en": {
            RoleNames.KOMISSAR: "You are the main protector of the city. At night, you can check a player's role or shoot them.",
            RoleNames.FUQARO: "Your goal is to find the mafia and vote them out.",
            RoleNames.SERJANT: "You are the Detective's assistant.",
            RoleNames.DOKTOR: "You are the city Doctor. You heal one player each night.",
            RoleNames.HAMSHIRA: "You are the Nurse. If the doctor dies, you become the doctor.",
            RoleNames.DAYDI: "You are the Tracker. Watching someone at night, you may witness a murder.",
            RoleNames.KEZUVCHI: "You are the Sleeper. Put a player to sleep for a night.",
            RoleNames.OMADLI: "You are the Lucky One. You have a high chance of surviving attacks.",
            RoleNames.JANOB: "You are the Nobleman. Your vote carries more weight.",
            RoleNames.SOTQIN: "You are the Traitor. You are a civilian, but mafia sees you as partner.",
            RoleNames.XOYIN: "You are the Renegade. Try to find mafia to join them. 3 misses and you die.",
            RoleNames.QORIQCHI: "You are the Bodyguard. Protect one player each night.",
            RoleNames.ZANJIR: "You are the Linker. Link two players; if one dies, both die!",
            RoleNames.DON: "You are the Mafia Don. Give kill orders at night.",
            RoleNames.MAFIA: "You are Mafia. Execute the Don't order and hunt together.",
            RoleNames.ADVOKAT: "You are the Lawyer. Protect mafia during daytime voting.",
            RoleNames.OVCHI: "You are the Hunter. Kill a player each night to eliminate everyone!",
            RoleNames.JURNALIST: "You are the Journalist. Mafia's secret agent.",
            RoleNames.AYGOQCHI: "You are the Spy. Reveal player roles to the mafia.",
            RoleNames.QOTIL: "You are the Serial Killer. Everyone must die except you! :)",
            RoleNames.BORI: "You are the Werewolf. Your team shifts depending on who attacks you.",
            RoleNames.AFERIST: "You are the Trickster. Your goal is survival!",
            RoleNames.GAZABDOR: "You are the Avenger. Survive and punish your targets!",
            RoleNames.SEHRGAR: "You are the Sorcerer. Swap roles of two players at night.",
            RoleNames.SUIDSID: "You are the Jester. Win if you get voted off and lynched! :)",
            RoleNames.QASOSKOR: "You are the Vigilante. Help the civilians win.",
            RoleNames.QAROQCHI: "You are the Robber. Steal money or gems at night.",
            RoleNames.AKTYOR: "You are the Actor. Each night you assume a new random role.",
            RoleNames.JIN: "You are the Genie. Grant a choice to a player: 1. Life 2. Money 3. Kill.",
            RoleNames.KONCHI: "You are the Miner. Mine diamonds and gold at night, but watch out for traps!",
            RoleNames.TAQLIDCHI: "You are the Mimic. Start roleless; inherit the role of the first player who dies.",
            RoleNames.REVERSER: "You are the Reverser. Each night redirect target 1's action to target 2."
        },
        "tr": {
            RoleNames.KOMISSAR: "Şehrin ana koruyususunuz. Gece bir oyuncunun rolünü kontrol edebilir veya onu vurabilirsiniz.",
            RoleNames.FUQARO: "Göreviniz mafyayı bulmak ve oylamada asmaktır.",
            RoleNames.SERJANT: "Komiserin yardımcısısınız.",
            RoleNames.DOKTOR: "Şehir doktorusunuz. Her gece bir oyuncuyu iyileştirirsiniz.",
            RoleNames.HAMSHIRA: "Hemşiresiniz. Doktor ölürse onun yerine doktor olursunuz.",
            RoleNames.DAYDI: "Sokak gezginisiniz. Gece birini izleyerek cinayet tanığı olabilirsiniz.",
            RoleNames.KEZUVCHI: "Gezginsiniz. Gece birine uyku hapı verip uyutursunuz.",
            RoleNames.OMADLI: "Şanslı sivilsiniz. Ölümden kurtulma olasılığınız yüksektir.",
            RoleNames.JANOB: "Asilzadesiniz, oyunuz daha ağırlıklıdır.",
            RoleNames.SOTQIN: "Hain sivilsiniz. Mafya sizi kendi tarafında görür.",
            RoleNames.XOYIN: "İsyankarsınız. Mafyayı bulmaya çalışırsınız, 3 hatada ölürsünüz.",
            RoleNames.QORIQCHI: "Korumasınız. Her gece bir kişiyi korursunuz.",
            RoleNames.ZANJIR: "Zincircisiniz. İki oyuncuyu bağlarsınız; biri ölürse diğeri de ölür!",
            RoleNames.DON: "Mafya Liderisiniz (Don). Gece emir verirsiniz.",
            RoleNames.MAFIA: "Mafyasınız. Don'un emrini yerine getirirsiniz.",
            RoleNames.ADVOKAT: "Avukatsınız. Oylamada mafyayı savunursunuz.",
            RoleNames.OVCHI: "Avcısınız. Her gece bir kişiyi öldürebilirsiniz.",
            RoleNames.JURNALIST: "Gazetecisiniz. Mafya ajanı.",
            RoleNames.AYGOQCHI: "Ajasınız. Oyuncuların rollerini mafyaya bildirirsiniz.",
            RoleNames.QOTIL: "Katilsiniz. Şehirdeki herkes ölmeli, siz hariç! :)",
            RoleNames.BORI: "Kurt adamsınız. Tarafınız ölüm şeklinize göre değişir.",
            RoleNames.AFERIST: "Sahtekarsınız. Amacınız hayatta kalmaktır!",
            RoleNames.GAZABDOR: "Cezalandırıcısınız. Amacınız hayatta kalmak ve cezalandırmaktır!",
            RoleNames.SEHRGAR: "Büyücüsünüz. Gece iki oyuncunun rolünü değiştirebilirsiniz.",
            RoleNames.SUIDSID: "İntiharcısınız. Oylamada asılırsanız kazanırsınız! :)",
            RoleNames.QASOSKOR: "Intikamcısınız. Sivillere yardım edin.",
            RoleNames.QAROQCHI: "Soyguncusunuz. Gece birinden para veya elmas çalarsınız.",
            RoleNames.AKTYOR: "Aktörsünüz. Her gece rastgele yeni bir rol alıp onu oynarsınız.",
            RoleNames.JIN: "Cinsiniz. Gece bir oyuncuya 3 dilek seçeneği sunarsınız: 1. Hayat 2. Para 3. Cinayet.",
            RoleNames.KONCHI: "Madencisiniz. Gece elmas ve altın kazarsınız, tuzaklara dikkat edin!",
            RoleNames.TAQLIDCHI: "Taklitçisiniz. Oyuna rolsüz başlarsınız, ölen ilk oyuncunun rolünü alırsınız.",
            RoleNames.REVERSER: "Reversersiniz. Her gece 1. oyuncunun eylemini 2. oyuncuya yönlendirirsiniz."
        }
    }

    @classmethod
    def get_description(cls, role_with_emoji: str, lang: str = "uz") -> str:
        lang_code = (lang or "uz").lower()
        descriptions = cls._DESCRIPTIONS.get(lang_code, cls._DESCRIPTIONS["uz"])
        return descriptions.get(role_with_emoji, cls._DESCRIPTIONS["uz"].get(role_with_emoji, "Vazifasi kiritilmagan."))

    @classmethod
    def get_by_role(cls, role_with_emoji: str, lang: str = "uz") -> str:
        """Rol xabari: premium emoji bilan va tanlangan tildagi matn."""
        disp = role_display(role_with_emoji)
        desc = cls.get_description(role_with_emoji, lang=lang)
        lang_code = (lang or "uz").lower()
        prefix_map = {
            "uz": f"Siz - <b>{disp}</b>!",
            "ru": f"Вы — <b>{disp}</b>!",
            "en": f"You are — <b>{disp}</b>!",
            "tr": f"Sen — <b>{disp}</b>!"
        }
        prefix = prefix_map.get(lang_code, prefix_map["uz"])
        return f"{prefix}\n{desc}"
