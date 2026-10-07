from tortoise import fields
from tortoise.models import Model

class User(Model):
    id = fields.BigIntField(pk=True)
    user_id = fields.BigIntField(unique=True)  # Telegram user ID
    full_name = fields.CharField(max_length=100, default="", null=True)
    is_bot = fields.BooleanField(default=False)
    mention = fields.TextField()
    gender = fields.CharField(max_length=1, null=True)  # "m" | "f" | None
    gender_changes = fields.SmallIntField(default=0)  # necha marta o'zgartirdi (max 3)
    username = fields.CharField(max_length=64, null=True)  # Telegram @username, webapp orqali aniqlanganda saqlanadi
    created_at = fields.DatetimeField(auto_now_add=True)  # ro'yxatdan o'tgan sana (admin panel uchun)
    lang = fields.CharField(max_length=5, default="uz")  # bu bot yagona tilda ishlaydi, doim "uz"
    last_seen = fields.DatetimeField(null=True)  # webapp'da oxirgi faollik vaqti (online/offline holati uchun)
    support_cleared_at = fields.DatetimeField(null=True)  # foydalanuvchi o'z chatini tozalagan vaqt — faqat o'zi uchun yashiradi, admin hammasini ko'radi
    tournament_manager_lang = fields.CharField(max_length=5, null=True)  # bo'sh/NULL = oddiy foydalanuvchi; qiymat bo'lsa (masalan "uz") — turnir/reklama menejeri
    def __str__(self):
        return self.full_name

class Transfers(Model):
    id = fields.BigIntField(pk=True)
    from_user = fields.ForeignKeyField("models.User", related_name="transfers_from")
    to_user = fields.ForeignKeyField("models.User", related_name="transfers_to")
    amount = fields.BigIntField()
    type = fields.CharField(max_length=50)  # "diamond", "dollar"
    caption = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)

class DiamondBuyStars(Model):
    user_id = fields.BigIntField()
    amount = fields.IntField()
    stars = fields.IntField()
    charge_id = fields.CharField(max_length=128, null=True, unique=True)
    kind = fields.CharField(max_length=10, default="diamond")  # "diamond" yoki "dollar"
    source = fields.CharField(max_length=10, default="bot")  # "bot" yoki "webapp"
    created_at = fields.DatetimeField(auto_now_add=True)

class AdminGiveLog(Model):
    """Adminlar tomonidan foydalanuvchilarga berilgan har qanday narsaning tarixi —
    botning o'zidan ('bot') yoki webapp orqali ('webapp') qilinganidan qat'i nazar."""
    id = fields.BigIntField(pk=True)
    admin_user_id = fields.BigIntField()
    target_user_id = fields.BigIntField()
    field = fields.CharField(max_length=30)
    amount = fields.BigIntField(default=0)
    extra = fields.CharField(max_length=100, default="")
    source = fields.CharField(max_length=10, default="bot")
    created_at = fields.DatetimeField(auto_now_add=True)

class SupportMessage(Model):
    """Operator (admin) bilan foydalanuvchi o'rtasidagi tarjima qilingan yozishmalar tarixi.
    Foydalanuvchi qaysi tilda yozmasin, admin uni doim o'zbekcha ko'radi; admin o'zbekcha
    yozgani esa foydalanuvchining o'z tiliga tarjima qilinib yetkaziladi."""
    id = fields.BigIntField(pk=True)
    customer_user_id = fields.BigIntField()  # suhbat tegishli bo'lgan mijoz
    is_from_admin = fields.BooleanField(default=False)
    admin_user_id = fields.BigIntField(null=True)
    original_text = fields.TextField()  # xabarni yozgan kishi aynan nima yozgani
    original_lang = fields.CharField(max_length=8, default="uz")  # original_text tili
    uz_text = fields.TextField()  # admin o'qishi uchun — doim o'zbekcha
    customer_text = fields.TextField()  # mijoz o'qishi uchun — doim mijoz tilida
    image_url = fields.CharField(max_length=300, null=True)
    is_read = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

class SupportConversationState(Model):
    """Admin bitta mijoz bilan suhbatni o'z ro'yxatidan 'o'chirganda' shu yerga belgi qo'yiladi —
    xabarlarning o'zi o'chmaydi, mijozning o'zida hammasi saqlanib qoladi, faqat admin
    ro'yxatida shu vaqtdan oldingi xabarlar bilan suhbat yashiriladi (mijoz yozsa qayta chiqadi)."""
    id = fields.BigIntField(pk=True)
    customer_user_id = fields.BigIntField(unique=True)
    admin_cleared_at = fields.DatetimeField(null=True)

