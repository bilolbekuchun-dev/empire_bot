from tortoise import fields
from tortoise.models import Model

class Game(Model):
    id = fields.BigIntField(pk=True)
    chat = fields.ForeignKeyField("models.Chat", related_name="games")
    creator = fields.ForeignKeyField("models.User", related_name="created_games")
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    message_id = fields.BigIntField()
    phase = fields.CharField(max_length=10, default="waiting")  # waiting / night / day / end
    mode = fields.CharField(max_length=20, default="classic")
    bot_id = fields.BigIntField(null=True)
    qm_portlat_active = fields.BooleanField(default=False)  # Qora Materiya: Portlatish ishlatilgan (barcha himoyalar o'chgan)

class GamePlayer(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="game_players")
    game = fields.ForeignKeyField("models.Game", related_name="players")
    role = fields.CharField(max_length=70, )  # mafioso, don, doctor, citizen, etc.
    is_alive = fields.BooleanField(default=True)
    joined_at = fields.DatetimeField(auto_now=True)
    deaded_at = fields.DatetimeField(auto_now=True)
    is_sayed_last_word = fields.BooleanField(default=False)
    can_heal_self = fields.BooleanField(default=True)
    can_protection_self = fields.BooleanField(default=True)
    can_document_self = fields.BooleanField(default=True)
    can_investigate_self = fields.BooleanField(default=True)
    can_osishdan_himoya = fields.BooleanField(default=True)
    can_osishdan_himoya_adv = fields.BooleanField(default=True)
    can_slip_himoya = fields.BooleanField(default=True)
    can_miltiq = fields.BooleanField(default=True)
    can_doridan_himoya = fields.BooleanField(default=True)
    can_qotildan_himoya = fields.BooleanField(default=True)
    can_maska = fields.BooleanField(default=True)
    is_sleep = fields.BooleanField(default=False)
    is_osilmas = fields.BooleanField(default=False)
    osildi = fields.BooleanField(default=False)
    missed_nights = fields.BigIntField(default=0) 
    should_choose_card = fields.BooleanField(default=False)
    is_really_winner = fields.BooleanField(default=False) 
    last_visited_user_id = fields.BigIntField(null=True)
    maxsus_raqam = fields.BigIntField(null=True)  
    win = fields.BooleanField(default=False)
    gazabdor_targets = fields.ManyToManyField(
        "models.GamePlayer",
        related_name="picked_by_gazabdor"
    )
    is_actioned = fields.BooleanField(default=False)
    life = fields.IntField(default=100)
    team = fields.CharField(max_length=20, null=True)

    # Bosh Komissar (Komissar upgrade) tizimi
    kom_success_checks = fields.IntField(default=0)           # muvaffaqiyatli tekshiruvlar soni (3 -> upgrade)
    kom_is_upgraded = fields.BooleanField(default=False)      # Bosh Komissar ga o'tganmi
    kom_wire_uses = fields.IntField(default=2)                # Simli Qurilma: qolgan foydalanishlar
    kom_wire_target_pid = fields.BigIntField(null=True)       # Simli Qurilma: kuzatiladigan GamePlayer.id
    kom_profile_used = fields.BooleanField(default=False)     # Psixoprofile ishlatilganmi (1x)
    kom_qosh_used = fields.BooleanField(default=False)        # Qo'sh Tekshiruv ishlatilganmi (1x)
    kom_arrest_pid = fields.BigIntField(null=True)            # Shoshilinch Arrest: GamePlayer.id (shu tun)
    kom_arrest_used = fields.BooleanField(default=False)      # Shoshilinch Arrest ishlatilganmi (1x)
    kom_himoya_target_pid = fields.BigIntField(null=True)     # Himoya Dasturi: himoyalangan GamePlayer.id
    kom_himoya_nights = fields.IntField(default=0)            # Himoya Dasturi: qolgan tunlar soni
    kom_signal_used = fields.BooleanField(default=False)      # Aldamchi Signal ishlatilganmi (1x)
    kom_himoya_protected = fields.BooleanField(default=False) # Himoya Dasturi ostidami (tekshiruvdan himoya)

    # Qora Materiya (Tinch axoli/Fuqaro roliga biriktirilgan qo'shimcha qobiliyatlar)
    qm_active = fields.BooleanField(default=False)
    qm_void_swap_role = fields.CharField(max_length=70, null=True)
    qm_void_swap_days = fields.IntField(default=0)
    qm_original_role = fields.CharField(max_length=70, null=True)
    qm_portlat_used = fields.BooleanField(default=False)
    qm_tiriltir_used = fields.BooleanField(default=False)
    qm_xazina_used = fields.BooleanField(default=False)

