from tortoise import fields, models

class GameSetTime(models.Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField(unique=True)
    day_time = fields.BigIntField(default=45)      
    night_time = fields.BigIntField(default=45)    
    vote_time = fields.BigIntField(default=30)     
    like_time = fields.BigIntField(default=30)
    word_time = fields.BigIntField(default=30)
    reg_time = fields.BigIntField(default=120)  # Ro'yxatdan o'tish vaqti
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "game_sets_time"

    def __str__(self):
        return f"GameSet(chat_id={self.chat_id})"

class GameModeSet(models.Model):
    chat_id = fields.BigIntField(unique=True)
    mode_name = fields.CharField(max_length=20, default="super")

class GameSetListRoles(models.Model):
    chat_id = fields.BigIntField(unique=True)
    # store blacklisted role names as a comma-separated string
    blacklist = fields.TextField(default="")
    updated_at = fields.DatetimeField(auto_now=True)

    def get_blacklist(self):
        return [r for r in self.blacklist.split(",") if r]

    def set_blacklist(self, roles_list):
        self.blacklist = ",".join(sorted(set(roles_list)))

    def ban_role(self, role: str):
        r = set(self.get_blacklist())
        r.add(role)
        self.blacklist = ",".join(sorted(r))

    def unban_role(self, role: str):
        r = set(self.get_blacklist())
        r.discard(role)
        self.blacklist = ",".join(sorted(r))

    def is_banned(self, role: str) -> bool:
        return role in set(self.get_blacklist())

class GameSetPermissions(models.Model):
    chat_id = fields.BigIntField(unique=True)
    anonim_ovoz_berish = fields.BooleanField(default=False)
    leave_qilish = fields.BooleanField(default=True)
    last_word_say = fields.BooleanField(default=True)
    frendly_fire = fields.BooleanField(default=False)

    updated_at = fields.DatetimeField(auto_now=True)

class GameSetWeapons(models.Model):
    chat_id = fields.BigIntField(unique=True)
    himoya = fields.BooleanField(default=True)  # Himoya
    hujjat = fields.BooleanField(default=True)  # Hujjat
    qotildan_himoya = fields.BooleanField(default=True)  # Qotildan himoya
    ovozdan_himoya = fields.BooleanField(default=True)  # Ovozdan himoya
    miltiq = fields.BooleanField(default=True)  # Miltiq
    doridan_himoya = fields.BooleanField(default=True)  # Doridan himoya
    slip_himoya = fields.BooleanField(default=True)  # Sirpanishdan himoya
    maska = fields.BooleanField(default=True)  # Maska
    geroy = fields.BooleanField(default=True)  # Geroy
    active_role = fields.BooleanField(default=True)  # Faol rol
    updated_at = fields.DatetimeField(auto_now=True)

class GroupBalance(models.Model):
    chat_id = fields.BigIntField(unique=True)
    balance = fields.BigIntField(default=0)
    real_money = fields.IntField(default=0)  # Real pul ($) miqdori
    updated_at = fields.DatetimeField(auto_now=True)
    last_reset_at = fields.DatetimeField(null=True)  # Oxirgi marta balans tozalangan vaqt

class GroupGiveSet(models.Model):
    chat_id = fields.BigIntField(unique=True)

    diamond = fields.BigIntField(default=0)
    dollar = fields.BigIntField(default=0)

    updated_at = fields.DatetimeField(auto_now=True)

class GroupMoreSet(models.Model):
    chat_id = fields.BigIntField(unique=True)

    mafning_ovozi = fields.BooleanField(default=True)
    adv_view = fields.BooleanField(default=True)
    max_players = fields.BigIntField(default=30)
    rollarni_guruhlash = fields.BooleanField(default=True)

    updated_at = fields.DatetimeField(auto_now=True)

class CommandPermissionsChat(models.Model):
    chat_id = fields.BigIntField(unique=True)
    start_cmd = fields.CharField(max_length=10)
    stop_cmd = fields.CharField(max_length=10)
    game_cmd = fields.CharField(max_length=10)
    top1_cmd = fields.CharField(max_length=10)
    top7_cmd = fields.CharField(max_length=10)
    top30_cmd = fields.CharField(max_length=10)
    gtop1_cmd = fields.CharField(max_length=10)
    gtop7_cmd = fields.CharField(max_length=10)
    gtop30_cmd = fields.CharField(max_length=10)
    extend_cmd = fields.CharField(max_length=10, default="admin")
    updated_at = fields.DatetimeField(auto_now=True)

class WriteGroupPermis(models.Model):
    chat_id = fields.BigIntField(unique=True)
    night = fields.CharField(max_length=20, default="alive") 
    day = fields.CharField(max_length=20, default="alive")
    updated_at = fields.DatetimeField(auto_now=True)

class GamingOnChat(models.Model):
    chat_id = fields.BigIntField(unique=True)
    can_gaming = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    bot_id = fields.BigIntField(null=True)

class BlockGrousp(models.Model):
    chat_id = fields.BigIntField(unique=True)
    updated_at = fields.DatetimeField(auto_now=True)

class NickModeSet(models.Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField(unique=True)
    selected_nicklist = fields.ForeignKeyField("models.NickList", related_name="used_in_chats", null=True)

class NickList(models.Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField(unique=True)
    name = fields.CharField(max_length=50)

class NickListItem(models.Model):
    id = fields.BigIntField(pk=True)
    nick_list = fields.ForeignKeyField("models.NickList", related_name="nick_items")
    nick_name = fields.CharField(max_length=30)

class WolfOrFoxSet(models.Model):
    chat_id = fields.BigIntField(unique=True)
    wolf_or_fox = fields.BooleanField(default=True)  # True = Bo'ri, False = Tulki
    updated_at = fields.DatetimeField(auto_now=True)

class TransfersReportsChat(models.Model):
    chat_id = fields.BigIntField(unique=True)
    report_diamond = fields.BooleanField(default=True)
    report_dollar = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)

class GroupBalanceTransfer(models.Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField(unique=True)
    balance = fields.DecimalField(max_digits=10, decimal_places=2)
    updated_at = fields.DatetimeField(auto_now=True)