from tortoise import fields
from tortoise.models import Model

class UserAirdrop(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="airdrops", on_delete=fields.CASCADE)
    airdrop_type = fields.CharField(max_length=20)  # "daily", "weekly", "monthly"
    cost_diamonds = fields.IntField()  # 1, 7, 30
    is_claimed = fields.BooleanField(default=False)
    claimed_reward_text = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField()  # 12h, 24h, 48h after creation
    is_notified = fields.BooleanField(default=False)  # Smart Notification status

    class Meta:
        table = "user_airdrops"

class RoleSpinLog(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="role_spins", on_delete=fields.CASCADE)
    won_role = fields.CharField(max_length=50)
    cost_diamonds = fields.IntField(default=2)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "role_spin_logs"