class PlayersGameBall(Model):
    player = fields.ForeignKeyField("models.GamePlayer", related_name="player_game_ball", on_delete=fields.CASCADE)
    game = fields.ForeignKeyField("models.Game", related_name="players_ball")
    ball = fields.IntField(default=0)

class GazabdorPick(Model):
    actor = fields.ForeignKeyField("models.GamePlayer", related_name="gazabdor_actions", on_delete=fields.CASCADE)
    target = fields.ForeignKeyField("models.GamePlayer", related_name="gazabdor_targets_back", on_delete=fields.CASCADE)
    phase = fields.ForeignKeyField("models.GamePhase", related_name="gazabdor_picks", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        unique_together = (("actor", "target", "phase"),)

class GamePhase(Model):
    id = fields.BigIntField(pk=True)
    game = fields.ForeignKeyField("models.Game", related_name="phases")
    phase_type = fields.CharField(max_length=10)  # day / night
    number = fields.BigIntField()  # 1, 2, 3...
    started_at = fields.DatetimeField(auto_now_add=True)
    is_end = fields.BooleanField(default=False)

class Vote(Model):
    id = fields.BigIntField(pk=True)
    phase = fields.ForeignKeyField("models.GamePhase", related_name="votes")
    voter = fields.ForeignKeyField("models.GamePlayer", related_name="votes_given")
    target = fields.ForeignKeyField("models.GamePlayer", related_name="votes_received")
    created_at = fields.DatetimeField(auto_now_add=True)

class Action(Model):
    id = fields.BigIntField(pk=True)
    phase = fields.ForeignKeyField("models.GamePhase", related_name="actions")
    actor = fields.ForeignKeyField("models.GamePlayer", related_name="actions_made")
    target = fields.ForeignKeyField("models.GamePlayer", related_name="actions_received")
    action_type = fields.CharField(max_length=20)  # kill, heal, investigate
    result = fields.CharField(max_length=100, null=True)
    with_miltiq = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

class Chat(Model):
    id = fields.BigIntField(pk=True)  
    chat_id = fields.BigIntField()
    title = fields.CharField(max_length=255)
    type = fields.CharField(max_length=50)  # group / supergroup
    created_at = fields.DatetimeField(auto_now_add=True)
    invite_link = fields.CharField(max_length=500, default="")

class Giveaway(Model):
    id = fields.BigIntField(pk=True)
    creator = fields.ForeignKeyField("models.User", related_name="giveaways")
    chat_id = fields.BigIntField()
    message_id = fields.BigIntField()
    total_amount = fields.BigIntField()
    remaining_amount = fields.BigIntField()
    collected_users = fields.JSONField(default=list)
    created_at = fields.DatetimeField(auto_now_add=True)

class VoteLike(Model):
    id = fields.BigIntField(pk=True)
    phase = fields.ForeignKeyField("models.GamePhase", related_name="vote_likes")
    target = fields.ForeignKeyField("models.GamePlayer", related_name="vote_target_likes")
    voter = fields.ForeignKeyField("models.GamePlayer", related_name="voted_likes")
    is_like = fields.BooleanField()
    created_at = fields.DatetimeField(auto_now_add=True)

class GiveTopChat(Model):
    chat = fields.ForeignKeyField("models.Chat", related_name="givetops")
    gived_at = fields.DatetimeField(auto_now_add=True)
    give_type = fields.CharField(max_length=3) # 1, 7, 30, 365


class Geroys(Model):
    user = fields.ForeignKeyField("models.User", related_name="geroy", on_delete=fields.CASCADE)
    name = fields.CharField(max_length=70)
    patron = fields.IntField(default=10)
    level = fields.IntField(default=1)
    himoya = fields.IntField(default=0)
    ball = fields.IntField(default=0)
    photo_url = fields.CharField(max_length=500, default="")  # foydalanuvchi yuklagan shaxsiy Geroy rasmi

class GeroyAction(Model):
    id = fields.BigIntField(pk=True)
    geroy = fields.ForeignKeyField("models.Geroys", related_name="actions", on_delete=fields.CASCADE)
    action_type = fields.CharField(max_length=20)  # attack, shield, skip
    target_user = fields.ForeignKeyField("models.User", related_name="geroy_actions", on_delete=fields.CASCADE, null=True, blank=True)
    phase = fields.ForeignKeyField("models.GamePhase", related_name="geroy_actions", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)


class TournamentTeam(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100)
    logo = fields.CharField(max_length=10, default="🛡")
    order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)


