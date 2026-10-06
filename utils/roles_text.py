from utils.role_names import RoleNames
from utils.premium_emojis import role_display
from utils.i18n import clean_lang

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
            RoleNames.KOMISSAR: "Главный защитник города. Ночью вы можете проверить роль игрока или выстрелить в него.",
            RoleNames.FUQARO: "Ваша задача — найти мафию и повесить их во время голосования.",
            RoleNames.SERJANT: "Помощник комиссара.",
            RoleNames.DOKTOR: "Городской врач. Каждую ночь вы лечите одного игрока.",
            RoleNames.HAMSHIRA: "Медсестра. Если доктор погибнет, вы займете его место.",
            RoleNames.DAYDI: "Ночью вы следите за кем-то и можете стать свидетелем убийства.",
            RoleNames.KEZUVCHI: "Ночью даете кому-то снотворное, и этот игрок спит целый день.",
            RoleNames.OMADLI: "Мирный житель с повышенным шансом выжить при нападении.",
            RoleNames.JANOB: "Мирный житель, но ваш голос имеет больший вес.",
            RoleNames.SOTQIN: "Мирный житель, но мафия считает вас своим.",
            RoleNames.XOYIN: "Ищете мафию ночью. Найдете — станете мафией, не найдете за 3 раза — погибаете.",
            RoleNames.QORIQCHI: "Телохранитель. Каждую ночь защищаете одного игрока.",
            RoleNames.ZANJIR: "Связываете двоих игроков каждую ночь. Если один умрет, погибнет и второй!",
            RoleNames.DON: "Глава мафии. Вы отдаете приказы ночью.",
            RoleNames.MAFIA: "Исполнитель мафии. Выполняете приказы Дона и ходите на охоту.",
            RoleNames.ADVOKAT: "Адвокат мафии. Защищаете мафию на суде.",
            RoleNames.OVCHI: "Наемный убийца. Каждую ночь можете убить игрока. Цель — уничтожить всех!",
            RoleNames.JURNALIST: "Агент мафии.",
            RoleNames.AYGOQCHI: "Шпион мафии. Узнаете роль игрока ночью и передаете мафии.",
            RoleNames.QOTIL: "Серийный убийца. Все в городе должны умереть, кроме вас :)",
            RoleNames.BORI: "Оборотень. Ваша сторона меняется в зависимости от того, кто вас убьет.",
            RoleNames.AFERIST: "Нейтральная роль. Ваша цель — просто выжить!",
            RoleNames.GAZABDOR: "Ваша цель — выжить и покарать виновных!",
            RoleNames.SEHRGAR: "Волшебник. Ночью можете поменять местами роли двух игроков.",
            RoleNames.SUIDSID: "Самоубийца. Если вас повесят на голосовании — вы выиграли! :)",
            RoleNames.QASOSKOR: "Мститель. Ваша цель — помочь мирным жителям.",
            RoleNames.QAROQCHI: "Грабитель. Ночью воруете деньги или алмазы у игрока.",
            RoleNames.AKTYOR: "Актер. Каждую ночь бот дает вам новую случайную роль.",
            RoleNames.JIN: "Джинн. Даете выбор игроку: жизнь, деньги или убийство.",
            RoleNames.KONCHI: "Шахтер. Добываете деньги и алмазы в шахтах.",
            RoleNames.TAQLIDCHI: "Подражатель. Занимаете роль первого погибшего игрока.",
            RoleNames.REVERSER: "Реверсер. Перенаправляете действие одного игрока на другого."
        },
        "en": {
            RoleNames.KOMISSAR: "The city's main defender. At night you can check a player's role or shoot them.",
            RoleNames.FUQARO: "Your task is to find the mafia and hang them during daytime voting.",
            RoleNames.SERJANT: "Sergeant, assistant to the Detective/Commissioner.",
            RoleNames.DOKTOR: "City Doctor. Heal one player every night.",
            RoleNames.HAMSHIRA: "Nurse. If the doctor dies, you take their place.",
            RoleNames.DAYDI: "Street Vagrant. Watch someone at night and potentially witness a murder.",
            RoleNames.KEZUVCHI: "Seductress/Lover. Put a player to sleep for one day.",
            RoleNames.OMADLI: "Lucky Citizen. High chance to survive an attack.",
            RoleNames.JANOB: "Nobleman. Your vote carries extra weight in trials.",
            RoleNames.SOTQIN: "Traitor. Innocent citizen, but mafia sees you as an ally.",
            RoleNames.XOYIN: "Turncoat. Look for mafia at night to join them, or perish after 3 failed tries.",
            RoleNames.QORIQCHI: "Bodyguard. Protect one player every night.",
            RoleNames.ZANJIR: "Chain master. Chain two players together; if one dies, both die!",
            RoleNames.DON: "Mafia Boss (Don). Give orders at night.",
            RoleNames.MAFIA: "Mafia member. Execute orders and hunt at night with your team.",
            RoleNames.ADVOKAT: "Mafia Lawyer. Defend mafia members in court.",
            RoleNames.OVCHI: "Hitman / Hunter. Kill one target per night.",
            RoleNames.JURNALIST: "Journalist / Mafia agent.",
            RoleNames.AYGOQCHI: "Spy. Discover a player's role at night and report to mafia.",
            RoleNames.QOTIL: "Serial Killer. Everyone in the city must die except you :)",
            RoleNames.BORI: "Werewolf. Your alignment changes depending on who kills you.",
            RoleNames.AFERIST: "Con artist / Neutral role. Goal: Survive!",
            RoleNames.GAZABDOR: "Avenger. Goal: Survive and punish!",
            RoleNames.SEHRGAR: "Wizard. Swap the roles of two players at night.",
            RoleNames.SUIDSID: "Suicide / Jester. If the village hangs you, you win! :)",
            RoleNames.QASOSKOR: "Vindicator. Goal: Help the innocent citizens win.",
            RoleNames.QAROQCHI: "Bandit / Robber. Rob players of dollars or diamonds at night.",
            RoleNames.AKTYOR: "Actor. Get a new random role every night.",
            RoleNames.JIN: "Genie. Offer a choice: life, wealth, or assassination.",
            RoleNames.KONCHI: "Miner. Mine dollars and diamonds at night.",
            RoleNames.TAQLIDCHI: "Imitator. Inherit the role of the first player who dies.",
            RoleNames.REVERSER: "Reverser. Redirect one player's night action to another."
        },
        "tr": {
            RoleNames.KOMISSAR: "Şehrin ana koruyucusu. Gece bir oyuncunun rolünü kontrol edebilir veya vurabilirsiniz.",
            RoleNames.FUQARO: "Göreviniz mafyayı bulmak ve gündüz oylamasında asmaktır.",
            RoleNames.SERJANT: "Komiser yardımcısı.",
            RoleNames.DOKTOR: "Şehir doktoru. Her gece bir oyuncuyu iyileştirirsiniz.",
            RoleNames.HAMSHIRA: "Hemşire. Doktor ölürse onun yerini alırsınız.",
            RoleNames.DAYDI: "Gece birini izler ve cinayete tanık olabilirsiniz.",
            RoleNames.KEZUVCHI: "Gece birine uyku hapı verirsiniz, o gün uyur.",
            RoleNames.OMADLI: "Şanslı köylü. Saldırılardan hayatta kalma şansı yüksek.",
            RoleNames.JANOB: "Soylu vatandaş. Oy hakkınız daha ağırdır.",
            RoleNames.SOTQIN: "Hain. Mafya sizi kendi safında görür.",
            RoleNames.XOYIN: "Döneklik yapmaya çalışan vatandaş.",
            RoleNames.QORIQCHI: "Koruma. Her gece bir kişiyi korursunuz.",
            RoleNames.ZANJIR: "Her gece iki kişiyi birbirine bağlarsınız. Biri ölürse diğeri de ölür!",
            RoleNames.DON: "Mafya Babası (Don). Gece emir verirsiniz.",
            RoleNames.MAFIA: "Mafya üyesi. Gece ava çıkarsınız.",
            RoleNames.ADVOKAT: "Mafya Avukatı. Mahkemede mafyayı savunursunuz.",
            RoleNames.OVCHI: "Kiralık katil. Her gece bir kişiyi öldürebilirsiniz.",
            RoleNames.JURNALIST: "Gazeteci / Mafya ajanı.",
            RoleNames.AYGOQCHI: "Casus. Gece bir oyuncunun rolünü öğrenip mafyaya bildirirsiniz.",
            RoleNames.QOTIL: "Seri Katil. Şehirdeki herkes ölmeli, siz hariç :)",
            RoleNames.BORI: "Kurtadam. Sizi kimin öldürdüğüne bağlı olarak tarafınız değişir.",
            RoleNames.AFERIST: "Sahtekâr. Amacınız hayatta kalmak!",
            RoleNames.GAZABDOR: "Öfkeli. Amacınız hayatta kalmak ve cezalandırmaktır!",
            RoleNames.SEHRGAR: "Büyücü. Gece iki oyuncunun rollerini takas edersiniz.",
            RoleNames.SUIDSID: "İntihar sevdalısı. Eğer oylamada asılırsanız kazanırsınız! :)",
            RoleNames.QASOSKOR: "İntikamcı. Masumlara yardım edersiniz.",
            RoleNames.QAROQCHI: "Haydut. Gece oyunculardan para veya elmas çalarsınız.",
            RoleNames.AKTYOR: "Aktör. Her gece yeni bir rastgele rol alırsınız.",
            RoleNames.JIN: "Cin. Bir oyuncuya 3 seçenek sunarsınız: Hayat, Servet veya Suikast.",
            RoleNames.KONCHI: "Madenci. Gece madenlerden para ve elmas çıkarırsınız.",
            RoleNames.TAQLIDCHI: "Taklitçi. İlk ölen oyuncunun rolünü üstlenirsiniz.",
            RoleNames.REVERSER: "Reverser. Bir oyuncunun gece eylemini başkasına yönlendirirsiniz."
        }
    }

    @classmethod
    def get_description(cls, role_with_emoji: str, lang: str = "uz") -> str:
        code = clean_lang(lang)
        lang_dict = cls._DESCRIPTIONS.get(code, cls._DESCRIPTIONS["uz"])
        if isinstance(lang_dict, dict):
            return lang_dict.get(role_with_emoji, cls._DESCRIPTIONS["uz"].get(role_with_emoji, "Vazifasi kiritilmagan."))
        return cls._DESCRIPTIONS["uz"].get(role_with_emoji, "Vazifasi kiritilmagan.")

    @classmethod
    def get_by_role(cls, role_with_emoji: str, lang: str = "uz") -> str:
        """Rol xabari: premium emoji bilan va tanlangan dildagi matn."""
        code = clean_lang(lang)
        disp = role_display(role_with_emoji)
        desc = cls.get_description(role_with_emoji, lang=code)
        
        headers = {
            "uz": f"Siz - <b>{disp}</b>!\n{desc}",
            "ru": f"Вы - <b>{disp}</b>!\n{desc}",
            "en": f"You are <b>{disp}</b>!\n{desc}",
            "tr": f"Siz - <b>{disp}</b>!\n{desc}"
        }
        return headers.get(code, headers["uz"])