class Blocked_user(Model):
    user = fields.ForeignKeyField("models.User", related_name="blocked_users", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

class Profile(Model):
    user = fields.ForeignKeyField("models.User", related_name="profile", on_delete=fields.CASCADE)
    dollar = fields.BigIntField(default=0)
    diamond = fields.BigIntField(default=0)
    himoya = fields.IntField(default=0)
    hujjat = fields.IntField(default=0)
    qotildan_himoya = fields.IntField(default=0)
    osishdan_himoya = fields.IntField(default=0)
    miltiq = fields.IntField(default=0)
    doridan_himoya = fields.IntField(default=0)
    maska = fields.IntField(default=0)
    wins = fields.BigIntField(default=0)
    slip_himoya = fields.IntField(default=0)
    geroy_himoya = fields.IntField(default=0)
    games_count = fields.BigIntField(default=0)
    on_himoya = fields.BooleanField(default=True)
    on_hujjat = fields.BooleanField(default=True)
    on_qotildan_himoya = fields.BooleanField(default=True)
    on_osishdan_himoya = fields.BooleanField(default=True)
    on_miltiq = fields.BooleanField(default=True)
    on_doridan_himoya = fields.BooleanField(default=True)
    on_maska = fields.BooleanField(default=True)
    on_slip_himoya = fields.BooleanField(default=True)
    on_geroy_himoya = fields.BooleanField(default=True)
    daily_streak = fields.IntField(default=0)  # kunlik kirish ketma-ketligi (1-7, keyin 7 da qoladi)
    last_claim_date = fields.DateField(null=True)  # oxirgi kunlik mukofot olingan sana
    birth_date = fields.CharField(max_length=5, null=True)  # "OO-KK" formatida (yil saqlanmaydi) — tug'ilgan kunni tabriklash uchun
    last_birthday_greeted_year = fields.IntField(null=True)  # shu yilda allaqachon tabriklanganmi (qayta-qayta bermaslik uchun)

class ActiveRole(Model):
    profile = fields.ForeignKeyField("models.Profile", related_name="active_roles", on_delete=fields.CASCADE) 
    role = fields.CharField(max_length=50)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

class ChangeDiamondGiveAway(Model):
    id = fields.BigIntField(pk=True)
    creator = fields.ForeignKeyField("models.User", related_name="change_giveaways")
    chat_id = fields.BigIntField()
    message_id = fields.BigIntField()
    amount = fields.BigIntField()
    collected_users = fields.JSONField(default=list)
    created_at = fields.DatetimeField(auto_now_add=True)

class OpenSandiqs(Model):
    user = fields.ForeignKeyField("models.User", related_name="open_sandiqs", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    sandiq_type = fields.CharField(max_length=20, default="mega")  # mega, super, etc.

class VipUser(Model):
    user = fields.ForeignKeyField("models.User", related_name="vip", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    emoji_id = fields.CharField(max_length=64, null=True)
    emoji_char = fields.CharField(max_length=16, null=True)
    duration_days = fields.IntField(default=30)

class Paralar(Model):
    user1 = fields.ForeignKeyField("models.User", related_name="paralar1", on_delete=fields.CASCADE)
    user2 = fields.ForeignKeyField("models.User", related_name="paralar2", on_delete=fields.CASCADE)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

class GeroyMarket(Model):
    user = fields.ForeignKeyField("models.User", related_name="geroy_market", on_delete=fields.CASCADE)
    geroy = fields.ForeignKeyField("models.Geroys", related_name="in_geroy_market", on_delete=fields.CASCADE)
    price = fields.BigIntField()
    is_sold = fields.BooleanField(default=False)  # legacy, status bilan birga saqlanadi
    status = fields.CharField(max_length=10, default="active")  # active | sold | cancelled
    channel_message_id = fields.BigIntField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class NftGiftCatalog(Model):
    """Telegramning sovg'a katalogidan sinxronlangan yozuv — admin har biriga olmos
    narxi qo'yishi mumkin. Narx qo'yilmagan (diamond_price=NULL) sovg'alar marketda
    ko'rinmaydi."""
    id = fields.BigIntField(pk=True)
    gift_id = fields.BigIntField(unique=True)  # Telegramdagi sovg'a ID'si
    title = fields.CharField(max_length=100, null=True)  # sovg'a nomi (fayl nomidan olingan)
    stars_price = fields.IntField()  # Telegramdagi asl narxi (Stars)
    diamond_price = fields.IntField(null=True)  # admin belgilagan narx (olmos) — NULL = sotuvda emas
    is_active = fields.BooleanField(default=True)
    sticker_path = fields.CharField(max_length=300, null=True)  # /uploads/nft_stickers/<gift_id>.jpg
    availability_remains = fields.IntField(null=True)  # limitli sovg'ada qolgan dona soni (cheksiz bo'lsa NULL)
    availability_total = fields.IntField(null=True)  # limitli sovg'aning jami soni
    synced_at = fields.DatetimeField(auto_now=True)


class NftPurchaseLog(Model):
    id = fields.BigIntField(pk=True)
    buyer_user_id = fields.BigIntField()
    gift_id = fields.BigIntField()
    diamond_price = fields.IntField()
    stars_price = fields.IntField(null=True)  # xarid vaqtidagi Stars narxi — byudjet hisobi uchun
    status = fields.CharField(max_length=10, default="pending")  # pending | sent | refunded
    error_text = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class NftMarketSettings(Model):
    """Bitta yagona qatorli sozlama — userbotning shu bot uchun ajratilgan Stars byudjeti.
    Bir nechta bot bitta haqiqiy Telegram hisobini ishlatganda, har bir bot o'ziga
    ajratilgan miqdordan chiqib ketmasligi uchun (haqiqiy hisobda hali Stars qolgan bo'lsa ham)."""
    id = fields.BigIntField(pk=True)
    stars_budget = fields.IntField(null=True)  # NULL = cheklanmagan (faqat haqiqiy balans tekshiriladi)
    spent_baseline = fields.IntField(default=0)  # byudjet oxirgi marta belgilangan paytdagi jami sarflangan Stars —
    # byudjet har safar "shu paytdan boshlab N ta Stars" sifatida ishlashi uchun (o'tmishdagi sarflarni hisobga olmay)


class NftResaleListing(Model):
    """Telegramning "Collectibles" (noyob, allaqachon upgrade qilingan, boshqa
    foydalanuvchilar qayta sotuvga qo'ygan) sovg'alari — har biri noyob, alohida
    egasi bor, faqat Stars orqali sotib olinadigan (TON-only bo'lmagan) nusxalar."""
    id = fields.BigIntField(pk=True)
    base_gift_id = fields.BigIntField()  # asl sovg'a turi (masalan "Plush Pepe")
    unique_id = fields.BigIntField(unique=True)  # Telegramdagi noyob nusxa ID'si
    slug = fields.CharField(max_length=100, unique=True)  # xarid uchun kerak (InputInvoiceStarGiftResale)
    title = fields.CharField(max_length=100)
    num = fields.IntField(null=True)  # nashr raqami (masalan #525)
    stars_price = fields.IntField()  # sotuvchi belgilagan joriy Stars narxi
    diamond_price = fields.IntField(null=True)  # admin belgilagan narx — NULL = sotuvda emas
    is_active = fields.BooleanField(default=True)
    sticker_path = fields.CharField(max_length=300, null=True)
    synced_at = fields.DatetimeField(auto_now=True)


class NftResalePurchaseLog(Model):
    id = fields.BigIntField(pk=True)
    buyer_user_id = fields.BigIntField()
    slug = fields.CharField(max_length=100)
    title = fields.CharField(max_length=100, null=True)
    diamond_price = fields.IntField()
    stars_price = fields.IntField(null=True)
    status = fields.CharField(max_length=20, default="pending")  # pending, sent, refunded
    error_text = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class PremiumGiftOption(Model):
    """Telegram Premium obunasini Stars evaziga sovg'a qilish variantlari
    (masalan 3/6/12 oylik) — Telegramning o'zidan sinxronlanadi."""
    id = fields.BigIntField(pk=True)
    months = fields.IntField(unique=True)
    stars_price = fields.IntField()
    diamond_price = fields.IntField(null=True)  # admin belgilagan narx — NULL = sotuvda emas
    is_active = fields.BooleanField(default=True)
    synced_at = fields.DatetimeField(auto_now=True)


class PremiumPurchaseLog(Model):
    id = fields.BigIntField(pk=True)
    buyer_user_id = fields.BigIntField()
    months = fields.IntField()
    diamond_price = fields.IntField()
    stars_price = fields.IntField(null=True)
    status = fields.CharField(max_length=20, default="pending")  # pending, sent, refunded
    error_text = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class BotAdmin(Model):
    """Koddasiz dinamik ravishda botga qo'shilgan adminlar."""
    id = fields.BigIntField(pk=True)
    user_id = fields.BigIntField(unique=True)
    added_by = fields.BigIntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class RequiredChannel(Model):
    """Majburiy obuna kanallari (Required Channels)"""
    id = fields.BigIntField(pk=True)
    title = fields.CharField(max_length=128, default="Kanal")
    channel_id = fields.BigIntField(null=True)
    username = fields.CharField(max_length=64, null=True)
    invite_link = fields.CharField(max_length=256, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