class TournamentArena(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100)
    order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)


class TournamentReferee(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100)
    order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)


class Tournament(Model):
    id = fields.BigIntField(pk=True)
    title = fields.CharField(max_length=200, default="Reklama")
    banner_text = fields.TextField(default="")
    banner_image = fields.CharField(max_length=500, default="")
    banner_images = fields.TextField(default="[]")  # qo'shimcha slayd rasmlari, JSON massiv sifatida
    status = fields.CharField(max_length=20, default="upcoming")  # upcoming, active, finished
    winner_name = fields.CharField(max_length=100, default="")
    winner_team = fields.CharField(max_length=100, default="")
    winner_user_id = fields.BigIntField(null=True)
    contact_username = fields.CharField(max_length=64, default="")
    contact_user_id = fields.BigIntField(null=True)
    contact_button_text = fields.CharField(max_length=50, default="")
    event_date = fields.CharField(max_length=100, default="")
    lang = fields.CharField(max_length=5, default="")
    order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    created_by_user_id = fields.BigIntField(null=True)  # turnir menejeri tomonidan yaratilgan bo'lsa — o'sha kishining Telegram ID'si (bosh admin yaratsa — NULL)
    contact_clicks = fields.IntField(default=0)  # "Qatnashish" tugmasi necha marta bosilgani — reklama samaradorligi statistikasi uchun
    target_user_id = fields.BigIntField(null=True)  # bo'sh = hammaga; bo'lsa — faqat shu Telegram ID'ga tegishli shaxsiy reklama/tabrik (masalan tug'ilgan kun), faqat o'sha odamga reklamalar boshida ko'rinadi
    kind = fields.CharField(max_length=20, default="ad")  # "ad" (Reklama) yoki "tournament" (Turnir) — admin panelda ikkalasi alohida ro'yxatda ko'rinishi uchun
    birthday_date = fields.CharField(max_length=5, null=True)  # shaxsiy tabrik uchun "DD.MM" formatida — kiritilsa, faqat shu kunda ko'rsatiladi va sovg'a beriladi (har yili qaytadi)
    gift_diamond = fields.IntField(default=0)  # birthday_date kelganda avtomatik beriladigan olmos miqdori
    gift_dollar = fields.IntField(default=0)  # birthday_date kelganda avtomatik beriladigan dollar miqdori
    gift_last_year = fields.IntField(null=True)  # sovg'a oxirgi marta berilgan yil — bir yilda bir marta berilishini nazorat qiladi


class Holiday(Model):
    """Bayramlar (Navro'z, Yangi yil va h.k.) — Reklama/Turnirdan alohida, o'zining
    festival ko'rinishi bilan barcha foydalanuvchilarga ko'rinadi."""
    id = fields.BigIntField(pk=True)
    title = fields.CharField(max_length=200, default="Bayram")
    banner_text = fields.TextField(default="")
    banner_image = fields.CharField(max_length=500, default="")
    banner_images = fields.TextField(default="[]")
    status = fields.CharField(max_length=20, default="upcoming")  # upcoming, active, finished
    event_date = fields.CharField(max_length=100, default="")
    order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)


class TournamentMatch(Model):
    id = fields.BigIntField(pk=True)
    tournament = fields.ForeignKeyField("models.Tournament", related_name="matches", on_delete=fields.CASCADE, null=True)
    team1 = fields.CharField(max_length=100)
    team2 = fields.CharField(max_length=100)
    arena = fields.CharField(max_length=100, default="")
    referee = fields.CharField(max_length=100, default="")
    match_time = fields.CharField(max_length=100, default="")
    score1 = fields.IntField(null=True)
    score2 = fields.IntField(null=True)
    status = fields.CharField(max_length=20, default="upcoming")
    order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

