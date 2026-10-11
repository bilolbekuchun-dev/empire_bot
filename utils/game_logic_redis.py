from redis import Redis
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, ClassVar
import json
from redis import Redis
from .database import redis_client
"""
Redis-backed version of the Action model.

Usage:
    r = Redis()
    ActionRedis.redis = r

    # create
    a = ActionRedis.create(phase=1, actor=2, target=3, action_type="kill", with_miltiq=False)

    # load
    a2 = ActionRedis.get(a.id)

    # query
    all_actions = ActionRedis.all()
    by_actor = ActionRedis.by_actor(2)

This file expects `redis` (redis-py) to be installed.
"""


DEFAULT_NEXT_ID_KEY = "action:next_id"
ACTION_KEY_PREFIX = "action:"
INDEX_PHASE = "actions:phase:"
INDEX_ACTOR = "actions:actor:"
INDEX_TARGET = "actions:target:"


@dataclass
class ActionRedis:
    """
    Redis-backed representation of the Action model.

    Fields:
      id: int
      phase: int (foreign key id)
      actor: int (foreign key id)
      target: int (foreign key id)
      action_type: str
      result: Optional[str]
      with_miltiq: bool
      created_at: str (ISO)
    """
    id: int
    phase: int
    actor: int
    target: int
    action_type: str
    result: Optional[str] = None
    with_miltiq: bool = False
    created_at: str = ""

    # class-level Redis client (must be set by the consumer)
    redis: ClassVar[Optional[Redis]] = None
    next_id_key: ClassVar[str] = DEFAULT_NEXT_ID_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "phase": str(self.phase),
            "actor": str(self.actor),
            "target": str(self.target),
            "action_type": self.action_type,
            "result": "" if self.result is None else self.result,
            "with_miltiq": "1" if self.with_miltiq else "0",
            "created_at": self.created_at,
        }

    @classmethod
    def _key(cls, id: int) -> str:
        return f"{ACTION_KEY_PREFIX}{id}"

    @classmethod
    def require_redis(cls):
        if cls.redis is None:
            raise RuntimeError("ActionRedis.redis is not set. Assign a redis.Redis instance to ActionRedis.redis")

    @classmethod
    def _parse_hash(cls, h: Dict[bytes, bytes]) -> "ActionRedis":
        decoded = {k.decode(): v.decode() for k, v in h.items()}
        return ActionRedis(
            id=int(decoded["id"]),
            phase=int(decoded["phase"]),
            actor=int(decoded["actor"]),
            target=int(decoded["target"]),
            action_type=decoded["action_type"],
            result=decoded["result"] or None,
            with_miltiq=decoded.get("with_miltiq", "0") == "1",
            created_at=decoded.get("created_at", ""),
        )

    @classmethod
    def create(
        cls,
        phase: int,
        actor: int,
        target: int,
        action_type: str,
        result: Optional[str] = None,
        with_miltiq: bool = False,
        created_at: Optional[str] = None,
    ) -> "ActionRedis":
        cls.require_redis()
        if created_at is None:
            created_at = datetime.now(timezone.utc).isoformat()
        # generate id
        new_id = int(cls.redis.incr(cls.next_id_key))
        action = ActionRedis(
            id=new_id,
            phase=phase,
            actor=actor,
            target=target,
            action_type=action_type,
            result=result,
            with_miltiq=with_miltiq,
            created_at=created_at,
        )
        cls._save_instance_to_redis(action)
        return action

    @classmethod
    def _save_instance_to_redis(cls, action: "ActionRedis"):
        cls.require_redis()
        key = cls._key(action.id)
        data = action.to_dict()
        # use HMSET to store fields
        for field, value in data.items():
            cls.redis.hset(key, field, value)
        # add indexes
        cls.redis.sadd(f"{INDEX_PHASE}{action.phase}", action.id)
        cls.redis.sadd(f"{INDEX_ACTOR}{action.actor}", action.id)
        cls.redis.sadd(f"{INDEX_TARGET}{action.target}", action.id)

    def save(self):
        """
        Persist updates of this instance to Redis.
        Note: If you change phase/actor/target, indexes will be updated (old index cleanup not automatic).
        For safe updates that change indexes, use update(...) classmethod to ensure index maintenance.
        """
        self.__class__._save_instance_to_redis(self)

    @classmethod
    def get(cls, id: int) -> Optional["ActionRedis"]:
        cls.require_redis()
        key = cls._key(id)
        h = cls.redis.hgetall(key)
        if not h:
            return None
        return cls._parse_hash(h)

    @classmethod
    def all(cls) -> List["ActionRedis"]:
        """
        Return all actions by scanning keys. For large datasets consider using indexes instead.
        """
        cls.require_redis()
        cursor = 0
        res: List[ActionRedis] = []
        pattern = f"{ACTION_KEY_PREFIX}*"
        while True:
            cursor, keys = cls.redis.scan(cursor=cursor, match=pattern, count=100)
            for k in keys:
                h = cls.redis.hgetall(k)
                if h:
                    res.append(cls._parse_hash(h))
            if cursor == 0:
                break
        # sort by id
        res.sort(key=lambda a: a.id)
        return res

    @classmethod
    def by_phase(cls, phase_id: int) -> List["ActionRedis"]:
        cls.require_redis()
        s_key = f"{INDEX_PHASE}{phase_id}"
        ids = cls.redis.smembers(s_key)
        return cls._load_many_ids(ids)

    @classmethod
    def by_actor(cls, actor_id: int) -> List["ActionRedis"]:
        cls.require_redis()
        s_key = f"{INDEX_ACTOR}{actor_id}"
        ids = cls.redis.smembers(s_key)
        return cls._load_many_ids(ids)

    @classmethod
    def by_target(cls, target_id: int) -> List["ActionRedis"]:
        cls.require_redis()
        s_key = f"{INDEX_TARGET}{target_id}"
        ids = cls.redis.smembers(s_key)
        return cls._load_many_ids(ids)

    @classmethod
    def _load_many_ids(cls, raw_ids: set) -> List["ActionRedis"]:
        cls.require_redis()
        if not raw_ids:
            return []
        ids = [int(v) if isinstance(v, (bytes, bytearray)) else int(v) for v in raw_ids]
        pipeline = cls.redis.pipeline()
        for id_ in ids:
            pipeline.hgetall(cls._key(id_))
        raws = pipeline.execute()
        res = []
        for h in raws:
            if h:
                res.append(cls._parse_hash(h))
        res.sort(key=lambda a: a.id)
        return res

    @classmethod
    def update(cls, id: int, **kwargs) -> Optional["ActionRedis"]:
        """
        Update fields on an existing action. Supported keys: phase, actor, target, action_type, result, with_miltiq
        Index sets will be updated if phase/actor/target change.
        """
        cls.require_redis()
        inst = cls.get(id)
        if not inst:
            return None
        old_phase, old_actor, old_target = inst.phase, inst.actor, inst.target
        for k, v in kwargs.items():
            if k not in {"phase", "actor", "target", "action_type", "result", "with_miltiq"}:
                continue
            setattr(inst, k, v)
        # persist
        cls._save_instance_to_redis(inst)
        # maintain indexes if they changed
        if old_phase != inst.phase:
            cls.redis.srem(f"{INDEX_PHASE}{old_phase}", inst.id)
            cls.redis.sadd(f"{INDEX_PHASE}{inst.phase}", inst.id)
        if old_actor != inst.actor:
            cls.redis.srem(f"{INDEX_ACTOR}{old_actor}", inst.id)
            cls.redis.sadd(f"{INDEX_ACTOR}{inst.actor}", inst.id)
        if old_target != inst.target:
            cls.redis.srem(f"{INDEX_TARGET}{old_target}", inst.id)
            cls.redis.sadd(f"{INDEX_TARGET}{inst.target}", inst.id)
        return inst

    @classmethod
    def delete(cls, id: int) -> bool:
        cls.require_redis()
        inst = cls.get(id)
        if not inst:
            return False
        key = cls._key(id)
        # remove from indexes
        cls.redis.srem(f"{INDEX_PHASE}{inst.phase}", id)
        cls.redis.srem(f"{INDEX_ACTOR}{inst.actor}", id)
        cls.redis.srem(f"{INDEX_TARGET}{inst.target}", id)
        # delete the hash
        cls.redis.delete(key)
        return True
    
ActionRedis.redis = redis_client